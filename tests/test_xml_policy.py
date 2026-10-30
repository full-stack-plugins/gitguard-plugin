import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gitflow.git import FlowError
from gitflow import xml_policy as xml


class XMLPolicyTests(unittest.TestCase):
    def policy(self):
        return json.loads((Path(__file__).resolve().parents[1] / 'profiles/github-flow.json').read_text())

    def test_all_templates(self):
        for path in (Path(__file__).resolve().parents[1] / 'profiles').glob('*.json'):
            value = json.loads(path.read_text())
            with self.subTest(path=path.name):
                self.assertEqual(xml.decode(xml.encode(value)), value)

    def test_cr_and_crlf_preserve_exact_rule(self):
        for value in ('a\rb', 'a\r\nb'):
            policy=self.policy();policy['commit_message_pattern']=value
            self.assertEqual(xml.decode(xml.encode(policy)),policy)

    def test_v2_roundtrip(self):
        value = self.policy()
        value.update(schema_version='2.0.0', rules={'GF001': {'severity': 'error', 'options': {'types': ['feat', 'fix'], 'allow_merge': False}}, 'GF002': {'severity': 'warn', 'options': {'max_length': 80}}}, extends={'path': '.gitflow/baselines/company.json', 'sha256': 'a' * 64})
        self.assertEqual(xml.decode(xml.encode(value)), value)
        value['extends'] = None
        self.assertEqual(xml.decode(xml.encode(value)), value)

    def assert_xml_invalid(self, raw):
        with self.assertRaises(FlowError) as raised:
            xml.decode(raw)
        self.assertEqual(raised.exception.code, 'policy_xml_invalid')
        self.assertEqual(raised.exception.message,
                         'XML policy is invalid or exceeds its resource budget.')

    def test_resource_limits(self):
        # Isolate XML budgets from policy-schema validation. Each boundary
        # control must parse/unpack successfully; the over-limit partner must
        # fail before the policy validator is reached.
        def nested(depth):
            return (b'<policy type="object"><nested type="list">' +
                    b'<item type="list">' * (depth - 2) +
                    b'</item>' * (depth - 2) + b'</nested></policy>')

        def nodes(count):
            return (b'<policy type="object"><items type="list">' +
                    b'<item type="null"/>' * (count - 2) +
                    b'</items></policy>')

        def text(size):
            # References split Expat character callbacks, exercising the
            # accumulated per-element bound as well as single callbacks.
            return (b'<policy type="object"><value type="string">' +
                    b'&#120;' * size + b'</value></policy>')

        def total_text(count):
            return (b'<policy type="object">' + b''.join(
                    b'<s%d type="string">' % i + b'x' * xml.MAX_TEXT +
                    b'</s%d>' % i for i in range(count)) + b'</policy>')

        small = b'<policy type="object"/>'
        cases = [
            ('depth', nested(xml.MAX_DEPTH), nested(xml.MAX_DEPTH + 1)),
            ('nodes', nodes(xml.MAX_NODES), nodes(xml.MAX_NODES + 1)),
            ('scalar text', text(xml.MAX_TEXT), text(xml.MAX_TEXT + 1)),
            ('total text', total_text(8), total_text(9)),
            ('bytes', small + b' ' * (xml.LIMIT - len(small)),
             small + b' ' * (xml.LIMIT - len(small) + 1)),
        ]
        for label, boundary, attack in cases:
            with self.subTest(limit=label):
                with mock.patch.object(xml, '_validate', side_effect=lambda p: p) as validate:
                    xml.decode(boundary)
                    validate.assert_called_once()
                    validate.reset_mock()
                    self.assert_xml_invalid(attack)
                    validate.assert_not_called()

    def test_forbidden_xml_features(self):
        good = xml.encode(self.policy())
        document = good.split(b'\n', 1)[1]
        attacks = {
            'internal entity': b'<!DOCTYPE policy [<!ENTITY x "boom">]>' + document,
            'external DTD': b'<!DOCTYPE policy SYSTEM "file:///etc/passwd">' + document,
            'external entity': b'<!DOCTYPE policy [<!ENTITY x SYSTEM "file:///etc/passwd">]>' + document,
            'XInclude': document.replace(b'</policy>', b'<xi:include xmlns:xi="http://www.w3.org/2001/XInclude" href="file:///etc/passwd"/></policy>'),
            'processing instruction': b'<?unsafe data?>' + document,
            'comment': b'<!-- comment -->' + document,
            'extra attribute': document.replace(b'<policy type="object">', b'<policy type="object" extra="x">', 1),
            'unknown type': document.replace(b'<revision type="int">', b'<revision type="float">'),
            'wrong scalar': document.replace(b'<revision type="int">1', b'<revision type="int">true'),
            'wrong root': document.replace(b'<policy ', b'<unknown ', 1).replace(b'</policy>', b'</unknown>'),
            'duplicate field': document.replace(b'</policy>', b'<revision type="int">1</revision></policy>'),
        }
        attacks['UTF-16 DTD'] = attacks['internal entity'].decode().encode('utf-16')
        for feature, raw in attacks.items():
            with self.subTest(feature=feature):
                self.assert_xml_invalid(raw)

    def test_unknown_xml_schema_and_fields(self):
        good = xml.encode(self.policy())
        attacks = [
            good.replace(b'1.0.0', b'9.0.0'),
            good.replace(b'</policy>', b'<unknown type="null"/></policy>'),
        ]
        for raw in attacks:
            with self.subTest(raw=raw):
                with self.assertRaises(FlowError) as raised:
                    xml.decode(raw)
                self.assertEqual(raised.exception.code, 'policy_schema_invalid')

    def test_store_and_shared_path(self):
        with tempfile.TemporaryDirectory() as temp:
            facts = {'common_dir': temp, 'git_dir': temp + '/worktrees/a'}
            self.assertEqual(xml.policy_path(facts), Path(temp) / 'gitflow.xml')
            with self.assertRaises(FlowError): xml.read_policy(facts)
            xml.write_policy(facts, self.policy())
            self.assertEqual(xml.read_policy(facts), self.policy())
            xml.write_policy(facts, self.policy())
            self.assertFalse(list(Path(temp).glob('.gitflow-write-*')))

    def test_unsafe_files(self):
        for kind in ('symlink', 'hardlink', 'directory', 'parent'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                base = Path(temp); common = base / 'common'; common.mkdir()
                target = common / 'gitflow.xml'; other = base / 'other'; other.write_bytes(xml.encode(self.policy()))
                if kind == 'symlink': target.symlink_to(other)
                elif kind == 'hardlink': os.link(other, target)
                elif kind == 'directory': target.mkdir()
                else:
                    common.rmdir(); common.symlink_to(base, target_is_directory=True)
                facts = {'common_dir': str(common)}
                with self.assertRaises(FlowError): xml.read_policy(facts)
                with self.assertRaises(FlowError): xml.write_policy(facts, self.policy())
                self.assertEqual(other.read_bytes(), xml.encode(self.policy()))

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO is not available on this operating system')
    def test_fifo_policy_is_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'gitflow.xml';os.mkfifo(target)
            facts={'common_dir':temp}
            with self.assertRaises(FlowError):xml.read_policy(facts)
            with self.assertRaises(FlowError):xml.write_policy(facts,self.policy())
            self.assertTrue(target.exists())

    def test_write_detects_replaced_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            facts = {'common_dir': temp}
            xml.write_policy(facts, self.policy())
            target = xml.policy_path(facts)
            original = xml.tempfile.mkstemp
            def replace_during_write(*args, **kwargs):
                result = original(*args, **kwargs)
                replacement = Path(temp) / 'replacement'
                replacement.write_bytes(b'preserve concurrent edit')
                os.replace(replacement, target)
                return result
            with mock.patch.object(xml.tempfile, 'mkstemp', side_effect=replace_during_write):
                with self.assertRaises(FlowError): xml.write_policy(facts, self.policy())
            self.assertEqual(target.read_bytes(), b'preserve concurrent edit')
            self.assertFalse(list(Path(temp).glob('.gitflow-write-*')))

    def test_oversized_read_and_bad_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            facts = {'common_dir': temp}
            target = Path(temp) / 'gitflow.xml'
            target.write_bytes(b'x' * (256 * 1024 + 1))
            with self.assertRaises(FlowError): xml.read_policy(facts)
            with self.assertRaises(FlowError): xml.write_policy(facts, self.policy())
            target.unlink()
            (Path(temp) / 'gitflow.xml.lock').unlink()
            (Path(temp) / 'gitflow.xml.lock').symlink_to(Path(temp) / 'other')
            with self.assertRaises(FlowError): xml.write_policy(facts, self.policy())
            self.assertFalse(target.exists())

    def test_unknown_fields_and_types(self):
        for key, value in [('unknown', 1), ('revision', True), ('roles', [])]:
            policy = copy.deepcopy(self.policy()); policy[key] = value
            with self.assertRaises(FlowError): xml.encode(policy)


if __name__ == '__main__': unittest.main()

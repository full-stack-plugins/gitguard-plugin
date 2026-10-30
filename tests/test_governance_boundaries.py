"""治理信任边界：真实 Git 对象、固定快照、未知状态不能变成通过。"""
import hashlib
import json
import subprocess
import sys
import test_ci_governance as ci_tests
from test_policy_rules import RuleCase
from test_core import ROOT
from gitflow import xml_policy
from xml.etree import ElementTree as ET


class GovernanceBoundaries(RuleCase):
    def test_mcp_annotations_match_network_and_readonly_behavior(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        from gitflow.mcp import descriptors
        entries = {x['name']: x for x in descriptors()}
        for name in ('check', 'rules', 'doctor'):
            self.assertTrue(entries['gitflow_' + name]['annotations']['readOnlyHint'])
        self.assertTrue(entries['gitflow_organization']['annotations']['openWorldHint'])

    def test_invalid_nullable_and_unknown_rule_options(self):
        self.configured({})
        file = self.path / '.git/gitflow.xml'
        original = xml_policy.decode(file.read_bytes())
        for config in (None, {'GF001': {'severity': []}}, {'GF104': {'severity': 'error', 'options': {'mode': None}}}, {'GF102': {'severity': 'off', 'options': {'pattern': None}}}):
            file.write_bytes(ET.tostring(xml_policy._element('policy',{**original, 'rules': config})))
            self.cli('policy', self.path, '--apply', code=3)

    def test_symlink_baseline_and_duplicate_json_fail_closed(self):
        self.configured({})
        destination = self.path / '.gitflow/baselines/team.json'
        destination.parent.mkdir()
        source = self.path.parent / 'baseline.json'
        source.write_text('{"schema_version":"1.0.0","rules":{},"rules":{},"locked_rules":[]}')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        self.cli('organization', self.path, '--source', source, '--name', 'team', '--sha256', digest, '--apply', code=3)
        self.assertFalse(destination.exists())
        source.write_text('{"schema_version":"1.0.0","rules":{},"locked_rules":[]}')
        destination.symlink_to(source)
        file = self.path / '.gitflow/workflow.json'
        value = json.loads(file.read_text())
        value['extends'] = {'path': '.gitflow/baselines/team.json', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
        file.write_text(json.dumps(value))
        (self.path / '.git/gitflow.xml').unlink()
        self.cli('policy', self.path, '--operation', 'migrate', '--apply', code=3)

    def test_native_managed_integration_checks_v2_metadata(self):
        self.configured({'GF001': {'severity': 'error', 'options': {'allow_merge': False}}}, profile='classic-gitflow')
        self.git('branch', 'develop', 'main')
        self.cli('hooks', self.path, '--apply')
        (self.path / 'feature.txt').write_text('feature')
        self.git('add', 'feature.txt');self.git('commit', '-m', 'feat: feature')
        self.git('switch', 'develop')
        r = self.cli('sync', self.path, '--operation', 'merge', '--source', 'feature/rules', '--apply', code=3)
        self.assertNotEqual(self.git('rev-parse', 'develop'), self.git('rev-parse', 'feature/rules'))
        self.assertTrue((self.path / '.git/MERGE_HEAD').exists())
        (self.path / '.git/MERGE_MSG').write_text('feat: integrate feature\n')
        self.cli('recovery', self.path, '--operation', 'continue', '--apply')
        self.assertFalse((self.path / '.git/MERGE_HEAD').exists())

    def test_trailer_text_in_body_is_not_signoff(self):
        self.configured({'GF103': {'severity': 'error'}})
        self.check('fix: repair\n\nSigned-off-by: Tester <test@example.invalid>\n\nMore body text', code=1)


class CIBoundaries(RuleCase):
    prepare = ci_tests.CIGovernanceTests.prepare
    commit = ci_tests.CIGovernanceTests.commit
    run_check = ci_tests.CIGovernanceTests.run_check

    def test_squash_still_checks_actual_authors(self):
        self.prepare({'GF102': {'severity': 'error', 'options': {'pattern': '^team@example[.]invalid$'}}})
        self.run_check(self.commit('wip'), '--message-mode', 'squash', '--message', 'feat: candidate', code=1)

    def test_squash_unknown_signer_is_unverified(self):
        self.prepare({'GF103': {'severity': 'error'}})
        self.run_check(self.commit('wip'), '--message-mode', 'squash', '--message', 'feat: candidate', code=3)

    def test_shallow_history_is_unverified(self):
        self.prepare()
        head = self.commit('feat: candidate')
        (self.path / '.git/shallow').write_text(self.base + '\n')
        r = self.run_check(head, code=3)
        self.assertEqual(r['reasons'][0]['code'], 'ci_history_incomplete')

    def test_commit_budget_cannot_partially_pass(self):
        self.prepare()
        tree = self.git('rev-parse', 'HEAD^{tree}')
        head = self.base
        for _ in range(501):
            head = self.git('commit-tree', tree, '-p', head, '-m', 'feat: valid')
        r = self.run_check(head, code=3)
        self.assertEqual(r['reasons'][0]['code'], 'ci_range_limit')

    def test_trusted_flattened_rules_cannot_be_weakened_by_candidate_json(self):
        self.prepare({})
        folder = self.path / '.gitflow/baselines';folder.mkdir()
        raw = json.dumps({'schema_version': '1.0.0', 'rules': {'GF001': {'severity': 'error'}}, 'locked_rules': ['GF001']}).encode()
        baseline = folder / 'team.json';baseline.write_bytes(raw)
        file = self.path / '.gitflow/workflow.json'
        value = json.loads(file.read_text());value['rules'] = {}
        value['extends'] = {'path': '.gitflow/baselines/team.json', 'sha256': hashlib.sha256(raw).hexdigest()}
        file.write_text(json.dumps(value));self.git('add', '.gitflow')
        self.base = self.commit('chore: baseline')
        baseline.write_text('{}');value['extends'] = None;file.write_text(json.dumps(value))
        self.git('add', '.gitflow')
        self.trusted_policy['rules']={'GF001':{'severity':'error'}}
        self.trusted_policy['extends']=None
        self.run_check(self.commit('bad candidate'), code=1)

    def test_event_runner_success_and_malformed_event(self):
        self.prepare()
        head = self.commit('feat: candidate')
        event = self.path.parent / 'event.json'
        report = self.path.parent / 'report.json';summary = self.path.parent / 'summary.md'
        command = [sys.executable, str(ROOT / 'scripts/ci_check.py'), '--repo', str(self.path), '--event', str(event), '--output', str(report), '--summary', str(summary)]
        event.write_text(json.dumps({'pull_request': {'base': {'sha': self.base, 'ref': 'main'}, 'head': {'sha': head, 'ref': 'feature/rules'}, 'title': 'feat: candidate', 'body': None}}))
        p = subprocess.run(command, env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertEqual(json.loads(report.read_text())['decision'], 'unverified')
        event.write_text('{}')
        p = subprocess.run(command, env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 3)


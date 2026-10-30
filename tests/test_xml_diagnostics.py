"""Read-only native wiring diagnostics use disposable installations."""
import os
import io
from contextlib import contextmanager
from unittest.mock import patch
import sys
import unittest
from test_core import GitTestCase, ROOT
sys.path.insert(0,str(ROOT/'scripts'))
from gitflow.diagnostics import doctor, describe


@contextmanager
def cp1252_default_text_files():
    """Use real file I/O with Windows' legacy default, retaining explicit codecs."""
    original = io.open
    def open_file(file, mode='r', buffering=-1, encoding=None, errors=None,
                  newline=None, closefd=True, opener=None):
        if 'b' not in mode and encoding in (None, 'locale'):
            encoding = 'cp1252'
        return original(file, mode, buffering, encoding, errors, newline, closefd, opener)
    with patch('io.open', new=open_file):
        yield


class XmlDiagnosticsTests(GitTestCase):
    def ready(self):
        self.repository(); self.activate(); self.cli('hooks',self.path,'--apply')
        self.runtime=self.path/'.gitflow/state/native-runtime'

    def hooks(self):
        return doctor(self.path)['integrations']['native_hooks']

    def test_current_installation_is_configured_and_read_only(self):
        self.ready()
        before=self.git('status','--porcelain')
        self.assertEqual(self.hooks()['status'],'configured')
        self.assertEqual(before,self.git('status','--porcelain'))

    def test_empty_hooks_path_is_external_manager(self):
        self.ready(); self.git('config','core.hooksPath','')
        observed=self.hooks()
        self.assertNotEqual(observed['status'],'configured')
        self.assertEqual(set(observed['entries'].values()),{'external_manager'})

    def test_same_version_runtime_edits_are_not_configured(self):
        self.ready()
        file=self.runtime/'scripts/gitflow/hooks.py'
        with cp1252_default_text_files():
            file.write_text(file.read_text(encoding='utf-8')+'\n# old semantics\n', encoding='utf-8')
        self.assertEqual(self.hooks()['status'],'outdated')

    def test_missing_xml_policy_is_not_configured(self):
        self.ready(); (self.runtime/'scripts/gitflow/xml_policy.py').unlink()
        self.assertEqual(self.hooks()['status'],'outdated')

    @unittest.skipIf(os.name=='nt','POSIX executable mode check')
    def test_nonexecutable_hook_is_not_configured(self):
        self.ready(); (self.path/'.git/hooks/commit-msg').chmod(0o644)
        self.assertNotEqual(self.hooks()['status'],'configured')

    @unittest.skipIf(os.name=='nt','POSIX symlink fixture')
    def test_redirected_runtime_is_not_followed(self):
        self.ready()
        directory=self.runtime/'scripts/gitflow'
        target=self.path.parent/'moved-runtime'; directory.rename(target); directory.symlink_to(target,target_is_directory=True)
        self.assertNotEqual(self.hooks()['status'],'configured')

    @unittest.skipIf(os.name=='nt','POSIX symlink fixture')
    def test_describe_does_not_inspect_legacy_candidate_path(self):
        self.ready()
        (self.path/'.gitflow/workflow.json').symlink_to(self.path.parent/'outside.json')
        self.assertEqual(describe(self.path)['decision'],'allow')

    def test_oversized_runtime_file_is_unverified(self):
        self.ready()
        (self.runtime/'scripts/oversized.py').write_bytes(b'x'*(256*1024+1))
        self.assertEqual(self.hooks()['runtime_status'],'unverified')
        self.assertNotEqual(self.hooks()['status'],'configured')


class PackageTextEncodingTests(unittest.TestCase):
    def test_validator_reads_real_package_with_cp1252_default(self):
        from validate_package import validate_package
        with cp1252_default_text_files():
            self.assertEqual(validate_package(), [])

class PackageVersionTests(unittest.TestCase):
    def test_every_wrapper_and_runtime_share_version(self):
        import json
        from validate_package import version_errors
        expected=json.loads((ROOT/'plugin.json').read_text(encoding='utf-8'))['version']
        self.assertEqual(version_errors(ROOT,expected),[])

    def test_stale_manifest_version_is_rejected(self):
        import json
        import tempfile
        from pathlib import Path
        from validate_package import VERSION_MANIFESTS,version_errors
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in VERSION_MANIFESTS:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(json.dumps({'version':'0.4.0'}),encoding='utf-8')
            (root/'marketplace.json').write_text(json.dumps({'plugins':[{'source':'./','version':'0.4.0'}]}),encoding='utf-8')
            runtime=root/'scripts/gitflow/git.py';runtime.parent.mkdir(parents=True)
            runtime.write_text("VERSION = '0.4.0'\n",encoding='utf-8')
            (root/'dsh/package.json').write_text('{"version":"0.3.0"}',encoding='utf-8')
            self.assertEqual(version_errors(root,'0.4.0'),['Plugin version mismatch: dsh/package.json'])
            (root/'dsh/package.json').write_text('{"version":"0.4.0"}',encoding='utf-8')
            (root/'marketplace.json').write_text(json.dumps({'plugins':[{'source':'./','version':'0.3.0'},{'source':'elsewhere','version':'unrelated'}]}),encoding='utf-8')
            self.assertEqual(version_errors(root,'0.4.0'),['Plugin version mismatch: marketplace.json local entry'])

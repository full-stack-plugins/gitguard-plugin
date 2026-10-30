"""Read-only native wiring diagnostics use disposable installations."""
import os
import sys
import unittest
from test_core import GitTestCase, ROOT
sys.path.insert(0,str(ROOT/'scripts'))
from gitflow.diagnostics import doctor, describe


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
        file.write_text(file.read_text()+'\n# old semantics\n')
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

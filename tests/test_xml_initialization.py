import sys
from pathlib import Path
from test_core import GitTestCase, ROOT
sys.path.insert(0, str(ROOT/'scripts'))

class XmlInitializationTests(GitTestCase):
    def test_init_writes_one_xml_and_managed_guidance_idempotently(self):
        self.repository();a=self.path/'AGENTS.md';a.write_bytes(b'User instructions\r\n')
        self.cli('init',self.path,'--profile','github-flow')
        self.assertEqual(a.read_bytes(),b'User instructions\r\n')
        self.assertFalse((self.path/'.git/gitflow.xml').exists())
        self.cli('init',self.path,'--profile','github-flow','--apply')
        x=self.path/'.git/gitflow.xml';self.assertTrue(x.is_file());self.assertFalse((self.path/'.gitflow/workflow.json').exists())
        self.assertTrue(a.read_bytes().startswith(b'User instructions\r\n'))
        before=(a.read_bytes(),x.read_bytes())
        self.cli('init',self.path,'--profile','github-flow','--apply')
        self.assertEqual((a.read_bytes(),x.read_bytes()),before)

    def test_missing_xml_never_uses_legacy_json(self):
        self.repository();self.activate()
        x=self.path/'.git/gitflow.xml';self.assertTrue(x.exists());x.unlink()
        self.cli('gate',self.path,'--action','commit',code=3)

    def test_bad_markers_preserve_both_targets(self):
        self.repository();a=self.path/'AGENTS.md';a.write_text('user\n<!-- GITGUARD_START -->\n')
        old=a.read_bytes();self.cli('init',self.path,'--profile','github-flow','--apply',code=3)
        self.assertEqual(a.read_bytes(),old);self.assertFalse((self.path/'.git/gitflow.xml').exists())

    def test_expanded_guidance_budget_rejected_before_xml_write(self):
        self.repository();a=self.path/'AGENTS.md';a.write_bytes(b'x'*(256*1024))
        before=a.read_bytes()
        r=self.cli('init',self.path,'--profile','github-flow','--apply',code=3)
        self.assertEqual(r['reasons'][0]['code'],'agents_unsafe')
        self.assertEqual(a.read_bytes(),before)
        self.assertFalse((self.path/'.git/gitflow.xml').exists())

    def test_second_file_failure_is_recoverable_without_policy_overwrite(self):
        from unittest.mock import patch
        from gitflow.initialization import initialize
        from gitflow.git import FlowError
        self.repository()
        with patch('gitflow.initialization.write_guidance',side_effect=OSError('fixture failure')):
            with self.assertRaises(FlowError) as error:
                initialize(self.path,'github-flow',apply=True)
        self.assertEqual(error.exception.code,'init_partial')
        x=self.path/'.git/gitflow.xml';before=x.read_bytes()
        self.assertFalse((self.path/'AGENTS.md').exists())
        self.cli('init',self.path,'--apply')
        self.assertEqual(x.read_bytes(),before)
        self.assertIn('GITGUARD_START',(self.path/'AGENTS.md').read_text())

    def test_noninteractive_new_repository_needs_profile(self):
        self.repository();self.cli('init',self.path,'--apply',code=3)
        self.assertFalse((self.path/'.git/gitflow.xml').exists())

    def test_interactive_selection_and_closed_input(self):
        import io,json
        from unittest.mock import patch
        from gitflow.cli import main
        self.repository()
        for answer,expected in [('github-flow',0),(EOFError(),3)]:
            output=io.StringIO()
            with patch('sys.stdin.isatty',return_value=True), patch('builtins.input',side_effect=answer if isinstance(answer,Exception) else [answer]), patch('sys.stdout',output), patch('sys.stderr',io.StringIO()):
                code=main(['init',str(self.path)])
            self.assertEqual(code,expected)
            self.assertEqual(json.loads(output.getvalue())['decision'],'preview' if expected==0 else 'unverified')
            self.assertFalse((self.path/'.git/gitflow.xml').exists())

    def test_repeat_interactive_init_does_not_reselect_profile(self):
        import io
        from unittest.mock import patch
        from gitflow.cli import main
        self.repository();self.activate('github-flow')
        with patch('sys.stdin.isatty',return_value=True), patch('builtins.input',side_effect=AssertionError('must not prompt')), patch('sys.stdout',io.StringIO()):
            self.assertEqual(main(['init',str(self.path)]),0)

    def test_linked_worktree_reads_same_xml(self):
        self.repository();self.activate('github-flow');other=self.path.parent/'linked'
        self.git('worktree','add','-b','feature/linked',str(other),'main')
        r=self.cli('gate',other,'--action','commit','--message','feat: linked');self.assertEqual(r['role'],'feature')
        self.assertFalse((other/'gitflow.xml').exists())

class XmlCITrustTests(GitTestCase):
    def test_ci_never_uses_pr_or_legacy_policy_as_trust(self):
        self.repository();self.activate('github-flow');oid=self.git('rev-parse','HEAD')
        r=self.cli('check',self.path,'--base',oid,'--head',oid,'--source','feature/x','--target','main',code=3)
        self.assertEqual(r['reasons'][0]['code'],'ci_policy_unconfigured')

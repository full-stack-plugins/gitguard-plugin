"""Init selects XML policy; host installation alone owns instruction files."""
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch
from test_core import GitTestCase, ROOT
sys.path.insert(0, str(ROOT / 'scripts'))


class XmlInitializationTests(GitTestCase):
    def initialize(self, profile='github-flow'):
        return self.cli('init', self.path, '--profile', profile, '--apply')

    def test_init_writes_only_xml_and_leaves_absent_agents_absent(self):
        self.repository()
        before={p:p.read_bytes() for p in self.path.iterdir() if p.is_file()}
        self.cli('init',self.path,'--profile','github-flow')
        self.assertFalse((self.path/'.git/gitflow.xml').exists())
        self.assertFalse((self.path/'AGENTS.md').exists())
        self.initialize()
        self.assertTrue((self.path/'.git/gitflow.xml').is_file())
        self.assertFalse((self.path/'AGENTS.md').exists())
        self.assertFalse((self.path/'.gitflow/workflow.json').exists())
        self.assertEqual({p:p.read_bytes() for p in self.path.iterdir() if p.is_file()},before)
        self.assertEqual(self.git('status','--porcelain'),'')

    def test_arbitrary_edited_malformed_and_large_agents_are_untouched(self):
        self.repository();a=self.path/'AGENTS.md'
        for raw in (b'Human\r\n',b'<!-- GITGUARD_START -->edited',
                    b'<!-- GITGUARD_END -->bad order<!-- GITGUARD_START -->',
                    b'<!-- GITGUARD_POLICY_GUIDANCE_V1_START -->unknown',
                    b'\xff\x00not utf8', b'x'*(256*1024+1)):
            with self.subTest(raw=raw[:50]):
                a.write_bytes(raw);before=(a.read_bytes(),a.stat().st_mtime_ns)
                self.initialize()
                self.assertEqual((a.read_bytes(),a.stat().st_mtime_ns),before)

    def test_symlink_and_nonregular_agents_are_irrelevant(self):
        import os
        self.repository();a=self.path/'AGENTS.md';outside=self.path.parent/'outside'
        outside.write_bytes(b'Preserve external guidance')
        a.symlink_to(outside)
        self.initialize();self.assertTrue(a.is_symlink());self.assertEqual(outside.read_bytes(),b'Preserve external guidance')
        a.unlink();a.mkdir();self.initialize();self.assertTrue(a.is_dir())
        a.rmdir()
        if hasattr(os,'mkfifo'):
            os.mkfifo(a);self.initialize();self.assertFalse(a.is_file());a.unlink()

    def test_idempotence_does_not_rewrite_policy_or_replace_profile(self):
        self.repository();self.initialize();x=self.path/'.git/gitflow.xml'
        before=(x.read_bytes(),x.stat().st_mtime_ns)
        self.cli('init',self.path,'--apply')
        self.assertEqual((x.read_bytes(),x.stat().st_mtime_ns),before)
        self.cli('init',self.path,'--profile','classic-gitflow','--apply',code=3)
        self.assertEqual((x.read_bytes(),x.stat().st_mtime_ns),before)

    def test_missing_xml_never_uses_legacy_json(self):
        self.repository();self.initialize();(self.path/'.git/gitflow.xml').unlink()
        folder=self.path/'.gitflow';folder.mkdir(exist_ok=True)
        (folder/'workflow.json').write_text((ROOT/'profiles/github-flow.json').read_text())
        self.cli('gate',self.path,'--action','commit',code=3)
        self.cli('init',self.path,'--profile','github-flow','--apply',code=3)

    def test_migration_is_xml_only_with_no_agents_or_unusable_agents(self):
        self.repository();folder=self.path/'.gitflow';folder.mkdir()
        source=folder/'workflow.json';source.write_text((ROOT/'profiles/github-flow.json').read_text())
        original=source.read_bytes()
        self.cli('policy',self.path,'--operation','migrate')
        self.assertFalse((self.path/'AGENTS.md').exists())
        self.cli('policy',self.path,'--operation','migrate','--apply')
        self.assertFalse((self.path/'AGENTS.md').exists());self.assertEqual(source.read_bytes(),original)
        x=self.path/'.git/gitflow.xml';x.unlink()
        a=self.path/'AGENTS.md';a.symlink_to(self.path.parent/'missing-guidance')
        self.cli('policy',self.path,'--operation','migrate','--apply')
        self.assertTrue(a.is_symlink());self.assertFalse(a.exists());self.assertTrue(x.exists())

    def test_removed_guidance_flag_is_rejected_cli_and_mcp(self):
        from gitflow.mcp import call,descriptors
        from gitflow.git import FlowError
        self.repository()
        self.cli('init',self.path,'--profile','github-flow','--migrate-guidance','--apply',code=2)
        self.assertFalse((self.path/'.git/gitflow.xml').exists())
        for name in ('gitflow_init','gitflow_policy'):
            descriptor=next(d for d in descriptors() if d['name']==name)
            self.assertNotIn('migrate_guidance',descriptor['inputSchema']['properties'])
            with self.assertRaises(FlowError):call(name,{'path':str(self.path),'migrate_guidance':True})

    def test_noninteractive_new_repository_needs_profile(self):
        self.repository();self.cli('init',self.path,'--apply',code=3)
        self.assertFalse((self.path/'.git/gitflow.xml').exists())

    def test_interactive_selection_and_closed_input(self):
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
        from gitflow.cli import main
        self.repository();self.initialize()
        with patch('sys.stdin.isatty',return_value=True),patch('builtins.input',side_effect=AssertionError('must not prompt')),patch('sys.stdout',io.StringIO()):
            self.assertEqual(main(['init',str(self.path)]),0)

    def test_linked_worktree_reads_same_xml(self):
        self.repository();self.initialize();other=self.path.parent/'linked'
        self.git('worktree','add','-b','feature/linked',str(other),'main')
        r=self.cli('gate',other,'--action','commit','--message','feat: linked')
        self.assertEqual(r['role'],'feature');self.assertFalse((other/'gitflow.xml').exists())
        self.assertFalse((other/'AGENTS.md').exists())


class XmlCITrustTests(GitTestCase):
    def test_ci_never_uses_pr_or_legacy_policy_as_trust(self):
        self.repository();self.cli('init',self.path,'--profile','github-flow','--apply');oid=self.git('rev-parse','HEAD')
        r=self.cli('check',self.path,'--base',oid,'--head',oid,'--source','feature/x','--target','main',code=3)
        self.assertEqual(r['reasons'][0]['code'],'ci_policy_unconfigured')

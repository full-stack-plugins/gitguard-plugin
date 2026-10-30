"""Native hook acceptance uses disposable repositories and local bare remotes."""
import os
import shlex
import subprocess
import sys
from test_core import GitTestCase, ROOT
sys.path.insert(0, str(ROOT / 'scripts'))
from gitflow.hooks import pretool
from gitflow.git import require_repo
from gitflow.policy import load
from gitflow.xml_policy import write_policy


class XmlNativeHookTests(GitTestCase):
    def ready(self):
        self.repository()
        self.activate()
        self.git('branch', 'develop')
        self.git('switch', '-c', 'feature/native', 'develop')
        self.git('commit', '--allow-empty', '-m', 'feat: native')

    def native(self, *args):
        return subprocess.run(['git', '-C', str(self.path), *args], env=self.env,
                              text=True, encoding="utf-8", capture_output=True, timeout=30)

    def install(self):
        self.cli('hooks', self.path, '--apply')

    def test_pretool_native_merge_direction_and_no_mutation(self):
        self.ready(); self.git('switch', 'develop')
        before = (self.git('show-ref'), self.git('ls-files', '--stage'), self.git('status', '--porcelain'))
        good = pretool({'cwd': str(self.path), 'tool_input': {'command': 'git merge feature/native'}})
        self.assertEqual(good['hookSpecificOutput']['permissionDecision'], 'allow')
        self.git('switch', 'feature/native')
        bad = pretool({'cwd': str(self.path), 'tool_input': {'command': 'git merge develop'}})
        self.assertEqual(bad['hookSpecificOutput']['permissionDecision'], 'deny')
        self.git('switch', 'develop')
        self.assertEqual(before, (self.git('show-ref'), self.git('ls-files', '--stage'), self.git('status', '--porcelain')))
        dynamic = pretool({'cwd': str(self.path), 'tool_input': {'command': 'git merge "$SOURCE"'}})
        self.assertEqual(dynamic['hookSpecificOutput']['permissionDecision'], 'ask')

    def test_installed_commit_and_native_merge(self):
        self.ready(); self.install()
        hook = self.path / '.git/hooks/commit-msg'
        self.assertIn(shlex.quote(sys.executable), hook.read_text())
        self.assertEqual(self.native('commit', '--allow-empty', '-m', 'feat: allowed').returncode, 0)
        self.git('switch', 'develop')
        self.assertEqual(self.native('commit', '--allow-empty', '-m', 'feat: forbidden').returncode, 1)
        merge = self.native('merge', '--no-ff', 'feature/native', '-m', 'Merge feature/native')
        self.assertEqual(merge.returncode, 0, merge.stderr)

    def test_push_checks_every_pending_message(self):
        self.ready()
        facts=require_repo(self.path)
        policy,_=load(facts)
        policy['commit_message_pattern']=r'(chore|docs|feat): .+'
        write_policy(facts,policy)
        remote = self.path.parent / 'remote.git'
        self.git('init', '--bare', str(remote)); self.git('remote', 'add', 'origin', str(remote))
        self.install()
        self.assertEqual(self.native('push', 'origin', 'feature/native').returncode, 0)
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-m', 'bad message')
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-m', 'feat: good tip')
        push = self.native('push', 'origin', 'feature/native')
        self.assertNotEqual(push.returncode, 0)
        self.assertIn('deny', push.stderr)

    def test_push_rejects_bad_historical_author_on_new_branch(self):
        self.ready()
        facts=require_repo(self.path); policy,_=load(facts)
        policy['schema_version']='2.0.0'
        policy['extends']=None
        policy['rules']={'GF102': {'severity':'error', 'options':{'pattern':r'.+@example\.invalid'}}}
        write_policy(facts,policy)
        self.git('commit', '--allow-empty', '--author=Wrong <wrong@else.invalid>', '-m', 'feat: bad author')
        self.git('commit', '--allow-empty', '-m', 'feat: good tip')
        remote=self.path.parent/'remote.git'
        self.git('init','--bare',str(remote)); self.git('remote','add','origin',str(remote)); self.install()
        result=self.native('push','origin','feature/native')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('deny',result.stderr)

    def test_ambiguous_native_merge_blocks_without_claiming_denial(self):
        self.ready(); self.git('branch','feature/alias'); self.install(); self.git('switch','develop')
        result=self.native('merge','--no-ff','feature/native','-m','Merge native')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('unverified',result.stderr)
        self.assertTrue((self.path/'.git/MERGE_HEAD').exists())

    def test_existing_hook_and_manager_are_preserved(self):
        self.ready()
        hook=self.path/'.git/hooks/commit-msg'; hook.write_text('existing\n')
        self.cli('hooks',self.path,'--apply',code=3)
        self.assertEqual(hook.read_text(),'existing\n')
        hook.unlink(); self.git('config','core.hooksPath','custom-hooks')
        self.cli('hooks',self.path,'--apply',code=3)
        self.assertEqual(self.git('config','core.hooksPath'),'custom-hooks')

    def push_input(self, line):
        from test_core import CLI
        return subprocess.run([sys.executable,str(CLI),'native','--kind','pre-push','--','origin','unused'],
                              cwd=self.path, env=self.env, input=line+'\n', text=True, encoding='utf-8',
                              capture_output=True, timeout=30)

    def test_push_ref_oid_unknown_history_and_non_ff_fail_closed(self):
        self.ready()
        head=self.git('rev-parse','HEAD'); base=self.git('rev-parse','develop')
        ref='refs/heads/feature/native'
        bads=[f'{ref} {base} {ref} '+ '0'*40,
              f'{ref} {head} {ref} '+ '1'*40,
              f'refs/tags/v1 {head} refs/tags/v1 '+ '0'*40,
              f'{ref} '+ '0'*40 + f' {ref} {head}']
        for line in bads:
            result=self.push_input(line)
            self.assertNotEqual(result.returncode,0,line)
            self.assertIn('unverified',result.stderr)
        self.git('switch','develop'); self.git('commit','--allow-empty','-m','feat: diverged')
        diverged=self.git('rev-parse','HEAD')
        result=self.push_input(f'{ref} {head} {ref} {diverged}')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('deny',result.stderr)

    def test_linked_worktree_uses_shared_policy_and_own_merge_target(self):
        self.ready()
        linked=self.path.parent/'linked'
        self.git('worktree','add',str(linked),'develop')
        result=pretool({'cwd':str(linked),'tool_input':{'command':'git merge feature/native'}})
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'allow')
        result=pretool({'cwd':str(self.path),'tool_input':{'command':'git merge develop'}})
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'deny')

    def test_pretool_rejects_dwim_shadow_of_local_merge_source(self):
        self.ready()
        self.git('update-ref','refs/feature/native',self.git('rev-parse','develop'))
        self.git('switch','develop')
        result=pretool({'cwd':str(self.path),'tool_input':{'command':'git merge feature/native'}})
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'ask')
        exact=pretool({'cwd':str(self.path),'tool_input':{'command':'git merge refs/heads/feature/native'}})
        self.assertEqual(exact['hookSpecificOutput']['permissionDecision'],'allow')

    def test_branch_creation_and_merge_options_remain_unverified(self):
        self.ready()
        for command in ('git switch -c feature/new', 'git branch feature/new',
                        'git -c merge.ff=false merge develop', 'git merge --no-ff develop',
                        'git merge -- develop'):
            result=pretool({'cwd':str(self.path),'tool_input':{'command':command}})
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'],'ask',command)
        self.assertNotIn('feature/new',self.git('branch','--format=%(refname:short)'))

    def test_push_replacement_objects_cannot_mask_bad_pending_message(self):
        self.ready()
        facts=require_repo(self.path); policy,_=load(facts)
        policy['commit_message_pattern']=r'(chore|docs|feat): .+'
        write_policy(facts,policy)
        remote=self.path.parent/'remote.git'
        self.git('init','--bare',str(remote)); self.git('remote','add','origin',str(remote))
        self.install()
        self.assertEqual(self.native('push','origin','feature/native').returncode,0)
        self.git('-c','core.hooksPath=/dev/null','commit','--allow-empty','-m','bad pending')
        bad=self.git('rev-parse','HEAD'); tree=self.git('rev-parse','HEAD^{tree}')
        parent=self.git('rev-parse','HEAD^')
        replacement=self.git('commit-tree',tree,'-p',parent,'-m','feat: disguised')
        self.git('replace',bad,replacement)
        result=self.native('push','origin','feature/native')
        self.assertNotEqual(result.returncode,0,result.stderr)
        self.assertIn('deny',result.stderr)
        actual=self.git('rev-parse','refs/heads/feature/native',cwd=remote)
        self.assertNotEqual(actual,bad)

    def test_native_merge_enforces_top_level_message_pattern(self):
        self.ready()
        facts=require_repo(self.path); policy,_=load(facts)
        policy['commit_message_pattern']=r'feat: .+'
        write_policy(facts,policy)
        self.install(); self.git('switch','develop')
        result=self.native('merge','--no-ff','feature/native','-m','bad merge message')
        self.assertNotEqual(result.returncode,0,result.stderr)
        self.assertIn('deny',result.stderr)
        self.assertTrue((self.path/'.git/MERGE_HEAD').exists())

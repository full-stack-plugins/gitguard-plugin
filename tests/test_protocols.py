"""真实标准输入/输出协议，不通过函数直调冒充宿主接线。"""
import json
import os
from pathlib import Path
import subprocess
import sys
from test_core import GitTestCase, CLI

class ProtocolTests(GitTestCase):
    def hook(self,event,command=None,cwd=None):
        data={'hook_event_name':event,'cwd':str(cwd or self.path),'tool_name':'Bash',
              'tool_input':{'command':command or 'git status'}}
        p=subprocess.run([sys.executable,str(CLI),'hook','--event',event],input=json.dumps(data),text=True,capture_output=True,env=self.env)
        self.assertEqual(p.returncode,0,p.stderr)
        return json.loads(p.stdout)

    def test_hook_blocks_main_commit_and_allows_read_commands(self):
        self.repository();self.activate(mode='local')
        r=self.hook('PreToolUse','git commit -m test')
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'deny')
        r=self.hook('PreToolUse','git status')
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'allow')

    def test_hook_follows_git_C_and_simple_cd_chains(self):
        self.repository();self.activate(mode='local')
        empty=self.path.parent/'empty';empty.mkdir()
        r=self.hook('PreToolUse',f'git -C "{self.path}" commit -m test',cwd=empty)
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'deny')
        r=self.hook('PreToolUse',f'cd "{self.path}" && git commit -m test',cwd=empty)
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'deny')

    def test_hook_does_not_execute_dynamic_or_quoted_text(self):
        self.repository();self.activate(mode='local')
        r=self.hook('PreToolUse','echo "git commit -m test"')
        self.assertNotIn('hookSpecificOutput',r)
        r=self.hook('PreToolUse','git -C "$REPO" commit -m test')
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'ask')
        r=self.hook('PreToolUse','git -c alias.save=commit save -m test')
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'ask')

    def test_hook_denies_force_push_unknown_flags(self):
        self.repository();self.activate(mode='local')
        r=self.hook('PreToolUse','git push --force origin main')
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'deny')

    def test_session_context_and_no_git_choice_persistence(self):
        data=self.path.parent/'plugin-data';self.env['PLUGIN_DATA']=str(data)
        r=self.hook('SessionStart')
        self.assertEqual(r,{})
        self.assertIn('未受 Git 管理',self.cli('context',self.path)['context'])
        self.cli('context',self.path,'--choice','defer','--apply')
        r=self.hook('SessionStart')
        self.assertEqual(r,{})
        explicit=self.cli('context',self.path)['context']
        self.assertIn('暂不启用',explicit)
        self.assertNotIn('是否初始化',explicit)
        self.repository();self.activate(mode='local')
        r=self.hook('SessionStart')
        self.assertIn('classic-gitflow',r['hookSpecificOutput']['additionalContext'])

    def test_mcp_initialize_list_call_closed_parameters(self):
        self.repository();self.activate(mode='local')
        messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'test','version':'1'}}},
                  {'jsonrpc':'2.0','method':'notifications/initialized'},
                  {'jsonrpc':'2.0','id':2,'method':'tools/list'},
                  {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'gitflow_gate','arguments':{'path':str(self.path),'action':'commit'}}},
                  {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'gitflow_branch','arguments':{'path':str(self.path),'operation':'create','name':'feature/a','source':'main','apply':'yes'}}}]
        p=subprocess.run([sys.executable,str(CLI),'mcp'],input='\n'.join(json.dumps(m) for m in messages)+'\n',text=True,capture_output=True,env=self.env)
        self.assertEqual(p.returncode,0,p.stderr)
        responses=[json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual(len(responses),4)
        self.assertEqual(responses[0]['result']['protocolVersion'],'2025-06-18')
        tools=responses[1]['result']['tools'];self.assertGreaterEqual(len(tools),8)
        self.assertTrue(next(t for t in tools if t['name']=='gitflow_discover')['annotations']['readOnlyHint'])
        result=json.loads(responses[2]['result']['content'][0]['text'])
        self.assertEqual(result['decision'],'deny')
        self.assertTrue(responses[3]['result']['isError'])
        self.assertNotIn('feature/a',self.git('branch','--format=%(refname:short)'))

    def test_native_hook_install_preview_and_existing_hooks_preserved(self):
        self.repository();self.activate(mode='local')
        self.cli('hooks',self.path)
        hooks=Path(self.git('rev-parse','--absolute-git-dir'))/'hooks'
        self.assertFalse((hooks/'commit-msg').exists())
        (hooks/'commit-msg').write_text('#!/bin/sh\nexit 0\n')
        self.cli('hooks',self.path,'--apply',code=3)
        self.assertEqual((hooks/'commit-msg').read_text(),'#!/bin/sh\nexit 0\n')

    def test_native_installed_commit_hook_actually_blocks_then_allows(self):
        self.repository();self.activate(mode='local');self.cli('hooks',self.path,'--apply')
        p=subprocess.run(['git','-C',str(self.path),'commit','--allow-empty','-m','blocked'],env=self.env,text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0,p.stdout)
        self.git('switch','-c','feature/native')
        self.git('commit','--allow-empty','-m','allowed')

    def test_mcp_rejects_invalid_init_mode_without_side_effects(self):
        self.repository()
        sys.path.insert(0,str(CLI.parent))
        from gitflow.mcp import call
        from gitflow.git import FlowError
        with self.assertRaises(FlowError):
            call('gitflow_init',{'path':str(self.path),'profile':'classic-gitflow','mode':'invalid','apply':True})
        self.assertFalse((self.path/'.gitflow').exists())

    def test_hook_marks_git_inside_command_substitution_unverified(self):
        self.repository();self.activate(mode='local')
        r=self.hook('PreToolUse','echo "$(git commit -m test)"')
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'ask')

    def test_hook_does_not_flatten_newline_shell_commands(self):
        self.repository();self.activate(mode='local')
        r=self.hook('PreToolUse','git status\ngit commit --allow-empty -m blocked')
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'ask')
        r=self.hook('PreToolUse','/usr/bin/git commit -m blocked')
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'deny')

    def test_hook_checks_ordinary_native_merge_direction(self):
        self.repository();self.activate(mode='local');self.git('branch','develop');self.git('branch','feature/a','develop');self.git('switch','develop')
        r=self.hook('PreToolUse','git merge feature/a')
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'allow')

    def test_native_hooks_allow_bound_plugin_integration(self):
        self.repository();self.activate(mode='local');self.git('branch','develop');self.cli('hooks',self.path,'--apply')
        self.git('switch','-c','feature/a','develop');(self.path/'new').write_text('new');self.git('add','.');self.git('commit','-m','feat')
        self.git('switch','develop')
        r=self.cli('sync',self.path,'--operation','merge','--source','feature/a','--apply')
        self.assertEqual(r['decision'],'applied')

    def test_native_push_hook_rejects_non_fast_forward_even_with_force(self):
        self.repository();self.activate(mode='local');self.cli('hooks',self.path,'--apply')
        remote=self.path.parent/'remote.git';self.git('init','--bare',str(remote));self.git('remote','add','origin',str(remote))
        self.git('switch','-c','feature/a');old=self.git('rev-parse','HEAD')
        self.git('commit','--allow-empty','-m','new');new=self.git('rev-parse','HEAD');self.git('push','origin','feature/a')
        self.git('update-ref','refs/heads/feature/a',old)
        p=subprocess.run(['git','-C',str(self.path),'push','--force','origin','feature/a'],env=self.env,text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(self.git('ls-remote','origin','refs/heads/feature/a').split()[0],new)

    def test_native_hook_allows_bound_conflict_continue(self):
        self.repository();self.activate(mode='local');self.git('branch','develop');self.cli('hooks',self.path,'--apply')
        for branch,value in [('feature/a','a'),('feature/b','b')]:
            self.git('switch','-c',branch,'develop');(self.path/'app.txt').write_text(value);self.git('add','.');self.git('commit','-m',value)
        self.git('switch','develop');self.cli('sync',self.path,'--operation','merge','--source','feature/b','--apply')
        self.cli('sync',self.path,'--operation','merge','--source','feature/a','--apply',code=3)
        (self.path/'app.txt').write_text('resolved');self.git('add','app.txt')
        self.cli('recovery',self.path,'--operation','continue','--apply')
        self.assertEqual(self.cli('discover',self.path)['operation_states'],[])

    def test_native_hotfix_finish_covers_active_release(self):
        self.repository();self.activate(mode='local');self.git('branch','develop');self.git('branch','release/1.0');self.cli('hooks',self.path,'--apply')
        self.cli('release',self.path,'--operation','start','--name','hotfix/security','--source','main','--apply')
        self.git('switch','hotfix/security');(self.path/'security').write_text('fix');self.git('add','.');self.git('commit','-m','fix')
        r=self.cli('release',self.path,'--operation','finish','--name','hotfix/security','--apply')
        self.assertEqual(r['remaining_targets'],[])

    def test_hook_never_approves_native_rebase_short_ref_semantics(self):
        self.repository();self.activate(mode='local');self.git('branch','develop');self.git('switch','-c','feature/a','develop')
        r=self.hook('PreToolUse','git rebase develop')
        self.assertEqual(r['hookSpecificOutput']['permissionDecision'],'ask')

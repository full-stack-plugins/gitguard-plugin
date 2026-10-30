"""负例、防误判与真实冲突恢复。"""
import json
from pathlib import Path
from test_core import GitTestCase
from gitflow import xml_policy
from xml.etree import ElementTree as ET

class BoundaryTests(GitTestCase):
    def ready(self):
        self.repository();self.activate(mode='local');self.git('branch','develop')

    def test_unknown_source_branch_is_unverified(self):
        self.ready()
        self.cli('gate',self.path,'--action','merge','--source','feature/nonexistent','--target','develop',code=3)

    def test_complex_regex_is_rejected_before_it_can_block_hook(self):
        self.repository();self.activate()
        file=self.path/'.git/gitflow.xml';policy=xml_policy.decode(file.read_bytes())
        policy['roles']['feature']['pattern']='feature/(a|aa)+'
        file.write_bytes(ET.tostring(xml_policy._element('policy',policy)))
        self.cli('policy',self.path,'--apply',code=3)

    def test_shared_metadata_symlink_cannot_escape(self):
        self.repository()
        outside=self.path.parent/'outside';outside.mkdir()
        (self.path/'.gitflow').symlink_to(outside,target_is_directory=True)
        self.cli('init',self.path,'--profile','classic-gitflow','--apply',code=3)
        self.assertEqual(list(outside.iterdir()),[])

    def test_generated_markdown_symlink_is_rejected(self):
        self.repository()
        directory=self.path/'.gitflow';directory.mkdir()
        outside=self.path.parent/'outside.md';outside.write_text('preserve')
        (self.path/'AGENTS.md').symlink_to(outside)
        self.cli('init',self.path,'--profile','classic-gitflow','--apply',code=3)
        self.assertEqual(outside.read_text(),'preserve')

    def test_release_conflict_retains_partial_targets_and_abort_recovers(self):
        self.ready()
        self.git('switch','-c','release/1.0','develop');(self.path/'app.txt').write_text('release')
        self.git('add','.');self.git('commit','-m','release')
        self.git('switch','main');(self.path/'app.txt').write_text('main')
        self.git('add','.');self.git('commit','-m','main');self.git('switch','release/1.0')
        r=self.cli('release',self.path,'--operation','finish','--name','release/1.0','--apply',code=3)
        self.assertIn('main',r['remaining_targets']);self.assertEqual(r['after']['branch'],'main')
        self.assertIn('MERGE_HEAD',r['after']['operation_states'])
        self.cli('recovery',self.path,'--operation','abort','--apply')
        self.assertEqual(self.git('branch','--show-current'),'main')
        self.assertEqual((self.path/'app.txt').read_text(),'main')

    def test_linked_worktree_branch_switch_is_refused(self):
        self.ready();other=self.path.parent/'other';self.git('worktree','add',str(other),'develop')
        self.cli('branch',self.path,'--operation','switch','--name','develop','--apply',code=3)

    def test_hotfix_finish_includes_active_release(self):
        self.ready();self.git('branch','release/1.0','develop')
        self.cli('release',self.path,'--operation','start','--name','hotfix/security','--source','main','--apply')
        self.git('switch','hotfix/security');(self.path/'security').write_text('fix');self.git('add','.');self.git('commit','-m','fix')
        r=self.cli('release',self.path,'--operation','finish','--name','hotfix/security','--apply')
        self.assertIn('release/1.0',r['targets']);self.assertEqual(r['remaining_targets'],[])

    def test_microsoft_backport_and_git_maintainer_direction_are_distinct(self):
        self.repository();self.activate('microsoft-release',mode='local');self.git('branch','release/1.0')
        (self.path/'fix').write_text('fix');self.git('add','.');self.git('commit','-m','fix')
        commit=self.git('rev-parse','HEAD')
        self.cli('release',self.path,'--operation','backport','--targets','release/1.0','--commit',commit,'--apply')
        self.assertIn('fix',self.git('ls-tree','--name-only','release/1.0'))
        before=self.git('rev-parse','release/1.0')
        self.cli('release',self.path,'--operation','backport','--targets','release/1.0','--commit',commit,'--apply')
        self.assertEqual(before,self.git('rev-parse','release/1.0'))

    def test_running_journal_blocks_unrelated_apply_until_review(self):
        self.ready()
        file=self.path/'.gitflow/state/worktrees/main/journal.json'
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text(json.dumps({'schema_version':'1.0.0','entries':[{'id':'interrupted','action':'sync.push','status':'running','before':{},'steps':[],'commands':[]}]}))
        self.cli('branch',self.path,'--operation','create','--name','feature/new','--source','develop','--apply',code=3)
        self.assertNotIn('feature/new',self.git('branch','--format=%(refname:short)'))

    def test_corrupt_git_directory_is_not_reported_as_absent(self):
        (self.path/'.git').mkdir()
        self.cli('discover',self.path,code=3)

    def test_ambiguous_serial_repetitions_are_rejected(self):
        self.repository();self.activate()
        file=self.path/'.git/gitflow.xml';policy=xml_policy.decode(file.read_bytes())
        policy['roles']['feature']['pattern']='feature/a*a*a*a*a*a*b'
        file.write_bytes(ET.tostring(xml_policy._element('policy',policy)))
        self.cli('policy',self.path,'--apply',code=3)

    def test_same_name_tag_cannot_replace_real_release_branch(self):
        self.ready();base=self.git('rev-parse','HEAD')
        self.git('switch','-c','release/1.0','develop');(self.path/'release').write_text('release');self.git('add','.');self.git('commit','-m','release')
        source=self.git('rev-parse','refs/heads/release/1.0');self.git('tag','release/1.0',base)
        r=self.cli('discover',self.path);self.assertEqual(r['branch'],'release/1.0')
        r=self.cli('release',self.path,'--operation','finish','--name','release/1.0','--apply')
        for target in ('main','develop'):
            self.assertEqual(self.git('merge-base',source,'refs/heads/'+target),source)
        self.assertEqual(r['remaining_targets'],[])

    def test_invalid_origins_fail_before_creating_any_ref(self):
        self.ready();file=self.path/'.gitflow/state/origins.json';file.write_text('[]')
        self.cli('branch',self.path,'--operation','create','--name','feature/bad','--source','develop','--apply',code=3)
        self.assertNotIn('feature/bad',self.git('branch','--format=%(refname:short)'))

    def test_incomplete_origin_is_unknown_in_audit(self):
        self.ready();self.git('branch','feature/a','develop')
        file=self.path/'.gitflow/state/origins.json';file.write_text(json.dumps({'feature/a':{}}))
        r=self.cli('audit',self.path)
        self.assertTrue(any(o['code']=='branch_origin_unknown' and o.get('branch')=='feature/a' for o in r['observations']))

    def test_corrupt_journal_entry_does_not_crash_after_mutating(self):
        self.ready();file=self.path/'.gitflow/state/worktrees/main/journal.json';file.parent.mkdir(parents=True,exist_ok=True);file.write_text(json.dumps({'schema_version':'1.0.0','entries':[None]}))
        self.cli('branch',self.path,'--operation','create','--name','feature/bad','--source','develop','--apply',code=3)
        self.assertNotIn('feature/bad',self.git('branch','--format=%(refname:short)'))

    def test_resume_verifies_completed_merge_without_repeating_commit(self):
        self.ready();self.git('switch','-c','feature/new','develop');(self.path/'new').write_text('new');self.git('add','.');self.git('commit','-m','new');self.git('switch','develop')
        result=self.cli('sync',self.path,'--operation','merge','--source','feature/new','--apply')
        file=self.path/'.gitflow/state/worktrees/main/journal.json';journal=json.loads(file.read_text())
        journal['entries'][-1]['status']='unknown';journal['entries'][-1]['steps'][-1]['status']='running';file.write_text(json.dumps(journal))
        before=self.git('rev-parse','HEAD')
        self.cli('recovery',self.path,'--operation','resume','--operation-id',result['operation_id'],'--apply')
        self.assertEqual(self.git('rev-parse','HEAD'),before)
        self.cli('branch',self.path,'--operation','create','--name','feature/after','--source','develop','--apply')

    def test_plan_ref_change_before_lock_is_rejected(self):
        self.ready();self.git('switch','-c','feature/changed','develop');self.git('commit','--allow-empty','-m','new');new=self.git('rev-parse','HEAD');self.git('switch','main')
        import sys
        from contextlib import contextmanager
        from unittest.mock import patch
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        from gitflow.operations import branch
        from gitflow.git import FlowError
        @contextmanager
        def changed(_):
            self.git('update-ref','refs/heads/develop',new)
            yield
        with patch('gitflow.operations.locked',changed):
            with self.assertRaises(FlowError):branch(self.path,'create',name='feature/new',source='develop',apply=True)
        self.assertNotIn('feature/new',self.git('branch','--format=%(refname:short)'))

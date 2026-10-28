"""Platform-neutral real Git safety acceptance; only disposable repos are mutated."""
from contextlib import contextmanager
import json
import subprocess
import sys
from unittest.mock import patch
from test_core import GitTestCase, CLI, ROOT

sys.path.insert(0, str(ROOT / 'scripts'))
from gitflow.git import FlowError
from gitflow.operations import branch


class NativeGitSafetyTests(GitTestCase):
    def cli(self, *args, code=0, cwd=None):
        result = subprocess.run([sys.executable, '-B', str(CLI), *map(str, args), '--json'],
                                env=self.env, cwd=cwd, capture_output=True,
                                text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, code, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def ready(self):
        self.repository()
        self.activate(mode='local')
        self.git('branch', 'develop')

    def test_candidate_ref_changed_before_lock_is_rejected(self):
        self.ready()
        self.git('switch', '-c', 'feature/changed', 'develop')
        self.git('commit', '--allow-empty', '-m', 'new')
        changed = self.git('rev-parse', 'HEAD')
        self.git('switch', 'main')
        @contextmanager
        def changed_before_lock(_):
            self.git('update-ref', 'refs/heads/develop', changed)
            yield
        with patch('gitflow.operations.locked', changed_before_lock):
            with self.assertRaises(FlowError) as error:
                branch(self.path, 'create', name='feature/new', source='develop', apply=True)
        self.assertEqual(error.exception.code, 'repository_changed')
        self.assertNotIn('feature/new', self.git('branch', '--format=%(refname:short)'))

    def test_conflict_retains_state_and_explicit_abort_preserves_original_content(self):
        self.ready()
        self.git('switch', '-c', 'release/1.0', 'develop')
        (self.path / 'app.txt').write_text('release', encoding='utf-8')
        self.git('add', '.'); self.git('commit', '-m', 'release')
        self.git('switch', 'main')
        (self.path / 'app.txt').write_text('main', encoding='utf-8')
        self.git('add', '.'); self.git('commit', '-m', 'main')
        original = self.git('rev-parse', 'HEAD')
        self.git('switch', 'release/1.0')
        result = self.cli('release', self.path, '--operation', 'finish', '--name', 'release/1.0', '--apply', code=3)
        self.assertIn('MERGE_HEAD', result['after']['operation_states'])
        self.assertIn('main', result['remaining_targets'])
        self.cli('recovery', self.path, '--operation', 'abort', '--apply')
        self.assertEqual(self.git('rev-parse', 'HEAD'), original)
        self.assertEqual((self.path / 'app.txt').read_text(encoding='utf-8'), 'main')

    def test_unknown_journal_blocks_unrelated_apply_and_resume_does_not_replay_merge(self):
        self.ready()
        self.git('switch', '-c', 'feature/new', 'develop')
        (self.path / 'new').write_text('new', encoding='utf-8')
        self.git('add', '.'); self.git('commit', '-m', 'new')
        self.git('switch', 'develop')
        result = self.cli('sync', self.path, '--operation', 'merge', '--source', 'feature/new', '--apply')
        journal_path = self.path / '.gitflow/state/worktrees/main/journal.json'
        journal = json.loads(journal_path.read_text(encoding='utf-8'))
        # Crash window: Git completed but the final journal receipt was not durable.
        journal['entries'][-1]['status'] = 'unknown'
        journal['entries'][-1]['steps'][-1]['status'] = 'running'
        journal_path.write_text(json.dumps(journal), encoding='utf-8')
        original = self.git('rev-parse', 'HEAD')
        blocked = self.cli('branch', self.path, '--operation', 'create', '--name', 'feature/blocked', '--source', 'develop', '--apply', code=3)
        self.assertEqual(blocked['reasons'][0]['code'], 'operation_unknown')
        self.assertNotIn('feature/blocked', self.git('branch', '--format=%(refname:short)'))
        self.cli('recovery', self.path, '--operation', 'resume', '--operation-id', result['operation_id'], '--apply')
        self.assertEqual(self.git('rev-parse', 'HEAD'), original)
        self.cli('branch', self.path, '--operation', 'create', '--name', 'feature/after', '--source', 'develop', '--apply')

    def test_dirty_switch_preserves_worktree_and_preview_does_not_create_ref(self):
        self.ready()
        self.cli('branch', self.path, '--operation', 'create', '--name', 'feature/preview', '--source', 'develop')
        self.assertNotIn('feature/preview', self.git('branch', '--format=%(refname:short)'))
        (self.path / 'app.txt').write_text('dirty', encoding='utf-8')
        self.cli('branch', self.path, '--operation', 'switch', '--name', 'develop', '--apply', code=3)
        self.assertEqual(self.git('branch', '--show-current'), 'main')
        self.assertEqual((self.path / 'app.txt').read_text(encoding='utf-8'), 'dirty')

    def test_worktree_identity_accepts_equivalent_path_and_rejects_other_worktree(self):
        from gitflow.operations import available
        self.ready()
        # Real Git emits one canonical spelling; equivalent lexical input must
        # not turn this same worktree into an allegedly occupied different one.
        available(self.path, 'main', str(self.path) + '/.')
        other = self.path.parent / 'other'
        self.git('worktree', 'add', str(other), 'develop')
        with self.assertRaises(FlowError) as caught:
            available(self.path, 'develop', str(self.path))
        self.assertEqual(caught.exception.code, 'branch_worktree_occupied')
        self.cli('branch', self.path, '--operation', 'switch', '--name', 'main', '--apply')
        self.assertEqual(self.git('branch', '--show-current'), 'main')

    def test_shared_cli_fixture_decodes_declared_utf8_with_legacy_locale(self):
        self.ready()
        # This is an encoding regression, not simulated Windows execution:
        # subprocess still invokes the real CLI, but its default decoder is cp1252.
        with patch('subprocess._text_encoding', return_value='cp1252'):
            result = GitTestCase.cli(self, 'gate', self.path, '--action', 'commit', code=1)
        message = next(reason['message'] for reason in result['reasons']
                       if reason['code'] == 'protected_branch_commit')
        self.assertEqual(message, '当前角色禁止直接提交，应进入任务分支。')

    def test_release_error_does_not_relabel_proven_complete_write_or_replay_it(self):
        from gitflow.storage import locked as actual_locked
        self.ready()
        @contextmanager
        def release_error(facts):
            # Fault injection only at release, after real locking and real Git.
            with actual_locked(facts):
                yield
            raise FlowError('state_lock_release_failed', 'injected release uncertainty')
        with patch('gitflow.operations.locked', release_error):
            with self.assertRaises(FlowError) as caught:
                branch(self.path, 'create', name='feature/completed', source='develop', apply=True)
        self.assertEqual(caught.exception.code, 'state_lock_release_failed')
        journal_path = self.path / '.gitflow/state/worktrees/main/journal.json'
        before = journal_path.read_bytes()
        journal = json.loads(before)
        self.assertEqual(journal['entries'][-1]['status'], 'complete')
        self.assertEqual(journal['entries'][-1]['steps'][-1]['status'], 'complete')
        original = self.git('rev-parse', 'feature/completed')
        denied = self.cli('branch', self.path, '--operation', 'create', '--name', 'feature/completed', '--source', 'develop', '--apply', code=1)
        self.assertEqual(denied['reasons'][0]['code'], 'branch_exists')
        self.assertEqual(self.git('rev-parse', 'feature/completed'), original)
        self.assertEqual(journal_path.read_bytes(), before)

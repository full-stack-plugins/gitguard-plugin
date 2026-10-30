"""用真实 Git 验证项目隐藏目录、worktree 隔离和旧状态接入。"""
import json
import shutil
import shlex
import sys
from pathlib import Path

from test_core import GitTestCase


class StorageLayoutTests(GitTestCase):
    def test_local_state_is_hidden_and_ignored(self):
        self.repository()
        self.activate(mode='local')
        self.assertTrue((self.path / '.git/gitflow.xml').is_file())
        self.assertFalse((self.path / '.gitflow/state/activation.json').exists())
        self.assertFalse((self.path / '.git/gitflow').exists())
        self.assertFalse((self.path / '.gitflow/workflow.json').exists())
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.cli('branch', self.path, '--operation', 'reconcile', '--apply')
        self.assertTrue((self.path / '.gitflow/state/worktrees/main/journal.json').exists())

    def test_linked_worktree_shares_policy_but_not_journal(self):
        self.repository()
        self.activate(mode='local')
        self.cli('branch', self.path, '--operation', 'reconcile', '--apply')
        main_journal = self.path / '.gitflow/state/worktrees/main/journal.json'
        before = main_journal.read_bytes()
        linked = self.path.parent / 'linked'
        self.git('worktree', 'add', str(linked), 'develop')
        self.cli('branch', linked, '--operation', 'create', '--name', 'feature/linked', '--source', 'develop', '--apply')
        self.assertEqual(main_journal.read_bytes(), before)
        journals = list((self.path / '.gitflow/state/worktrees').glob('*/journal.json'))
        self.assertEqual(len(journals), 2)
        self.assertFalse((linked / '.gitflow').exists())
        self.assertEqual(self.git('status', '--porcelain', cwd=linked), '')

    def test_separate_git_dir_keeps_data_in_project(self):
        metadata = self.path.parent / 'metadata'
        self.git('init', '-b', 'main', '--separate-git-dir', str(metadata))
        self.activate(mode='local')
        self.assertTrue((metadata / 'gitflow.xml').exists())
        self.assertFalse((metadata / 'gitflow').exists())

    def legacy(self):
        self.repository()
        # Build the old public contract independently of the implementation.
        import hashlib
        from test_core import ROOT
        policy = json.loads((ROOT / 'profiles/classic-gitflow.json').read_text())
        digest = hashlib.sha256(json.dumps(policy, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
        legacy = self.path / '.git/gitflow'
        legacy.mkdir()
        (legacy / 'activation.json').write_text(json.dumps({'schema_version': '1.0.0', 'mode': 'local', 'policy': policy, 'sha256': digest}))
        (legacy / 'origins.json').write_text('{}')
        (legacy / 'journal.json').write_text('{"schema_version":"1.0.0","entries":[]}')
        (legacy / 'user-note.txt').write_text('preserve me')
        return legacy

    def test_readonly_legacy_then_apply_migrates_without_loss(self):
        legacy = self.legacy()
        before = {p.name: p.read_bytes() for p in legacy.iterdir()}
        self.cli('policy', self.path, '--operation', 'migrate')
        self.assertFalse((self.path / '.gitflow').exists())
        self.assertEqual({p.name: p.read_bytes() for p in legacy.iterdir()}, before)
        self.cli('policy', self.path, '--operation', 'migrate', '--apply')
        state = self.path / '.gitflow/state'
        self.assertFalse(legacy.exists())
        for name in ('activation.json', 'origins.json'):
            self.assertEqual(json.loads((state / name).read_text()), json.loads(before[name]))
        self.assertEqual((state / 'legacy/main/user-note.txt').read_text(), 'preserve me')
        self.assertTrue((state / 'worktrees/main/journal.json').exists())
        self.assertTrue((self.path / '.git/gitflow.xml').exists())
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.cli('branch', self.path, '--operation', 'reconcile', '--apply')

    def test_conflicting_legacy_state_is_not_overwritten(self):
        legacy = self.legacy()
        state = self.path / '.gitflow/state'
        state.mkdir(parents=True)
        (state / 'origins.json').write_text('{"unexpected":{}}')
        self.cli('policy', self.path, '--operation', 'migrate', '--apply', code=3)
        self.assertTrue((legacy / 'activation.json').exists())
        self.assertEqual((state / 'origins.json').read_text(), '{"unexpected":{}}')

    def test_migration_retargets_only_owned_native_hooks(self):
        legacy = self.legacy()
        runtime = legacy / 'native-runtime'
        runtime.mkdir()
        from test_core import ROOT
        shutil.copytree(ROOT / 'scripts', runtime / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        hook = self.path / '.git/hooks/commit-msg'
        hook.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(runtime / 'scripts/gitflow.py')) + ' native --kind commit-msg -- "$@"\n')
        hook.chmod(0o755)
        self.cli('policy', self.path, '--operation', 'migrate', '--apply')
        expected_script = self.path / '.gitflow/state/native-runtime/scripts/gitflow.py'
        self.assertEqual(hook.read_text(), '#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' +
                         shlex.quote(str(expected_script)) + ' native --kind commit-msg -- "$@"\n')
        import subprocess
        result = subprocess.run(['git', '-C', str(self.path), 'commit', '--allow-empty', '-m', 'fix: blocked'], env=self.env, capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('当前角色禁止直接提交', result.stdout + result.stderr)

    def test_custom_legacy_hook_stops_migration(self):
        legacy = self.legacy()
        (legacy / 'native-runtime').mkdir()
        hook = self.path / '.git/hooks/commit-msg'
        hook.write_text('#!/bin/sh\n# custom\n' + str(legacy / 'native-runtime/scripts/gitflow.py'))
        before = hook.read_bytes()
        self.cli('policy', self.path, '--operation', 'migrate', '--apply', code=3)
        self.assertEqual(hook.read_bytes(), before)
        self.assertTrue(legacy.exists())

    def test_legacy_linked_journal_migrates_and_next_write_uses_new_layout(self):
        legacy = self.legacy()
        self.git('branch', 'develop')
        linked = self.path.parent / 'linked'
        self.git('worktree', 'add', str(linked), 'develop')
        admin = Path(self.git('rev-parse', '--absolute-git-dir', cwd=linked))
        old = admin / 'gitflow'
        old.mkdir()
        (old / 'journal.json').write_text('{"schema_version":"1.0.0","entries":[]}')
        self.cli('gate', linked, '--action', 'commit', code=3)
        self.assertTrue(old.exists())
        self.cli('policy', self.path, '--operation', 'migrate', '--apply')
        self.cli('branch', linked, '--operation', 'create', '--name', 'feature/migrate', '--source', 'develop', '--apply')
        self.assertFalse(legacy.exists())
        self.assertFalse(old.exists())
        state = self.path / '.gitflow/state'
        journals = list((state / 'worktrees').glob('*/journal.json'))
        self.assertEqual(len(journals), 2)
        self.assertIn('feature/migrate', json.loads((state / 'origins.json').read_text()))
        self.assertTrue(any(json.loads(p.read_text())['entries'] for p in journals))

    def test_state_symlink_is_rejected_without_external_write(self):
        self.repository()
        outside = self.path.parent / 'outside'
        outside.mkdir()
        (self.path / '.gitflow').mkdir()
        (self.path / '.gitflow/state').symlink_to(outside, target_is_directory=True)
        self.cli('init', self.path, '--profile', 'classic-gitflow', '--mode', 'local', '--apply', code=3)
        self.assertEqual(list(outside.iterdir()), [])

    def test_readonly_new_layout_does_not_change_state_or_config(self):
        self.repository()
        self.activate(mode='local')
        files = [self.path / '.git/config', self.path / '.git/info/exclude', self.path / '.git/gitflow.xml', *[p for p in (self.path / '.gitflow').rglob('*') if p.is_file()]]
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}
        self.cli('gate', self.path, '--action', 'commit', code=1)
        self.cli('init', self.path, '--profile', 'classic-gitflow', '--mode', 'local')
        self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}, before)

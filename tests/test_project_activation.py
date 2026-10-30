"""真实 Hook 子进程验证 Git 项目触发边界，不把插件 cwd 当项目。"""
import json
from pathlib import Path
import subprocess
import sys
from test_core import GitTestCase, CLI

EVENTS = ('SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'Stop')


class ProjectActivationTests(GitTestCase):
    def hook(self, event, cwd=None, command='git push --force origin main', omit_cwd=False):
        payload = {'hook_event_name': event, 'tool_name': 'Bash',
                   'tool_input': {'command': command}}
        if not omit_cwd:
            payload['cwd'] = str(cwd or self.path)
        proc = subprocess.run([sys.executable, str(CLI), 'hook', '--event', event],
                              input=json.dumps(payload), text=True, capture_output=True,
                              cwd=CLI.parent.parent, env=self.env, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_plain_directory_is_silent_for_every_event_without_writes(self):
        self.env['PLUGIN_DATA'] = str(self.path.parent / 'plugin-data')
        for event in EVENTS:
            with self.subTest(event=event):
                self.assertEqual(self.hook(event), {})
        self.assertEqual(list(self.path.iterdir()), [])
        self.assertFalse(Path(self.env['PLUGIN_DATA']).exists())

    def test_missing_cwd_never_activates_using_plugin_repository(self):
        for event in EVENTS:
            with self.subTest(event=event):
                self.assertEqual(self.hook(event, omit_cwd=True), {})

    def test_bare_repository_does_not_activate(self):
        self.git('init', '--bare')
        for event in EVENTS:
            with self.subTest(event=event):
                self.assertEqual(self.hook(event), {})

    def test_repository_subdirectory_and_unborn_activate(self):
        self.repository(commit=False)
        self.cli('init',self.path,'--profile','classic-gitflow','--apply')
        nested = self.path / 'src'; nested.mkdir()
        result = self.hook('SessionStart', cwd=nested)
        self.assertIn('classic-gitflow', result['hookSpecificOutput']['additionalContext'])
        self.assertIn('初始提交', result['hookSpecificOutput']['additionalContext'])
        for event in ('UserPromptSubmit', 'PostToolUse', 'Stop'):
            self.assertNotEqual(self.hook(event, cwd=nested), {})

    def test_worktree_git_file_and_detached_head_activate(self):
        self.repository(); self.activate(mode='local')
        linked = self.path.parent / 'linked'
        self.git('worktree', 'add', '--detach', str(linked))
        self.assertTrue((linked / '.git').is_file())
        result = self.hook('SessionStart', cwd=linked)
        self.assertIn('classic-gitflow', result['hookSpecificOutput']['additionalContext'])
        result = self.hook('PreToolUse', cwd=linked, command='git status')
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'allow')

    def test_submodule_git_file_binds_its_own_workflow(self):
        self.repository(); self.activate(mode='local')
        child = self.path.parent / 'source'
        child.mkdir()
        self.git('init', '-b', 'main', cwd=child)
        self.git('commit', '--allow-empty', '-m', 'initial', cwd=child)
        self.git('-c', 'protocol.file.allow=always', 'submodule', 'add', str(child), 'module')
        module = self.path / 'module'
        self.assertTrue((module / '.git').is_file())
        self.cli('init', module, '--profile', 'github-flow', '--mode', 'local', '--apply')
        result = self.hook('SessionStart', cwd=module)
        self.assertIn('github-flow', result['hookSpecificOutput']['additionalContext'])
        self.assertNotIn('classic-gitflow', result['hookSpecificOutput']['additionalContext'])

    def test_effective_command_target_controls_activation(self):
        self.repository(); self.activate(mode='local')
        plain = self.path.parent / 'plain'; plain.mkdir()
        for command in (f'git -C "{self.path}" commit -m blocked',
                        f'git -C"{self.path}" commit -m blocked',
                        f'cd "{self.path}" && git commit -m blocked',
                        f'git -C "{self.path.parent}" -C project commit -m blocked'):
            with self.subTest(command=command):
                result = self.hook('PreToolUse', cwd=plain, command=command)
                self.assertEqual(result.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')
        for command in (f'git -C "{plain}" push --force origin main',
                        f'cd "{plain}" && git push --force origin main'):
            with self.subTest(command=command):
                self.assertEqual(self.hook('PreToolUse', command=command), {})

    def test_git_environment_cannot_activate_unmanaged_directory(self):
        self.repository()
        plain = self.path.parent / 'plain'; plain.mkdir()
        self.env.update(GIT_DIR=str(self.path / '.git'), GIT_WORK_TREE=str(self.path))
        for event in EVENTS:
            with self.subTest(event=event):
                self.assertEqual(self.hook(event, cwd=plain), {})

    def test_cd_updates_activation_before_unknown_dynamic_target(self):
        self.repository(); self.activate(mode='local')
        plain = self.path.parent / 'plain'; plain.mkdir()
        result = self.hook('PreToolUse', cwd=plain,
                           command=f'cd "{self.path}" && git -C "$REPO" commit -m blocked')
        self.assertEqual(result.get('hookSpecificOutput', {}).get('permissionDecision'), 'ask')
        result = self.hook('PreToolUse',
                           command=f'cd "{plain}" && git -C "$REPO" commit -m blocked')
        self.assertEqual(result, {})

    def test_state_changes_are_observed_without_cached_activation(self):
        self.assertEqual(self.hook('SessionStart'), {})
        self.repository(); self.activate(mode='local')
        self.assertNotEqual(self.hook('SessionStart'), {})
        (self.path / '.git').rename(self.path / 'saved-git-metadata')
        for event in EVENTS:
            with self.subTest(event=event):
                self.assertEqual(self.hook(event), {})

    def test_unmanaged_dynamic_commands_do_not_activate_or_execute(self):
        marker = self.path / 'must-not-exist'
        for command in (f'git -C "$(touch {marker})" commit -m bad',
                        'git status\ngit push --force origin main',
                        'git -c alias.save=commit save -m bad'):
            with self.subTest(command=command):
                self.assertEqual(self.hook('PreToolUse', command=command), {})
        self.assertFalse(marker.exists())

    def test_damaged_git_metadata_is_unverified_not_allowed(self):
        (self.path / '.git').mkdir()
        result = self.hook('PreToolUse', command='git commit -m blocked')
        self.assertEqual(result.get('hookSpecificOutput', {}).get('permissionDecision'), 'ask')
        result = self.hook('SessionStart')
        self.assertIn('未验证', result['systemMessage'])
        self.assertNotIn('hookSpecificOutput', result)

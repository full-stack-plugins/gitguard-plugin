"""真实仓库验收：防止检查错仓、默认写入、政策漂移与保护分支放行。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/gitflow.py'
sys.path.insert(0,str(ROOT/'scripts'))


class GitTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gitflow-test-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / 'project'
        self.path.mkdir()
        self.env = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                    'GIT_AUTHOR_NAME': 'Tester', 'GIT_AUTHOR_EMAIL': 'test@example.invalid',
                    'GIT_COMMITTER_NAME': 'Tester', 'GIT_COMMITTER_EMAIL': 'test@example.invalid'}

    def git(self, *args, cwd=None):
        p = subprocess.run(['git', '-C', str(cwd or self.path), *args], env=self.env,
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.strip()

    def repository(self, commit=True):
        self.git('init', '-b', 'main')
        if commit:
            (self.path / 'app.txt').write_text('initial\n')
            self.git('add', 'app.txt')
            self.git('commit', '-m', 'chore: initial')

    def cli(self, *args, code=0, cwd=None):
        p = subprocess.run([sys.executable, str(CLI), *map(str, args), '--json'],
                           env=self.env, cwd=cwd, capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(p.returncode, code, p.stderr or p.stdout)
        try:
            return json.loads(p.stdout)
        except ValueError:
            self.fail('CLI 未返回完整 JSON: ' + p.stdout + p.stderr)

    def activate(self, profile='classic-gitflow', mode='shared'):
        result=self.cli('init', self.path, '--profile', profile, '--mode', mode, '--apply')
        return result


class CoreTests(GitTestCase):
    def test_version_is_executable_from_another_directory(self):
        r = self.cli('version', cwd=self.path)
        self.assertEqual(r['version'], json.loads((ROOT / 'plugin.json').read_text())['version'])

    def test_no_git_discovery_does_not_initialize_or_write(self):
        before = list(self.path.iterdir())
        r = self.cli('discover', self.path)
        self.assertEqual(r['git_state'], 'absent')
        self.assertEqual(r['next_actions'][0]['action'], 'ask_git_initialization')
        self.assertEqual(list(self.path.iterdir()), before)

    def test_subdirectory_binds_existing_parent_repository(self):
        self.repository()
        nested = self.path / 'src'
        nested.mkdir()
        r = self.cli('discover', nested)
        self.assertEqual(r['root'], str(self.path))
        self.assertEqual(r['branch'], 'main')

    def test_init_preview_preserves_all_project_files(self):
        self.repository()
        r = self.cli('init', self.path, '--profile', 'classic-gitflow')
        self.assertEqual(r['decision'], 'preview')
        self.assertFalse((self.path / '.gitflow').exists())
        self.assertFalse((self.path / '.git/gitflow').exists())

    def test_no_git_apply_requires_explicit_initialization(self):
        self.cli('init', self.path, '--apply', code=3)
        self.assertFalse((self.path / '.git').exists())
        r = self.cli('init', self.path, '--profile','classic-gitflow','--initialize-git', '--apply')
        self.assertEqual(r['profile'], 'classic-gitflow')
        self.assertEqual(self.git('symbolic-ref', '--short', 'HEAD'), 'main')
        self.assertEqual(self.git('rev-list', '--all', '--count'), '0')

    def test_existing_history_requires_profile_when_no_prior_contract(self):
        self.repository()
        self.cli('init', self.path, '--apply', code=3)
        self.assertFalse((self.path / '.gitflow').exists())

    def test_init_is_idempotent_and_does_not_overwrite_policy(self):
        self.repository()
        self.activate()
        policy = self.path / '.git/gitflow.xml'
        content = policy.read_bytes()
        self.cli('init', self.path, '--profile', 'github-flow', '--apply', code=3)
        self.assertEqual(policy.read_bytes(), content)
        self.cli('init', self.path, '--profile', 'classic-gitflow', '--apply')
        self.assertEqual(policy.read_bytes(), content)

    def test_protected_main_denies_regular_commit(self):
        self.repository()
        self.activate()
        r = self.cli('gate', self.path, '--action', 'commit', code=1)
        self.assertEqual(r['decision'], 'deny')
        self.assertIn('protected_branch_commit', [x['code'] for x in r['reasons']])

    def test_feature_commit_is_allowed_and_has_unknown_origin(self):
        self.repository()
        self.activate()
        self.git('switch', '-c', 'feature/123-login')
        r = self.cli('gate', self.path, '--action', 'commit')
        self.assertEqual(r['decision'], 'allow')
        r = self.cli('audit', self.path, code=1)
        self.assertIn('branch_origin_unknown', [x['code'] for x in r['observations']])

    def test_naming_violation_is_not_a_quality_failure(self):
        self.repository()
        self.activate()
        self.git('switch', '-c', 'my_random_branch')
        r = self.cli('gate', self.path, '--action', 'commit', code=1)
        self.assertEqual(r['reasons'][0]['code'], 'branch_name_unmatched')
        self.assertEqual(r['quality_decision'], 'not_evaluated')

    def test_missing_ephemeral_roles_are_not_audit_failures(self):
        self.repository()
        self.git('branch', 'develop')
        self.activate()
        r = self.cli('audit', self.path)
        self.assertEqual(r['decision'], 'allow')
        self.assertEqual(r['missing_required_roles'], [])

    def test_xml_is_the_only_runtime_authority(self):
        self.repository();self.activate()
        # A legacy JSON file cannot change the active XML rule.
        folder=self.path/'.gitflow';folder.mkdir(exist_ok=True)
        policy=json.loads((ROOT/'profiles/classic-gitflow.json').read_text())
        policy['roles']['main']['allow_commit']=True
        (folder/'workflow.json').write_text(json.dumps(policy))
        self.cli('gate',self.path,'--action','commit',code=1)
        from gitflow.xml_policy import write_policy
        write_policy({'common_dir':str(self.path/'.git')},policy)
        self.cli('gate',self.path,'--action','commit')

    def test_invalid_policy_field_is_rejected_without_activation(self):
        self.repository();self.activate()
        p=self.path/'.git/gitflow.xml'
        p.write_bytes(p.read_bytes().replace(b'<allow_commit type="bool">false',b'<allow_commit type="bool">yes',1))
        self.cli('policy',self.path,'--operation','activate','--apply',code=3)
        self.cli('gate',self.path,'--action','commit',code=3)

    def test_linked_worktree_uses_shared_activation(self):
        self.repository()
        self.git('branch', 'develop')
        self.activate()
        other = self.path.parent / 'linked'
        self.git('worktree', 'add', '-b', 'feature/123-linked', str(other), 'develop')
        r = self.cli('discover', other)
        self.assertEqual(r['common_dir'], str(self.path / '.git'))
        self.assertNotEqual(r['git_dir'], r['common_dir'])
        self.cli('gate', other, '--action', 'commit')

    def test_local_policy_has_no_shared_definition(self):
        self.repository()
        self.activate(mode='local')
        self.assertFalse((self.path / '.gitflow/workflow.json').exists())
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.cli('gate', self.path, '--action', 'commit', code=1)

    def test_detached_head_commit_is_unverified(self):
        self.repository()
        self.activate()
        self.git('switch', '--detach')
        r = self.cli('gate', self.path, '--action', 'commit', code=3)
        self.assertIn('detached_head', [x['code'] for x in r['reasons']])

    def test_merge_direction_is_enforced_by_role(self):
        self.repository()
        self.git('branch', 'develop')
        self.git('branch', 'feature/123-test')
        self.activate()
        self.cli('gate', self.path, '--action', 'merge', '--source', 'feature/123-test',
                 '--target', 'main', code=1)
        self.cli('gate', self.path, '--action', 'merge', '--source', 'feature/123-test',
                 '--target', 'develop')


if __name__ == '__main__':
    unittest.main()

class OnboardingTests(GitTestCase):
    def test_existing_repository_init_reports_missing_long_term_branch(self):
        self.repository()
        r=self.cli('init',self.path,'--profile','classic-gitflow','--mode','local','--apply')
        self.assertEqual(r['missing_required_roles'],['develop'])
        self.assertIn('audit',[a['action'] for a in r['next_actions']])

    def test_initialization_preserves_existing_human_markdown(self):
        self.repository();directory=self.path/'.gitflow';directory.mkdir();file=directory/'workflow.md';file.write_text('人工维护的工作流说明')
        self.cli('init',self.path,'--profile','classic-gitflow','--apply')
        self.assertEqual(file.read_text(),'人工维护的工作流说明')

"""Real launcher installation in isolated directories, without touching user bins."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gitguard install ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'user bin'
        self.entry = self.bin / 'gitguard'

    def lifecycle(self, command, *flags, code=0):
        result = subprocess.run(['sh', str(ROOT / 'bin/gitguard'), command,
                                 '--bin-dir', str(self.bin), *flags],
                                cwd=self.root, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, code, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def version(self, entry):
        result = subprocess.run(['sh', str(entry), 'version', '--json'],
                                cwd=self.root, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['decision'], 'allow')

    def test_installed_launcher_runs_from_unrelated_directory(self):
        self.lifecycle('install')
        self.version(self.entry)

    def test_installed_launcher_runs_on_path(self):
        self.lifecycle('install')
        result = subprocess.run(['gitguard', 'version', '--json'], cwd=self.root,
                                env={**os.environ, 'PATH': str(self.bin) + os.pathsep + os.environ['PATH']},
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['decision'], 'allow')

    def test_relative_link_chain_runs(self):
        self.lifecycle('install')
        alias = self.root / 'alias with spaces'
        alias.symlink_to(Path('user bin') / 'gitguard')
        self.version(alias)

    def test_install_dry_run_creates_nothing(self):
        self.lifecycle('install', '--dry-run')
        self.assertFalse(self.bin.exists())

    def test_uninstall_dry_run_preserves_link_and_then_uninstalls(self):
        self.lifecycle('install')
        before = os.readlink(self.entry)
        self.lifecycle('uninstall', '--dry-run')
        self.assertTrue(self.entry.is_symlink())
        self.assertEqual(os.readlink(self.entry), before)
        self.lifecycle('uninstall')
        self.assertFalse(os.path.lexists(self.entry))
        self.assertTrue((ROOT / 'bin/gitguard').is_file())

    def test_repeated_install_and_upgrade_remain_usable(self):
        self.lifecycle('install')
        self.lifecycle('install')
        self.lifecycle('upgrade')
        self.version(self.entry)

    def test_existing_file_is_never_overwritten_or_removed(self):
        self.bin.mkdir()
        self.entry.write_text('unmanaged')
        for command in ('install', 'upgrade', 'uninstall'):
            for flags in ((), ('--dry-run',)):
                self.lifecycle(command, *flags, code=1)
                self.assertEqual(self.entry.read_text(), 'unmanaged')

    def test_unmanaged_and_dangling_links_are_preserved(self):
        self.bin.mkdir()
        for target in (self.root / 'missing', ROOT / 'README.md'):
            self.entry.symlink_to(target)
            for command in ('install', 'upgrade', 'uninstall'):
                self.lifecycle(command, code=1)
                self.assertEqual(os.readlink(self.entry), str(target))
            self.entry.unlink()

    def test_missing_uninstall_is_denied(self):
        self.lifecycle('uninstall', code=1)
        self.assertFalse(self.bin.exists())

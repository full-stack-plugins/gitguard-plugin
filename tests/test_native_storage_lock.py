"""Real OS locks; same contract on Windows and POSIX, no platform simulation."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from gitflow import storage
from gitflow.git import FlowError


class NativeLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gitguard-native-lock-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / 'state.lock'

    def test_excludes_second_lock_and_releases_after_exception(self):
        with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
            with storage._lock_file(self.path):
                with self.assertRaises(FlowError) as caught:
                    with storage._lock_file(self.path):
                        self.fail('concurrent lock acquired')
                self.assertEqual(caught.exception.code, 'operation_busy')
                raise RuntimeError('fixture failure')
        with storage._lock_file(self.path):
            pass

    def test_hardlinked_lock_is_rejected_without_changing_target(self):
        outside = self.path.parent / 'outside'
        outside.write_bytes(b'preserve')
        os.link(outside, self.path)
        with self.assertRaises(FlowError) as caught:
            with storage._lock_file(self.path):
                self.fail('hardlink lock acquired')
        self.assertEqual(caught.exception.code, 'state_file_invalid')
        self.assertEqual(outside.read_bytes(), b'preserve')

    def test_process_crash_releases_kernel_lock(self):
        source = ('import sys; sys.path.insert(0, sys.argv[1]); '
                  'from gitflow.storage import _lock_file; '
                  'lock = _lock_file(sys.argv[2]); lock.__enter__(); '
                  'from pathlib import Path; Path(sys.argv[3]).write_text("ready"); sys.stdin.read()')
        ready = self.path.parent / 'ready'
        child = subprocess.Popen([sys.executable, '-u', '-c', source,
                                  str(ROOT / 'scripts'), str(self.path), str(ready)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, encoding='utf-8')
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready.exists(), 'lock child did not become ready within five seconds')
            with self.assertRaises(FlowError) as caught:
                with storage._lock_file(self.path):
                    self.fail('cross-process lock acquired')
            self.assertEqual(caught.exception.code, 'operation_busy')
            child.kill()
            child.communicate(timeout=5)
            with storage._lock_file(self.path):
                pass
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)

    def test_migration_moves_directory_without_releasing_old_file_lock(self):
        old = self.path.parent / 'legacy'
        old.mkdir()
        target = self.path.parent / 'backup'
        with storage._lock_file(old / 'state.lock', movable=True):
            old.rename(target)
            with self.assertRaises(FlowError) as caught:
                with storage._lock_file(target / 'state.lock'):
                    self.fail('migration released original lock')
            self.assertEqual(caught.exception.code, 'operation_busy')
        with storage._lock_file(target / 'state.lock'):
            pass

    @unittest.skipUnless(sys.platform == 'win32', 'actual Windows junction required')
    def test_windows_junction_lock_parent_is_rejected_without_creating_file(self):
        outside = self.path.parent / 'outside'
        outside.mkdir()
        junction = self.path.parent / 'junction'
        result = subprocess.run(['cmd.exe', '/D', '/C', 'mklink', '/J', str(junction), str(outside)],
                                capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            with self.assertRaises(FlowError) as caught:
                with storage._lock_file(junction / 'state.lock'):
                    self.fail('junction lock acquired')
            self.assertEqual(caught.exception.code, 'state_symlink')
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            os.rmdir(junction)

    @unittest.skipUnless(sys.platform == 'win32', 'actual Windows rename sharing required')
    def test_windows_primary_lock_pins_directory_until_release(self):
        folder = self.path.parent / 'primary'
        folder.mkdir()
        destination = self.path.parent / 'moved'
        with storage._lock_file(folder / 'state.lock'):
            with self.assertRaises(OSError):
                folder.rename(destination)
        folder.rename(destination)

"""Native Windows Job Object contracts, never simulated on Unix."""
import os
from pathlib import Path
import subprocess
import signal
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from gitflow.git import FlowError, run


@unittest.skipUnless(sys.platform == 'win32', 'requires native Windows Job Objects')
class WindowsRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gitguard windows space ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def execute(self, code, timeout=5, cancelled=None):
        from gitflow.windows_process import run_windows
        return run_windows([sys.executable, '-c', code], dict(os.environ), timeout,
                           cancelled=cancelled)

    def test_real_git_query(self):
        result = run(self.root, '--version')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.startswith(b'git version '))

    def test_literal_arguments_and_closed_stdin(self):
        from gitflow.windows_process import run_windows
        literal = 'space & | "quoted" trailing\\'
        result = run_windows([sys.executable, '-c',
                              'import sys; assert not sys.stdin.buffer.read(); print(repr(sys.argv[1]))', literal],
                             dict(os.environ), 5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode().strip(), repr(literal))

    def test_output_budget_is_not_truncated_success(self):
        with self.assertRaises(FlowError) as caught:
            self.execute('import sys; sys.stdout.buffer.write(b"x" * (5*1024*1024))')
        self.assertEqual(caught.exception.code, 'git_output_limit')

    def tree_code(self, wait):
        marker = self.root / 'escaped.marker'
        ready = self.root / 'ready.marker'
        grandchild = 'import time,pathlib; time.sleep(1); pathlib.Path(' + repr(str(marker)) + ').write_text("escaped")'
        return ('import subprocess,sys,pathlib,time; subprocess.Popen([sys.executable,"-c",' + repr(grandchild) + ']); '
                'pathlib.Path(' + repr(str(ready)) + ').write_text("ready"); ' +
                ('time.sleep(30)' if wait else 'pass'))

    def test_normal_parent_exit_reaps_descendant(self):
        result = self.execute(self.tree_code(False))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'ready.marker').exists())
        time.sleep(1.2)
        self.assertFalse((self.root / 'escaped.marker').exists())

    def test_timeout_reaps_descendant(self):
        started = time.monotonic()
        with self.assertRaises(FlowError) as caught:
            self.execute(self.tree_code(True), timeout=0.6)
        self.assertEqual(caught.exception.code, 'git_timeout')
        self.assertLess(time.monotonic()-started, 3)
        self.assertTrue((self.root / 'ready.marker').exists())
        time.sleep(1.2)
        self.assertFalse((self.root / 'escaped.marker').exists())

    def test_cancellation_after_handshake_reaps_descendant(self):
        ready = self.root / 'ready.marker'
        def cancelled():
            return ready.exists()
        with self.assertRaises(FlowError) as caught:
            self.execute(self.tree_code(True), cancelled=cancelled)
        self.assertEqual(caught.exception.code, 'git_cancelled')
        self.assertTrue(ready.exists())
        time.sleep(1.2)
        self.assertFalse((self.root / 'escaped.marker').exists())

    def test_missing_executable_is_structured(self):
        from gitflow.windows_process import run_windows
        with self.assertRaises(FlowError) as caught:
            run_windows([str(self.root / 'absent.exe')], dict(os.environ), 2)
        self.assertEqual(caught.exception.code, 'git_unavailable')

    def test_post_assignment_setup_failure_never_executes_child(self):
        from gitflow.windows_process import run_windows
        marker = self.root / 'must-not-exist'
        reached = []
        def fail():
            reached.append(True)
            raise OSError('injected pre-resume setup failure')
        started = time.monotonic()
        with self.assertRaises(FlowError) as caught:
            run_windows([sys.executable, '-c', 'import pathlib; pathlib.Path(' + repr(str(marker)) + ').touch()'],
                        dict(os.environ), 5, _before_resume=fail)
        self.assertTrue(reached, 'failure did not reach post-assignment test seam')
        self.assertEqual(caught.exception.code, 'git_io_error')
        self.assertLess(time.monotonic()-started, 3)
        self.assertFalse(marker.exists())

    def test_repeated_launches_release_handles(self):
        import ctypes as c
        from ctypes import wintypes as w
        kernel = c.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.argtypes, kernel.GetCurrentProcess.restype = [], w.HANDLE
        kernel.GetProcessHandleCount.argtypes = [w.HANDLE, c.POINTER(w.DWORD)]
        kernel.GetProcessHandleCount.restype = w.BOOL
        def count():
            result = w.DWORD()
            self.assertTrue(kernel.GetProcessHandleCount(kernel.GetCurrentProcess(), c.byref(result)))
            return result.value
        self.execute('pass')
        before = count()
        for _ in range(20):
            self.assertEqual(self.execute('pass').returncode, 0)
        self.assertLessEqual(count(), before + 2, 'native process/job/thread/pipe handles leaked')

    def test_cleanup_failure_is_unknown_not_success(self):
        from unittest.mock import patch
        from gitflow.windows_process import _Api
        with patch.object(_Api, 'active', side_effect=OSError('injected cleanup query failure')):
            with self.assertRaises(FlowError) as caught:
                self.execute('pass')
        self.assertEqual(caught.exception.code, 'git_cleanup_failed')

    def test_console_break_is_cancellation_and_reaps_tree(self):
        import json
        worker = self.root / 'controller.py'
        worker.write_text('''import json, os, sys
sys.path.insert(0, sys.argv[1])
from gitflow.windows_process import run_windows
from gitflow.git import FlowError
try:
    run_windows([sys.executable, '-c', sys.argv[2]], dict(os.environ), 20)
except FlowError as exc:
    print(json.dumps({'code':exc.code, 'decision':exc.decision}))
    raise SystemExit(3)
''', encoding='utf-8')
        proc = subprocess.Popen([sys.executable, str(worker), str(ROOT / 'scripts'), self.tree_code(True)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        try:
            deadline = time.monotonic() + 5
            while not (self.root / 'ready.marker').exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue((self.root / 'ready.marker').exists())
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            stdout, stderr = proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, 3, stderr.decode(errors='replace'))
            self.assertEqual(json.loads(stdout), {'code':'git_cancelled', 'decision':'unverified'})
            time.sleep(1.2)
            self.assertFalse((self.root / 'escaped.marker').exists())
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=3)

    def test_project_git_executable_cannot_override_absolute_path_git(self):
        # This deliberately is not a valid executable: CreateProcess cwd-first
        # resolution would fail, whereas the configured PATH Git must succeed.
        (self.root / 'git.exe').write_bytes(b'not the authorized Git executable')
        previous = os.getcwd()
        try:
            os.chdir(self.root)
            result = run(self.root, '--version')
        finally:
            os.chdir(previous)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith(b'git version '))

    def test_resume_uncertainty_has_unknown_operation_classification(self):
        from unittest.mock import patch
        from gitflow.windows_process import _Api
        original = _Api.resume
        def resume_then_fail(api, pid):
            original(api, pid)
            raise OSError('injected failure after ResumeThread')
        with patch.object(_Api, 'resume', resume_then_fail):
            with self.assertRaises(FlowError) as caught:
                self.execute('pass')
        self.assertEqual(caught.exception.code, 'git_cleanup_failed')


    def test_thread_close_failure_is_unknown_and_does_not_skip_other_handles(self):
        import ctypes as c
        from unittest.mock import patch
        from gitflow.windows_process import _Api
        closed = []
        class FailingCloseApi(_Api):
            def __init__(self):
                super().__init__()
                original = self.CloseHandle
                def close(handle):
                    result = original(handle)  # always release the real test resource
                    closed.append(handle)
                    if len(closed) == 1:
                        c.set_last_error(5)
                        return 0
                    return result
                self.CloseHandle = close
        with patch('gitflow.windows_process._Api', FailingCloseApi):
            with self.assertRaises(FlowError) as caught:
                self.execute('pass')
        self.assertEqual(caught.exception.code, 'git_cleanup_failed')
        self.assertGreaterEqual(len(closed), 4, 'thread close failure skipped snapshot/process/job close')



class WindowsPathContractTests(unittest.TestCase):
    def test_root_relative_paths_do_not_gain_current_drive_authority(self):
        from gitflow.windows_process import _fully_qualified_windows_path
        for value in (r'\git.exe', '/git.exe', 'C:git.exe', 'relative', ''):
            self.assertFalse(_fully_qualified_windows_path(value), value)
        for value in (r'C:\Tools\git.exe', r'\\server\share\git.exe', r'\\server\share',
                      r'\\?\C:\Tools\git.exe'):
            self.assertTrue(_fully_qualified_windows_path(value), value)

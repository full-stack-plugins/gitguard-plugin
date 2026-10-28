"""Real Git subprocess groups: bounded output, orphan pipes and cancellation."""
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from gitflow.git import FlowError, run


@unittest.skipUnless(sys.platform.startswith('linux'), 'requires Linux process state evidence')
class RunnerSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gitguard-runner-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pidfile = self.root / 'child.pid'
        self.helper = self.root / 'helper.py'
        self.helper.write_text('''import pathlib, subprocess, sys, time
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
pathlib.Path(sys.argv[1]).write_text(str(child.pid))
if sys.argv[2] == 'wait':
    child.wait()
''')
        self.addCleanup(self.cleanup_child)

    def cleanup_child(self):
        if self.pidfile.exists():
            try:
                os.kill(int(self.pidfile.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass

    def args(self, mode):
        command = '!' + ' '.join(shlex.quote(x) for x in
                                 [sys.executable, str(self.helper), str(self.pidfile), mode])
        return ['-c', 'alias.fixture=' + command, 'fixture']

    def child_running(self):
        pid = int(self.pidfile.read_text())
        try:
            return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()[0] != 'Z'
        except FileNotFoundError:
            return False

    def assert_child_stopped(self):
        deadline = time.monotonic() + 3
        while self.child_running() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertFalse(self.child_running(), 'Git descendant still alive')

    def test_timeout_kills_descendant_after_git_leader_exits(self):
        with self.assertRaises(FlowError) as caught:
            run(self.root, *self.args('orphan'), timeout=0.5)
        self.assertEqual(caught.exception.code, 'git_timeout')
        self.assertTrue(self.pidfile.exists())
        self.assert_child_stopped()

    def test_sigint_returns_unverified_and_stops_descendants(self):
        worker = self.root / 'worker.py'
        worker.write_text('''import json, sys
sys.path.insert(0, sys.argv[1])
from gitflow.git import run, FlowError
try:
    run(sys.argv[2], *sys.argv[3:], timeout=20)
except FlowError as exc:
    print(json.dumps({'decision':exc.decision, 'code':exc.code}))
    raise SystemExit(3)
''')
        proc = subprocess.Popen([sys.executable, '-B', str(worker), str(ROOT / 'scripts'),
                                 str(self.root), *self.args('wait')], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while not self.pidfile.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(self.pidfile.exists())
            proc.send_signal(signal.SIGINT)
            stdout, stderr = proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, 3, stderr)
            self.assertNotIn('Traceback', stderr)
            self.assertEqual(json.loads(stdout), {'decision':'unverified', 'code':'git_cancelled'})
            self.assert_child_stopped()
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate()

    def test_output_limit_is_unverified_not_truncated_success(self):
        command = '!' + shlex.quote(sys.executable) + ' -c ' + shlex.quote('print("x" * (5 * 1024 * 1024))')
        with self.assertRaises(FlowError) as caught:
            run(self.root, '-c', 'alias.fixture=' + command, 'fixture')
        self.assertEqual(caught.exception.code, 'git_output_limit')

    def test_cleanup_permission_error_is_structured_and_fail_closed(self):
        with patch('gitflow.git.os.killpg', side_effect=PermissionError('denied')):
            with self.assertRaises(FlowError) as caught:
                run(self.root, '--version')
        self.assertEqual(caught.exception.code, 'git_cleanup_failed')
        self.assertEqual(caught.exception.decision, 'unverified')

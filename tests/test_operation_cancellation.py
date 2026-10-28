"""SIGINT during a real local push must leave an unknown operation for review."""
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
import unittest
from test_core import GitTestCase, CLI


@unittest.skipUnless(sys.platform.startswith('linux'), 'requires POSIX Git hook and SIGINT')
class CancellationTests(GitTestCase):
    def test_cancelled_push_is_unknown_and_blocks_unrelated_apply(self):
        self.repository()
        self.activate(mode='local')
        self.git('branch', 'develop')
        remote = self.path.parent / 'remote.git'
        self.git('init', '--bare', str(remote))
        self.git('remote', 'add', 'origin', str(remote))
        marker = self.path.parent / 'hook.pid'
        helper = self.path.parent / 'hook.py'
        helper.write_text('import os, pathlib, time\npathlib.Path(' + repr(str(marker)) +
                          ').write_text(str(os.getpid()))\ntime.sleep(60)\n')
        hook = self.path / '.git/hooks/pre-push'
        hook.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(helper)) + '\n')
        hook.chmod(0o755)
        proc = subprocess.Popen([sys.executable, '-B', str(CLI), 'sync', str(self.path),
                                 '--operation', 'push', '--remote', 'origin', '--target', 'main',
                                 '--apply', '--json'], env=self.env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists())
            proc.send_signal(signal.SIGINT)
            stdout, stderr = proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, 3, stderr)
            result = json.loads(stdout)
            self.assertEqual(result['decision'], 'unverified')
            self.assertEqual(result['reasons'][0]['code'], 'git_cancelled')
            journal = json.loads((self.path / '.gitflow/state/worktrees/main/journal.json').read_text())
            self.assertEqual(journal['entries'][-1]['status'], 'unknown')
            blocked = self.cli('branch', self.path, '--operation', 'create', '--name', 'feature/new',
                               '--source', 'develop', '--apply', code=3)
            self.assertEqual(blocked['reasons'][0]['code'], 'operation_unknown')
            self.assertNotIn('feature/new', self.git('branch', '--format=%(refname:short)'))
            hook_pid = int(marker.read_text())
            stat = Path(f'/proc/{hook_pid}/stat')
            self.assertTrue(not stat.exists() or stat.read_text().split(') ', 1)[1].startswith('Z '))
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate()
            if marker.exists():
                try:
                    os.kill(int(marker.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass

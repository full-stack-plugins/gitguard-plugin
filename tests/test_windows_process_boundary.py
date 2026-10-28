"""The unverified Windows process-tree backend must not run a Git operation."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gitflow import git


class WindowsProcessBoundaryTests(unittest.TestCase):
    def test_unverified_windows_backend_stops_before_starting_git(self):
        with patch.object(sys, 'platform', 'win32'), patch.object(
                git.subprocess, 'Popen', side_effect=AssertionError('Git must not start')):
            with self.assertRaises(git.FlowError) as caught:
                git.run('.', 'status')
        self.assertEqual(caught.exception.code, 'windows_process_control_unverified')
        self.assertEqual(caught.exception.decision, 'unverified')

"""The test harness must not confuse a damaged ancestor with a plain directory."""
from pathlib import Path
import tempfile
import unittest

from run_isolated import contaminated_ancestors, isolated_environment


class TestIsolationTests(unittest.TestCase):
    def test_ancestor_metadata_is_reported_and_preserved(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);metadata=root/'.git';metadata.mkdir()
            (metadata/'fixture-note').write_text('preserve')
            child=root/'child';child.mkdir()
            self.assertIn(metadata,contaminated_ancestors(child))
            with self.assertRaisesRegex(RuntimeError,'ancestor Git metadata'):
                with isolated_environment(child):self.fail('must not run tests')
            self.assertEqual((metadata/'fixture-note').read_text(),'preserve')
            self.assertEqual(list(child.iterdir()),[])

    def test_broken_git_marker_is_not_treated_as_absent(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);metadata=root/'.git';metadata.write_text('gitdir: missing')
            self.assertIn(metadata,contaminated_ancestors(root))
            with self.assertRaises(RuntimeError):
                with isolated_environment(root):self.fail('must not run tests')
            self.assertEqual(metadata.read_text(),'gitdir: missing')

    def test_clean_environment_controls_real_child_tempfiles(self):
        import json,subprocess,sys
        with isolated_environment(Path(tempfile.gettempdir())) as (root,env):
            self.assertEqual(contaminated_ancestors(root),[])
            probe=subprocess.run([sys.executable,'-c','import tempfile,json; print(json.dumps(tempfile.gettempdir()))'],env=env,capture_output=True,text=True,check=True)
            self.assertEqual(Path(json.loads(probe.stdout)),root)
            self.assertTrue(root.is_dir())
        self.assertFalse(root.exists())

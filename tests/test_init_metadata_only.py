"""Metadata initialization must not inspect tracked guidance through Git filters."""
import io
import json
import os
from pathlib import Path
import shlex
import sys
from unittest.mock import patch
from test_core import GitTestCase, ROOT


class InitMetadataOnlyTests(GitTestCase):
    def setUp(self):
        super().setUp()
        self.repository()
        self.agents = self.path / 'AGENTS.md'
        self.agents.write_bytes(b'Human guidance before\n')
        (self.path / '.gitattributes').write_text('AGENTS.md filter=guidance-proof\n')
        self.git('add', 'AGENTS.md', '.gitattributes')
        self.git('commit', '-m', 'test: tracked guidance fixture')
        self.marker = self.path.parent / 'filter-executed'
        script = self.path.parent / 'guidance clean filter.py'
        script.write_text('from pathlib import Path\nimport sys\n'
                          f'Path({str(self.marker)!r}).write_text("executed")\n'
                          'sys.stdout.buffer.write(sys.stdin.buffer.read())\n')
        command = shlex.quote(sys.executable) + ' ' + shlex.quote(str(script))
        self.git('config', 'filter.guidance-proof.clean', command)
        self.original = b'Human guidance edited\n'
        self.assertEqual(len(self.original), len(self.agents.read_bytes()))
        self.agents.write_bytes(self.original)
        info = self.agents.stat()
        os.utime(self.agents, ns=(info.st_atime_ns, info.st_mtime_ns + 2_000_000_000))
        self.assertFalse(self.marker.exists())

    def assert_guidance_uninspected(self):
        self.assertFalse(self.marker.exists(), 'Git clean filter read tracked AGENTS.md')
        self.assertEqual(self.agents.read_bytes(), self.original)

    def test_control_full_discover_inspects_status_and_executes_fixture_filter(self):
        from gitflow.git import discover
        facts = discover(self.path)
        self.assertTrue(self.marker.exists(), 'Fixture must reproduce a real status clean-filter invocation')
        self.assertTrue(facts['dirty'])
        self.assertGreater(facts['dirty_entries'], 0)
        self.assertEqual(facts['worktree_status'], 'inspected')

    def test_metadata_api_reports_unknown_cleanliness_and_preserves_other_facts(self):
        from gitflow.git import discover, require_repo
        for query in (discover, require_repo):
            with self.subTest(query=query.__name__):
                facts = query(self.path, inspect_worktree=False)
                self.assertIsNone(facts['dirty']);self.assertIsNone(facts['dirty_entries'])
                self.assertEqual(facts['worktree_status'], 'not_inspected')
                self.assertEqual(facts['branch'], 'main')
                self.assertEqual(facts['head'], self.git('rev-parse', 'HEAD'))
                self.assertIn('main', facts['ref_oids'])
                self.assertEqual(facts['operation_states'], [])
                self.assertEqual(facts['remotes'], [])
                self.assert_guidance_uninspected()

    def test_init_preview_and_apply_do_not_read_guidance(self):
        for flags in ((), ('--apply',)):
            with self.subTest(flags=flags):
                self.marker.unlink(missing_ok=True)
                self.cli('init', self.path, '--profile', 'github-flow', *flags)
                self.assert_guidance_uninspected()
        self.assertTrue((self.path / '.git/gitflow.xml').is_file())

    def test_interactive_init_selection_is_metadata_only(self):
        from gitflow.cli import main
        for flags in ([], ['--apply']):
            with self.subTest(flags=flags):
                self.marker.unlink(missing_ok=True)
                output = io.StringIO()
                with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='github-flow'), patch('sys.stdout', output), patch('sys.stderr', io.StringIO()):
                    self.assertEqual(main(['init', str(self.path), *flags]), 0)
                self.assertEqual(json.loads(output.getvalue())['profile'], 'github-flow')
                self.assert_guidance_uninspected()

    def test_legacy_migration_preview_and_apply_do_not_read_guidance(self):
        folder = self.path / '.gitflow';folder.mkdir()
        (folder / 'workflow.json').write_text((ROOT / 'profiles/github-flow.json').read_text())
        for flags in ((), ('--apply',)):
            with self.subTest(flags=flags):
                self.marker.unlink(missing_ok=True)
                self.cli('policy', self.path, '--operation', 'migrate', *flags)
                self.assert_guidance_uninspected()
        self.assertTrue((self.path / '.git/gitflow.xml').is_file())

"""Frozen snapshots retain byte identities and POSIX lock keys across checkouts."""
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from vendor_skills import files


class SnapshotPortabilityTests(unittest.TestCase):
    def test_windows_relative_paths_use_posix_lock_keys(self):
        # Keep actual enumeration and hashing; simulate only Windows path spelling
        # so this platform-dependent failure is reproducible on Linux as well.
        relative_to = Path.relative_to
        def windows_relative(path, *other, **kwargs):
            relative = relative_to(path, *other, **kwargs)
            return PureWindowsPath(*relative.parts)
        expected = json.loads((ROOT / 'skills.lock.json').read_text(encoding='utf-8'))['files']
        with patch.object(Path, 'relative_to', new=windows_relative):
            observed = files(ROOT)
        self.assertEqual(observed, expected)
        self.assertTrue(all('\\' not in key for key in observed))

    def test_autocrlf_checkout_preserves_exact_frozen_bytes(self):
        env = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull}
        with tempfile.TemporaryDirectory(prefix='snapshot-checkout-') as temp:
            source = Path(temp) / 'source';source.mkdir()
            checkout = Path(temp) / 'checkout'
            for directory in ('skills', 'profiles'):
                shutil.copytree(ROOT / directory, source / directory, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            for name in ('sources.json', 'skills.lock.json'):
                shutil.copyfile(ROOT / name, source / name)
            if (ROOT / '.gitattributes').exists():
                shutil.copyfile(ROOT / '.gitattributes', source / '.gitattributes')
            (source / 'unprotected.txt').write_bytes(b'one\ntwo\n')
            def git(*args, cwd=source):
                result = subprocess.run(['git', '-C', str(cwd), *map(str, args)], env=env, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout
            git('init', '-b', 'main')
            git('config', 'core.autocrlf', 'false')
            git('add', '.')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'snapshot fixture')
            git('-c', 'core.autocrlf=true', 'clone', '--no-local', source, checkout)
            # Control confirms the checkout actually converted ordinary text.
            self.assertEqual((checkout / 'unprotected.txt').read_bytes(), b'one\r\ntwo\r\n')
            expected = json.loads((source / 'skills.lock.json').read_text(encoding='utf-8'))['files']
            self.assertEqual(files(checkout), expected)
            for relative, digest in expected.items():
                with self.subTest(path=relative):
                    self.assertEqual((checkout / relative).read_bytes(), (source / relative).read_bytes())
                    self.assertEqual(hashlib.sha256((checkout / relative).read_bytes()).hexdigest(), digest)

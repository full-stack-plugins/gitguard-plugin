"""Public skill identities must survive vendoring and offline packaging."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SUFFIXES = ('awesome', 'workflow', 'init', 'branch', 'audit', 'commit', 'sync', 'release', 'recovery')
EXPECTED = {'gitguard-' + suffix for suffix in SUFFIXES}

class SkillNamespaceTests(unittest.TestCase):
    def test_public_directories_frontmatter_and_host_prompts_match(self):
        self.assertEqual({p.name for p in (ROOT/'skills').iterdir() if p.is_dir()}, EXPECTED)
        for name in EXPECTED:
            with self.subTest(skill=name):
                text = (ROOT/'skills'/name/'SKILL.md').read_text(encoding='utf-8')
                self.assertTrue(text.startswith('---\nname: '+name+'\n'))
                prompt = (ROOT/'skills'/name/'agents/openai.yaml').read_text(encoding='utf-8')
                self.assertIn('display_name: "'+name+'"', prompt)
                self.assertIn('$'+name, prompt)

    def test_package_validation_rejects_wrong_skill_identity(self):
        sys.path.insert(0, str(ROOT/'scripts'))
        import validate_package
        self.assertTrue(hasattr(validate_package, 'skill_name_errors'), 'package validation must enforce public skill names')
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw);(root/'skills/git-init').mkdir(parents=True)
            self.assertTrue(validate_package.skill_name_errors(root))

    def test_offline_package_exposes_only_namespaced_skill_entries(self):
        with tempfile.TemporaryDirectory() as raw:
            output=Path(raw)/'candidate.zip'
            result=subprocess.run([sys.executable,str(ROOT/'scripts/package.py'),'--output',str(output)],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr or result.stdout)
            with zipfile.ZipFile(output) as archive:
                entries=[p for p in archive.namelist() if re.fullmatch(r'gitflow/skills/[^/]+/SKILL.md',p)]
                self.assertEqual({p.split('/')[2] for p in entries},EXPECTED)
                for p in entries:
                    self.assertTrue(archive.read(p).decode().startswith('---\nname: '+p.split('/')[2]+'\n'))

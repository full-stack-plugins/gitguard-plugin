"""Owned skill wiring uses the real launcher; generic provenance stays separate."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from vendor_skills import snapshot_errors


class OwnedInitTests(unittest.TestCase):
    @unittest.skipIf(os.name=='nt','POSIX launcher; native cmd covered separately')
    def test_installed_init_preview_apply_repeat_preserves_agents(self):
        with tempfile.TemporaryDirectory(prefix='owned init ') as raw:
            temp=Path(raw);project=temp/'project';project.mkdir();bins=temp/'bin'
            subprocess.run(['git','init','-b','main',str(project)],check=True,capture_output=True)
            agents=project/'AGENTS.md';agents.write_bytes(b'Human instructions\r\n')
            result=subprocess.run([sys.executable,str(ROOT/'scripts/install_cli.py'),'install','--bin-dir',str(bins)],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            env={**os.environ,'PATH':str(bins)+os.pathsep+os.environ['PATH']}
            def call(*args):
                result=subprocess.run(['gitguard','init',str(project),'--profile','github-flow','--json',*args],env=env,cwd=temp,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                return json.loads(result.stdout)
            call();self.assertFalse((project/'.git/gitflow.xml').exists())
            call('--apply');xml=(project/'.git/gitflow.xml').read_bytes()
            call('--apply');self.assertEqual((project/'.git/gitflow.xml').read_bytes(),xml)
            self.assertEqual(agents.read_bytes(),b'Human instructions\r\n')
            agents.unlink();call('--apply');self.assertFalse(agents.exists())

    def test_lock_detects_owned_generic_and_runtime_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)/'plugin';shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('.git','__pycache__'))
            self.assertEqual(snapshot_errors(root),[])
            for name in ('skills/gitguard-init/SKILL.md','vendor/git-skills/skills/git-init/SKILL.md','profiles/github-flow.json'):
                file=root/name;before=file.read_bytes();file.write_bytes(before+b'\nchanged')
                self.assertTrue(snapshot_errors(root),name);file.write_bytes(before)

    def test_vendoring_keeps_owned_skill_and_checks_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)/'plugin';source=Path(raw)/'upstream'
            shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('.git','__pycache__'))
            shutil.copytree(ROOT/'vendor/git-skills',source)
            (source/'.claude-plugin').mkdir();(source/'.claude-plugin/plugin.json').write_text('{"version":"0.2.0"}')
            for args in (['init'],['add','.'],['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','source']):
                subprocess.run(['git','-C',str(source),*args],check=True,capture_output=True)
            owned=(root/'skills/gitguard-init/SKILL.md').read_bytes()
            for _ in range(2):
                result=subprocess.run([sys.executable,str(root/'scripts/vendor_skills.py'),'--source',str(source)],capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual((root/'skills/gitguard-init/SKILL.md').read_bytes(),owned)
                self.assertEqual(snapshot_errors(root,source),[])
            lockfile=root/'skills.lock.json';original=lockfile.read_text();lock=json.loads(original)
            lock['source_commit']='0'*40;lockfile.write_text(json.dumps(lock))
            self.assertTrue(snapshot_errors(root,source));lockfile.write_text(original)
            (source/'.git/info/exclude').write_text('ignored.txt\n')
            (source/'skills/git-init/ignored.txt').write_text('not committed')
            result=subprocess.run([sys.executable,str(root/'scripts/vendor_skills.py'),'--source',str(source)],capture_output=True,text=True,timeout=30)
            self.assertNotEqual(result.returncode,0)
            (source/'skills/git-init/ignored.txt').unlink()
            (source/'skills/git-init/SKILL.md').write_text('drift')
            self.assertIn('Upstream source drift',snapshot_errors(root,source))

    @unittest.skipIf(os.name=='nt','symlink fixture needs POSIX permissions')
    def test_vendor_rejects_redirected_output_before_any_write(self):
        with tempfile.TemporaryDirectory() as raw:
            temp=Path(raw);root=temp/'plugin';source=temp/'upstream'
            shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('.git','__pycache__'))
            shutil.copytree(ROOT/'vendor/git-skills',source)
            (source/'.claude-plugin').mkdir();(source/'.claude-plugin/plugin.json').write_text('{"version":"0.2.0"}')
            for args in (['init'],['add','.'],['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','source']):
                subprocess.run(['git','-C',str(source),*args],check=True,capture_output=True)
            for target in ('vendor','sources.json','skills.lock.json'):
                with self.subTest(target=target):
                    location=root/target;backup=temp/('backup-'+target);location.rename(backup)
                    external=temp/('external-'+target)
                    if backup.is_dir():
                        external.mkdir();(external/'git-skills').mkdir();(external/'git-skills/sentinel').write_bytes(b'preserve')
                    else:external.write_bytes(b'preserve')
                    location.symlink_to(external,target_is_directory=backup.is_dir())
                    before={str(p.relative_to(temp)):p.read_bytes() for p in temp.rglob('*') if p.is_file() and not p.is_symlink()}
                    result=subprocess.run([sys.executable,str(root/'scripts/vendor_skills.py'),'--source',str(source)],capture_output=True,text=True,timeout=30)
                    self.assertNotEqual(result.returncode,0)
                    after={str(p.relative_to(temp)):p.read_bytes() for p in temp.rglob('*') if p.is_file() and not p.is_symlink()}
                    self.assertEqual(after,before)
                    location.unlink();backup.rename(location)

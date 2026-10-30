"""Actual packaged XML/native path, without a host trust or installation claim."""
import json
import subprocess
import sys
import zipfile
from test_core import GitTestCase, ROOT


class XmlPackageTests(GitTestCase):
    def test_offline_package_guards_real_git_and_uses_current_xml(self):
        self.repository()
        archive=self.path.parent/'candidate.zip'
        built=subprocess.run([sys.executable,str(ROOT/'scripts/package.py'),'--output',str(archive)],env=self.env,capture_output=True,text=True)
        self.assertEqual(built.returncode,0,built.stderr)
        unpack=self.path.parent/'package'
        with zipfile.ZipFile(archive) as package:
            package.extractall(unpack)
        entry=unpack/'gitflow/scripts/gitflow.py'
        def cli(*args,code=0):
            p=subprocess.run([sys.executable,str(entry),*map(str,args),'--json'],env=self.env,capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,code,p.stderr+p.stdout)
            return json.loads(p.stdout)
        cli('init',self.path,'--profile','github-flow','--apply')
        self.assertFalse((self.path/'AGENTS.md').exists())
        cli('hooks',self.path,'--apply')
        r=cli('doctor',self.path)
        self.assertEqual(r['integrations']['native_hooks']['status'],'configured')
        self.assertEqual(r['integrations']['ci']['status'],'unconfigured')
        blocked=subprocess.run(['git','-C',str(self.path),'commit','--allow-empty','-m','fix: blocked'],env=self.env,capture_output=True,text=True)
        self.assertNotEqual(blocked.returncode,0)
        self.git('switch','-c','feature/package')
        self.git('commit','--allow-empty','-m','feat: packaged')
        remote=self.path.parent/'remote.git';self.git('init','--bare',str(remote))
        self.git('remote','add','origin',str(remote));self.git('push','origin','feature/package')
        self.assertEqual(self.git('rev-parse','HEAD'),self.git('rev-parse','refs/heads/feature/package',cwd=remote))
        xml=self.path/'.git/gitflow.xml';xml.write_bytes(b'<!DOCTYPE policy><policy/>')
        rejected=subprocess.run(['git','-C',str(self.path),'commit','--allow-empty','-m','feat: forbidden'],env=self.env,capture_output=True,text=True)
        self.assertNotEqual(rejected.returncode,0)
        self.assertIn('unverified',rejected.stderr)
        self.assertFalse((self.path/'.gitflow/workflow.json').exists())

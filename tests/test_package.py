"""包的真实路径、快照、异目录运行与粒度技能安装。"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

class PackageTests(unittest.TestCase):
    def test_pack_and_run_from_other_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            temp=Path(folder);output=temp/'gitflow.zip'
            p=subprocess.run([sys.executable,str(ROOT/'scripts/package.py'),'--output',str(output)],text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr or p.stdout)
            with zipfile.ZipFile(output) as archive:
                self.assertFalse(any('__pycache__' in name or '.superpowers/' in name for name in archive.namelist()))
                archive.extractall(temp/'unpacked')
            packed=temp/'unpacked/gitflow'
            for script,args in [('gitflow.py',['version','--json']),('vendor_skills.py',['--check']),('validate_package.py',[])]:
                p=subprocess.run([sys.executable,str(packed/'scripts'/script),*args],cwd=temp,text=True,capture_output=True)
                self.assertEqual(p.returncode,0,p.stderr or p.stdout)
            messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25'}},
                      {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'gitflow_discover','arguments':{'path':str(temp)}}}]
            p=subprocess.run([sys.executable,str(packed/'scripts/gitflow.py'),'mcp'],cwd=temp,input='\n'.join(json.dumps(m) for m in messages)+'\n',text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr)
            result=json.loads(json.loads(p.stdout.splitlines()[1])['result']['content'][0]['text'])
            self.assertEqual(result['git_state'],'absent')
            for event in ('SessionStart','UserPromptSubmit','PreToolUse','PostToolUse','Stop'):
                payload={'cwd':str(temp),'tool_input':{'command':'git push --force origin main'}}
                p=subprocess.run([sys.executable,str(packed/'scripts/gitflow.py'),'hook','--event',event],
                                 cwd=packed,input=json.dumps(payload),text=True,capture_output=True)
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertEqual(json.loads(p.stdout),{})
            subprocess.run(['git','-C',str(temp),'init','-b','main'],check=True,capture_output=True)
            p=subprocess.run([sys.executable,str(packed/'scripts/gitflow.py'),'hook','--event','SessionStart'],
                             cwd=packed,input=json.dumps({'cwd':str(temp)}),text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('No native XML policy is initialized',json.loads(p.stdout)['hookSpecificOutput']['additionalContext'])
            self.assertFalse((temp/'.git/gitflow.xml').exists())

    def test_snapshot_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            copy=Path(folder)/'plugin';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('__pycache__','.superpowers'))
            file=copy/'vendor/git-skills/skills/git-commit/SKILL.md';file.write_text(file.read_text()+'\n被修改\n')
            p=subprocess.run([sys.executable,str(copy/'scripts/vendor_skills.py'),'--check'],text=True,capture_output=True)
            self.assertNotEqual(p.returncode,0)

    def test_each_skill_can_run_in_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            temp=Path(folder)
            for source in (ROOT/'vendor/git-skills/skills').iterdir():
                isolated=temp/source.name;shutil.copytree(source,isolated)
                p=subprocess.run([sys.executable,str(isolated/'scripts/inspect_repository.py'),str(temp)],cwd=temp,text=True,capture_output=True)
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertEqual(json.loads(p.stdout)['git_state'],'absent')
                (temp/'.git').mkdir()
                damaged=subprocess.run([sys.executable,str(isolated/'scripts/inspect_repository.py'),str(temp)],cwd=temp,text=True,capture_output=True)
                self.assertEqual(damaged.returncode,3,damaged.stderr)
                self.assertEqual(json.loads(damaged.stdout)['decision'],'unverified')
                (temp/'.git').rmdir()

    def test_profile_relationships_and_all_templates_validate(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from gitflow.policy import template,role_for
        profiles=list((ROOT/'profiles').glob('*.json'));self.assertEqual(len(profiles),8)
        for file in profiles:template(file.stem)
        policy=template('git-maintainer')
        self.assertIn('main',policy['roles']['maint']['merge_into'])
        self.assertNotIn('maint',policy['roles']['main']['merge_into'])
        policy=template('microsoft-release')
        self.assertIn('maintenance',policy['roles']['main']['merge_into'])
        self.assertNotIn('main',policy['roles']['maintenance']['merge_into'])
        self.assertEqual(role_for(policy,'release/1.0'),'maintenance')

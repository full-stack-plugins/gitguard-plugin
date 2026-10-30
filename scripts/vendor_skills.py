#!/usr/bin/env python3
"""将 git-skills 固定快照复制到插件；核对全部文件 SHA-256。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]

def files(root):
    result={}
    for directory in ('skills','profiles'):
        for file in sorted((root/directory).rglob('*')):
            if '__pycache__' in file.parts:continue
            if file.is_symlink():raise ValueError('snapshot symlink')
            if file.is_file():result[file.relative_to(root).as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
    result['sources.json']=hashlib.sha256((root/'sources.json').read_bytes()).hexdigest()
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    lock=ROOT/'skills.lock.json'
    if args.check:
        expected=json.loads(lock.read_text(encoding='utf-8'))
        if files(ROOT)!=expected['files']:raise SystemExit('技能或模板快照被修改，请重新审阅和锁定。')
        if args.source and files(args.source)!=expected['files']:raise SystemExit('上游技能发生漂移，不能冒充当前快照。')
        print(json.dumps({'decision':'allow','files':len(expected['files'])}))
    else:
        if not args.source:parser.error('vendor 需要明确 --source，check 可只核对包')
        source=args.source.resolve()
        for directory in ('skills','profiles'):
            if (ROOT/directory).exists():shutil.rmtree(ROOT/directory)
            shutil.copytree(source/directory,ROOT/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copyfile(source/'sources.json',ROOT/'sources.json')
        lock.write_text(json.dumps({'schema_version':'1.0.0','source_package':'full-stack-skills/git-skills','source_version':json.loads((source/'.claude-plugin/plugin.json').read_text(encoding='utf-8'))['version'],'files':files(ROOT)},ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'decision':'applied','files':len(files(ROOT))}))

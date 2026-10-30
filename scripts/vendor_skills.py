#!/usr/bin/env python3
"""Keep generic upstream bytes separate from plugin-owned registered skills."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
VENDOR=Path('vendor/git-skills')


def files(root, directories=('skills','profiles','vendor')):
    result={}
    for directory in directories:
        base=root/directory
        if base.is_symlink():raise ValueError('snapshot symlink')
        for file in sorted(base.rglob('*')):
            if '__pycache__' in file.parts:continue
            if file.is_symlink():raise ValueError('snapshot symlink')
            if file.is_file():result[file.relative_to(root).as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
    source=root/'sources.json'
    if source.is_symlink():raise ValueError('snapshot symlink')
    result['sources.json']=hashlib.sha256(source.read_bytes()).hexdigest()
    return result


def source_files(root):
    return files(root, ('skills','profiles'))


def committed_files(root, commit):
    names=subprocess.run(['git','-C',str(root),'ls-tree','-rz','--name-only',commit,'--','skills','profiles','sources.json'],capture_output=True,check=True).stdout.split(b'\0')
    names=[name.decode('utf-8') for name in names if name]
    result={}
    for name in names:
        data=subprocess.run(['git','-C',str(root),'show',commit+':'+name],capture_output=True,check=True).stdout
        result[name]=hashlib.sha256(data).hexdigest()
    return result


def snapshot_errors(root, source=None):
    lock=json.loads((root/'skills.lock.json').read_text(encoding='utf-8'))
    errors=[]
    if lock.get('schema_version')!='2.0.0':return ['Unsupported snapshot schema']
    if (lock.get('source_package')!='full-stack-skills/git-skills'
        or not re.fullmatch(r'[0-9a-f]{40}(?:[0-9a-f]{24})?',str(lock.get('source_commit','')))
        or not isinstance(lock.get('source_version'),str)
        or lock.get('registered_skills')!=['gitguard-init']
        or lock.get('layout')!='generic-vendor-plugin-owned-v1'):
        errors.append('Invalid source provenance metadata')
    if source and not errors:
        try:
            if committed_files(source,lock.get('source_commit',''))!=lock['source_files']:
                errors.append('Source commit content differs from lock')
        except (subprocess.CalledProcessError,UnicodeError):
            errors.append('Source commit cannot be verified')
    if files(root)!=lock['files']:errors.append('Packaged snapshot drift')
    if source_files(root/VENDOR)!=lock['source_files']:errors.append('Vendored upstream drift')
    if source and source_files(source)!=lock['source_files']:errors.append('Upstream source drift')
    for relative,digest in lock['source_files'].items():
        if relative.startswith('profiles/') or relative=='sources.json':
            if lock['files'].get(relative)!=digest:errors.append('Runtime template differs from upstream: '+relative)
    return errors


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.check:
        errors=snapshot_errors(ROOT,args.source)
        if errors:raise SystemExit('; '.join(errors))
        print(json.dumps({'decision':'allow','files':len(files(ROOT))}))
    else:
        if not args.source:parser.error('vendor requires explicit --source')
        source=args.source.resolve()
        if source==ROOT or ROOT.is_relative_to(source) or source.is_relative_to(ROOT):
            parser.error('upstream must be outside plugin')
        # Validate all source identities before touching the destination.
        original=source_files(source)
        names={p.name for p in (source/'skills').iterdir() if p.is_dir()}
        expected={'git-'+s for s in ('awesome','workflow','init','branch','audit','commit','sync','release','recovery')}
        if names!=expected:raise SystemExit('Expected generic git-* upstream skills')
        commit=subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
        dirty=subprocess.run(['git','-C',str(source),'status','--porcelain'],capture_output=True,text=True,check=True).stdout
        if dirty:raise SystemExit('Commit upstream source before locking provenance')
        if committed_files(source,commit)!=original:raise SystemExit('Source files are not the committed snapshot')
        # Check every output path before deleting or copying anything.
        for relative in ('vendor','vendor/git-skills','profiles','sources.json','skills.lock.json'):
            output=ROOT/relative
            if output.is_symlink() or not output.resolve().is_relative_to(ROOT.resolve()):
                raise SystemExit('Redirected snapshot output: '+relative)
        files(ROOT)  # Reject linked owned skills/profiles before any mutation.
        dest=ROOT/VENDOR
        if dest.is_symlink():raise SystemExit('snapshot symlink')
        if dest.exists():shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for directory in ('skills','profiles'):
            shutil.copytree(source/directory,dest/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copyfile(source/'sources.json',dest/'sources.json')
        if (ROOT/'profiles').exists():shutil.rmtree(ROOT/'profiles')
        shutil.copytree(source/'profiles',ROOT/'profiles')
        shutil.copyfile(source/'sources.json',ROOT/'sources.json')
        lock={'schema_version':'2.0.0','source_package':'full-stack-skills/git-skills',
              'source_version':json.loads((source/'.claude-plugin/plugin.json').read_text())['version'],
              'source_commit':commit,'source_files':original,'files':files(ROOT),
              'registered_skills':['gitguard-init'],'layout':'generic-vendor-plugin-owned-v1'}
        (ROOT/'skills.lock.json').write_text(json.dumps(lock,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        print(json.dumps({'decision':'applied','source_files':len(original),'files':len(lock['files'])}))

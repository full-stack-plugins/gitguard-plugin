#!/usr/bin/env python3
"""离线标准库包边界与快照校验；官方 Schema 开发验收另行执行。"""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from gitflow.policy import validate
from vendor_skills import files

def validate_package():
    errors=[]
    for file in ROOT.rglob('*'):
        if file.is_symlink() and not file.resolve().is_relative_to(ROOT):errors.append('路径越界 '+str(file))
    manifest=json.loads((ROOT/'plugin.json').read_text(encoding='utf-8'))
    allowed={'$schema','name','version','description','author','homepage','repository','license','keywords','extensions'}
    if set(manifest)-allowed or manifest['$schema']!='https://agent-plugins.org/schemas/1.0.0/plugin.schema.json':errors.append('manifest 字段/版本')
    if not re.fullmatch(r'(?!.*(--|\.\.))[a-z0-9][a-z0-9.-]{0,62}[a-z0-9]|[a-z0-9]',manifest['name']):errors.append('manifest 名称')
    mcp=json.loads((ROOT/'mcp.json').read_text(encoding='utf-8'))
    if set(mcp)!={'$schema','mcpServers'} or mcp['$schema']!='https://agent-plugins.org/schemas/1.0.0/mcp.schema.json':errors.append('MCP 顶层')
    for config in mcp['mcpServers'].values():
        if set(config)-{'type','command','args','env','cwd'} or config.get('type')!='stdio' or config.get('command')!='python3':errors.append('MCP 服务')
        if config.get('cwd')!='./' or config.get('args')!=['${PLUGIN_ROOT}/scripts/gitflow.py','mcp']:errors.append('MCP 启动路径')
        if set(config.get('env',{})) & {'PLUGIN_ROOT','PLUGIN_DATA'}:errors.append('MCP 保留变量')
    lock=json.loads((ROOT/'skills.lock.json').read_text(encoding='utf-8'))
    if files(ROOT)!=lock['files']:errors.append('技能/模板快照摘要不一致')
    for file in (ROOT/'profiles').glob('*.json'):validate(json.loads(file.read_text(encoding='utf-8')))
    for file in (ROOT/'scripts').rglob('*.py'):ast.parse(file.read_text(encoding='utf-8'))
    return errors

if __name__=='__main__':
    errors=validate_package()
    print(json.dumps({'decision':'deny' if errors else 'allow','errors':errors},ensure_ascii=False))
    raise SystemExit(bool(errors))

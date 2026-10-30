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
from vendor_skills import snapshot_errors

VERSION_MANIFESTS = ('package.json', 'dsh/package.json', 'kimi.plugin.json',
                     '.claude-plugin/plugin.json', '.codex-plugin/plugin.json',
                     '.zcode-plugin/plugin.json')


def version_errors(root, expected):
    errors = []
    for relative in VERSION_MANIFESTS:
        data = json.loads((root / relative).read_text(encoding='utf-8'))
        if data.get('version') != expected:
            errors.append('Plugin version mismatch: ' + relative)
    marketplace = json.loads((root / 'marketplace.json').read_text(encoding='utf-8'))
    for entry in marketplace.get('plugins', []):
        if entry.get('source') in ('.', './') and entry.get('version') != expected:
            errors.append('Plugin version mismatch: marketplace.json local entry')
    module = ast.parse((root / 'scripts/gitflow/git.py').read_text(encoding='utf-8'))
    versions = [ast.literal_eval(node.value) for node in module.body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'VERSION' for t in node.targets)]
    if versions != [expected]:
        errors.append('Plugin version mismatch: runtime')
    return errors


SKILL_NAMES = {'gitguard-init'}


def skill_name_errors(root):
    errors = []
    directory = root / 'skills'
    observed = {p.name for p in directory.iterdir() if p.is_dir()} if directory.is_dir() else set()
    if observed != SKILL_NAMES:
        errors.append('Public skill directories must use the plugin-owned gitguard-init identity')
    for name in sorted(SKILL_NAMES & observed):
        try:
            text = (directory / name / 'SKILL.md').read_text(encoding='utf-8')
            prompt = (directory / name / 'agents/openai.yaml').read_text(encoding='utf-8')
            if not text.startswith('---\nname: ' + name + '\n'):
                errors.append('Skill frontmatter identity mismatch: ' + name)
            if 'display_name: "' + name + '"' not in prompt or '$' + name not in prompt:
                errors.append('Skill host prompt identity mismatch: ' + name)
        except (OSError, UnicodeError):
            errors.append('Missing or unreadable skill identity: ' + name)
    return errors


def validate_package():
    errors=skill_name_errors(ROOT)
    for file in ROOT.rglob('*'):
        if file.is_symlink() and not file.resolve().is_relative_to(ROOT):errors.append('路径越界 '+str(file))
    manifest=json.loads((ROOT/'plugin.json').read_text(encoding='utf-8'))
    errors.extend(version_errors(ROOT, manifest['version']))
    allowed={'$schema','name','version','description','author','homepage','repository','license','keywords','extensions'}
    if set(manifest)-allowed or manifest['$schema']!='https://agent-plugins.org/schemas/1.0.0/plugin.schema.json':errors.append('manifest 字段/版本')
    if not re.fullmatch(r'(?!.*(--|\.\.))[a-z0-9][a-z0-9.-]{0,62}[a-z0-9]|[a-z0-9]',manifest['name']):errors.append('manifest 名称')
    mcp=json.loads((ROOT/'mcp.json').read_text(encoding='utf-8'))
    if set(mcp)!={'$schema','mcpServers'} or mcp['$schema']!='https://agent-plugins.org/schemas/1.0.0/mcp.schema.json':errors.append('MCP 顶层')
    for config in mcp['mcpServers'].values():
        if set(config)-{'type','command','args','env','cwd'} or config.get('type')!='stdio' or config.get('command')!='python3':errors.append('MCP 服务')
        if config.get('cwd')!='./' or config.get('args')!=['${PLUGIN_ROOT}/scripts/gitflow.py','mcp']:errors.append('MCP 启动路径')
        if set(config.get('env',{})) & {'PLUGIN_ROOT','PLUGIN_DATA'}:errors.append('MCP 保留变量')
    errors.extend(snapshot_errors(ROOT))
    for file in (ROOT/'profiles').glob('*.json'):validate(json.loads(file.read_text(encoding='utf-8')))
    for file in (ROOT/'scripts').rglob('*.py'):ast.parse(file.read_text(encoding='utf-8'))
    return errors

if __name__=='__main__':
    errors=validate_package()
    print(json.dumps({'decision':'deny' if errors else 'allow','errors':errors},ensure_ascii=False))
    raise SystemExit(bool(errors))

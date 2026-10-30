"""XML 唯一规则源与显式旧配置迁移。"""
import hashlib
import json
from pathlib import Path
import re

from .git import FlowError, report, reason, require_repo, valid_branch
from .layout import state_file
from .organization import resolve, validate_pointer
from .storage import atomic_json, locked, read_json, safe_dir

ASSETS = Path(__file__).resolve().parents[2] / 'profiles'
TOP = {'schema_version', 'profile', 'revision', 'roles', 'primary_remote',
       'merge_method', 'commit_message_pattern', 'collaboration'}
ROLE = {'name', 'pattern', 'required', 'allow_commit', 'create_from', 'merge_into'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def validate(value):
    """拒绝未知字段、错误类型、无效角色关系与复杂不受限模式。"""
    if not isinstance(value, dict):
        raise FlowError('policy_schema_invalid', '工作流必须是对象。')
    version = value.get('schema_version')
    fields = TOP if version == '1.0.0' else TOP | {'rules', 'extends'}
    if version not in ('1.0.0', '2.0.0') or set(value) != fields:
        raise FlowError('policy_schema_invalid', '工作流字段或版本不符合契约。')
    if version == '2.0.0':
        from .rules import validate_rules
        validate_rules(value['rules'])
        validate_pointer(value['extends'])
    if not isinstance(value['profile'], str) or not re.fullmatch(r'[a-z0-9-]{1,64}', value['profile']):
        raise FlowError('policy_profile_invalid', '工作流标识无效。')
    if type(value['revision']) is not int or value['revision'] < 1:
        raise FlowError('policy_revision_invalid', '规则修订必须为正整数。')
    if value['merge_method'] not in ('merge', 'no-ff', 'squash', 'ff-only'):
        raise FlowError('policy_merge_invalid', '不支持的合并方式。')
    if value['collaboration'] not in ('shared', 'fork'):
        raise FlowError('policy_collaboration_invalid', '协作模式只能是 shared 或 fork。')
    remote = value['primary_remote']
    if not isinstance(remote, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', remote):
        raise FlowError('policy_remote_invalid', '权威远端必须是单一远端名称。')
    roles = value['roles']
    if not isinstance(roles, dict) or not 1 <= len(roles) <= 32:
        raise FlowError('policy_roles_invalid', '工作流需要 1–32 个分支角色。')
    for key, role in roles.items():
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,31}', key) or not isinstance(role, dict) or set(role) != ROLE:
            raise FlowError('policy_role_invalid', '分支角色字段无效。')
        for flag in ('required', 'allow_commit'):
            if type(role[flag]) is not bool:
                raise FlowError('policy_role_invalid', '角色标志必须是真实布尔值。')
        if (role['name'] is None) == (role['pattern'] is None):
            raise FlowError('policy_role_invalid', '角色需要固定名称或匹配模式之一。')
        if role['required'] and role['name'] is None:
            raise FlowError('policy_role_invalid', '必需角色应有固定名称；临时类型不要求预创建。')
        if role['name'] is not None and (not isinstance(role['name'], str) or len(role['name']) > 240):
            raise FlowError('policy_role_invalid', '固定分支名称无效。')
        check_pattern(role['pattern'])
        for field in ('create_from', 'merge_into'):
            items = role[field]
            if not isinstance(items, list) or any(not isinstance(x, str) or x not in roles for x in items) or len(set(items)) != len(items):
                raise FlowError('policy_relation_invalid', '分支关系必须引用存在且唯一的角色。')
    check_pattern(value['commit_message_pattern'])
    return value


def check_pattern(pattern):
    if pattern is None:
        return
    if not isinstance(pattern, str) or not 1 <= len(pattern) <= 240 or '(?' in pattern or '\\1' in pattern:
        raise FlowError('policy_pattern_invalid', '模式需要受限正则表达式。')
    # 拒绝嵌套量词，避免本地定义耗尽 Hook 预算。
    if re.search(r'\)[+*{?]|\\[1-9]', pattern):
        raise FlowError('policy_pattern_invalid', '不接受嵌套无界量词。')
    # 只接受一个无界单原子重复，避免串行重叠量词组合爆炸。
    atoms = re.sub(r'\[[^\]]*\]', 'X', pattern)
    if '{' in atoms or len(re.findall(r'(?<!\\)[+*]', atoms)) > 1:
        raise FlowError('policy_pattern_invalid', '模式最多含一个单原子无界重复，不支持计数重复。')
    try:
        re.compile(pattern)
    except re.error as exc:
        raise FlowError('policy_pattern_invalid', '正则表达式无效。') from exc


def template(name):
    if not re.fullmatch(r'[a-z0-9-]{1,64}', name):
        raise FlowError('profile_unknown', '工作流模板不存在。')
    path = ASSETS / (name + '.json')
    if not path.is_file():
        raise FlowError('profile_unknown', '工作流模板不存在。')
    return validate(read_json(path))


def role_for(policy, name):
    if not isinstance(name, str) or len(name) > 240:
        return None
    matches = [key for key, role in policy['roles'].items()
               if role['name'] == name or (role['pattern'] is not None and re.fullmatch(role['pattern'], name))]
    if len(matches) > 1:
        raise FlowError('branch_role_ambiguous', '分支命中多个角色，请修订规则。')
    return matches[0] if matches else None


def activation_path(facts):
    return state_file(facts, 'activation.json')


def load(facts):
    from .xml_policy import read_policy
    policy = read_policy(facts)
    if policy.get('extends') is not None:
        raise FlowError('xml_external_policy', '运行时 XML 必须自包含；请在显式迁移时展开组织规则。')
    return policy, {'schema_version':'1.0.0', 'mode':'xml', 'policy':policy, 'sha256':digest(policy)}


def explanation(policy):
    lines = ['# 项目 Git 工作流', '', '此说明读取 git-common-dir/gitflow.xml；XML 是唯一运行时规则源。', '',
             f"工作流：{policy['profile']}；修订：{policy['revision']}；权威远端：{policy['primary_remote']}", '',
             '| 角色 | 名称/模式 | 长期必需 | 允许提交 | 来源角色 | 合入角色 |', '|---|---|---|---|---|---|']
    for key, role in policy['roles'].items():
        lines.append(f"| {key} | {role['name'] or role['pattern']} | {role['required']} | {role['allow_commit']} | {', '.join(role['create_from'])} | {', '.join(role['merge_into'])} |")
    return '\n'.join(lines) + '\n'


def write_activation(facts, policy, mode=None):
    """Compatibility API: writes only the single XML authority."""
    from .xml_policy import write_policy
    policy = validate(policy)
    if policy.get('extends') is not None:
        policy = resolve(policy, facts['root'])
        policy['extends'] = None
    for role in policy['roles'].values():
        if role['name'] and not valid_branch(facts['root'],role['name']):
            raise FlowError('policy_branch_name_invalid','规则含 Git 不接受的固定分支名称。')
    write_policy(facts,policy)
    return {'schema_version':'1.0.0','mode':'xml','policy':policy,'sha256':digest(policy)}


def activate(path, apply=False):
    """Legacy command validates XML; never imports JSON implicitly."""
    facts=require_repo(path);policy,active=load(facts)
    return report('policy.activate','allow',profile=policy['profile'],revision=policy['revision'],
                  policy_sha256=active['sha256'],mode='xml',unchanged=True)


def migrate(path, apply=False):
    from .xml_policy import policy_path
    from .initialization import guidance_snapshot, guidance_content, write_guidance
    facts=require_repo(path)
    if policy_path(facts).exists():raise FlowError('xml_already_exists','XML 已存在，拒绝旧规则覆盖。')
    legacy=activation_path(facts)
    candidate=safe_dir(facts['root'],'.gitflow/workflow.json')
    policy=None
    if legacy.exists():
        old=read_json(legacy)
        if not isinstance(old,dict) or set(old)!={'schema_version','mode','policy','sha256'} or old['schema_version']!='1.0.0' or old['mode'] not in ('shared','local'):
            raise FlowError('activation_invalid','旧激活记录损坏。')
        policy=validate(old['policy'])
        if digest(policy)!=old['sha256']:raise FlowError('activation_invalid','旧快照摘要不一致。')
    if candidate.exists():
        defined=resolve(validate(read_json(candidate)),facts['root'])
        if policy is not None and defined!=policy:raise FlowError('legacy_conflict','旧候选与快照不一致，不能猜测。')
        policy=defined
    if policy is None:raise FlowError('legacy_missing','没有可迁移的旧 JSON。')
    policy=resolve(policy,facts['root'])
    if 'extends' in policy:policy['extends']=None
    agents=safe_dir(facts['root'],'AGENTS.md');before=guidance_snapshot(agents);content=guidance_content(before[1])
    snapshots={p:p.read_bytes() for p in (legacy,candidate) if p.exists()}
    if apply:
        with locked(facts):
            def unchanged(p, raw):
                if p == legacy and not p.exists():
                    return read_json(activation_path(facts)) == json.loads(raw)
                return p.exists() and p.read_bytes()==raw
            if policy_path(facts).exists() or any(not unchanged(p,raw) for p,raw in snapshots.items()):
                raise FlowError('policy_changed','迁移输入已变化。')
            if guidance_snapshot(agents)!=before:raise FlowError('agents_changed','AGENTS.md 已变化。')
            write_activation(facts,policy)
            try:write_guidance(agents,before,content)
            except (OSError,FlowError) as exc:raise FlowError('init_partial','XML 已写入，旧文件保留；重复 init 修复引导。') from exc
    return report('policy.migrate','applied' if apply else 'preview',profile=policy['profile'],mode='xml',
                  policy_sha256=digest(policy),legacy_preserved=True)

"""项目接入、只读审计与动作门禁。"""
import re
from .git import FlowError, discover, oid, reason, report, require_repo, run, valid_branch
from .policy import activation_path, digest, explanation, load, role_for, template, validate, write_activation
from .storage import atomic_json, locked, read_json, safe_dir
from .provenance import read_origins, trusted
from . import rules
from .organization import resolve


def initialize(path, profile=None, mode='shared', apply=False, initialize_git=False):
    from .initialization import initialize as initialize_xml
    return initialize_xml(path, profile, mode, apply, initialize_git)


def metadata_checks(facts, policy, message):
    """待提交身份由 Git 自己解析，保持作者环境与原生提交一致。"""
    if policy['schema_version'] == '1.0.0':
        return []
    raw = run(facts['root'], 'var', 'GIT_AUTHOR_IDENT', check=False).stdout.decode().strip()
    match = re.fullmatch(r'(.*?) <([^<>]*)> [0-9]+ [+-][0-9]{4}', raw)
    context = {'message': message, 'author_name': match[1] if match else None, 'author_email': match[2] if match else None}
    return rules.evaluate(policy, context)


def gate(path, action, source=None, target=None, message=None):
    facts = require_repo(path)
    policy, active = load(facts)
    if facts['branch'] is None:
        raise FlowError('detached_head', 'HEAD 分离，先明确工作分支。')
    if facts['operation_states']:
        raise FlowError('operation_in_progress', '仓库存在中断操作，先诊断恢复。')
    current_role = role_for(policy, facts['branch'])
    if not current_role:
        return report('gate.' + action, 'deny', [reason('branch_name_unmatched', '当前分支不符合项目角色命名。')], quality_decision='not_evaluated')
    reasons, checks = [], []
    if action == 'commit':
        if not policy['roles'][current_role]['allow_commit']:
            reasons.append(reason('protected_branch_commit', '当前角色禁止直接提交，应进入任务分支。'))
        pattern = policy['commit_message_pattern']
        if pattern and (message is None or len(message) > 4096):
            raise FlowError('commit_message_required', '需要有界提交消息以验证项目约定。')
        if pattern and not re.fullmatch(pattern, message):
            reasons.append(reason('commit_message_invalid', '提交消息不符合项目约定。'))
        checks = metadata_checks(facts, policy, message)
        reasons.extend(rules.reasons(checks))
    elif action in ('merge', 'rebase', 'push', 'pull'):
        if not source or not target:
            raise FlowError('branch_identity_required', '动作需要明确源分支与目标分支。')
        if not valid_branch(path, source) or not valid_branch(path, target):
            raise FlowError('branch_identity_invalid', '源与目标必须是实际分支名称。')
        if action in ('merge', 'rebase') and (oid(path, 'refs/heads/' + source) is None or oid(path, 'refs/heads/' + target) is None):
            raise FlowError('branch_identity_unknown', '集成门禁需要存在的本地源和目标分支。')
        sr, tr = role_for(policy, source), role_for(policy, target)
        if not sr or not tr:
            reasons.append(reason('branch_name_unmatched', '源或目标不符合项目命名。'))
        elif action in ('push', 'pull') and source != target:
            reasons.append(reason('remote_mapping_denied', '当前实现只支持同名远端分支映射。'))
        elif action == 'merge' and tr not in policy['roles'][sr]['merge_into']:
            reasons.append(reason('merge_target_denied', '该来源角色不允许合入目标角色。'))
        elif action == 'rebase' and tr not in policy['roles'][sr]['create_from']:
            reasons.append(reason('rebase_target_denied', '该分支不允许以此角色重建基线。'))
    else:
        raise FlowError('action_unknown', '未建模的 Git 动作不能放行。')
    verdict = 'unverified' if rules.decision(checks) == 'unverified' else ('deny' if reasons else 'allow')
    return report('gate.' + action, verdict, reasons, checks=checks, branch=facts['branch'],
                  role=current_role, revision=policy['revision'], policy_sha256=active['sha256'], quality_decision='not_evaluated')


def audit(path):
    facts = require_repo(path)
    policy, active = load(facts)
    reasons, observations = [], []
    for key, role in policy['roles'].items():
        if role['required'] and role['name'] not in facts['branches']:
            reasons.append(reason('required_branch_missing', '缺少长期分支。', role=key, branch=role['name']))
    _, origins = read_origins(facts, strict=False)
    for name in facts['branches']:
        role = role_for(policy, name)
        if not role:
            reasons.append(reason('branch_name_unmatched', '已有分支无法匹配角色。', branch=name))
        elif policy['roles'][role]['name'] is None and not trusted(facts, policy, active, name, origins.get(name)):
            observations.append(reason('branch_origin_unknown', '来源记录缺失、无效、过期或无法核验；共同祖先不证明创建来源。', branch=name))
    if facts['operation_states']:
        observations.append(reason('operation_in_progress', '存在未完成 Git 操作。'))
    observations.extend([reason('remote_state_unverified', '当前远端信息只来自本地跟踪记录。'),
                         reason('server_protection_unverified', '本地规则不证明服务端分支保护已配置。')])
    if facts['shallow']:
        observations.append(reason('shallow_history', '浅克隆无法证明完整历史。'))
    return report('audit', 'deny' if reasons else 'allow', reasons, facts=facts,
                  profile=policy['profile'], mode=active['mode'], observations=observations,
                  missing_required_roles=[r['role'] for r in reasons if r['code'] == 'required_branch_missing'])

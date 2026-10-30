"""可信 XML 分发尚未配置；保留显式策略输入的只读范围计算内核。"""
import re
from .git import FlowError, oid, reason, report, require_repo, run, text, valid_branch
from .policy import digest, role_for, validate
from . import rules


def commit_oid(path, value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', value) or oid(path, value) != value:
        raise FlowError('ci_object_unknown', 'CI 必须提供本地存在的完整 commit OID；检查不会自动 fetch。')
    return value


def aggregate(values):
    if 'unverified' in values:
        return 'unverified'
    return 'deny' if 'deny' in values else 'allow'


def check(path, base, head, source, target, message_mode='commits', message=None):
    # No trusted XML distribution channel has been configured for CI. Neither
    # PR workspace XML nor legacy JSON may approve the PR that supplied it.
    raise FlowError('ci_policy_unconfigured', 'CI 尚未配置可信 XML 分发；不能使用 PR 自带规则或旧 JSON 放行。')


def evaluate_range(path, base, head, source, target, policy, message_mode='commits', message=None):
    """Pure evaluation kernel; caller must already possess trusted policy.

    The public CI/CLI does not expose this until trusted XML provisioning exists.
    Native checks and tests may reuse the bounded object evaluation algorithm.
    """
    facts = require_repo(path)
    if facts['shallow']:
        raise FlowError('ci_history_incomplete', '浅克隆不能证明完整 PR 范围，先由 CI 明确获取历史。')
    base, head = commit_oid(path, base), commit_oid(path, head)
    if not valid_branch(path, source) or not valid_branch(path, target):
        raise FlowError('ci_branch_required', '需要明确有效的源/目标分支。')
    if message_mode not in ('commits', 'squash'):
        raise FlowError('ci_message_mode_invalid', '消息模式必须为 commits 或 squash。')
    if message_mode == 'squash' and (not isinstance(message, str) or not message.strip() or len(message) > 4096):
        raise FlowError('ci_squash_message_required', 'squash 需要明确且有界的候选消息，不能猜测最终消息。')
    if run(path, 'merge-base', base, head, check=False).returncode != 0:
        raise FlowError('ci_history_unrelated', 'base 与 head 无法证明具有共同历史。')
    commits = text(path, 'rev-list', '--reverse', '--max-count=501', base + '..' + head).splitlines()
    if len(commits) > 500:
        raise FlowError('ci_range_limit', '提交范围超过 500 条预算，不能部分检查后报告通过。')
    policy = validate(policy)
    if policy.get('extends') is not None:
        raise FlowError('ci_policy_unconfigured','范围检查需要自包含的可信 XML 规则。')
    for role in policy['roles'].values():
        if role['name'] and not valid_branch(path, role['name']):
            raise FlowError('policy_branch_name_invalid', '规则含无效固定分支名。')
    sr, tr = role_for(policy, source), role_for(policy, target)
    violations = []
    if not sr or not tr:
        violations.append(reason('branch_name_unmatched', 'PR 分支不符合项目角色命名。'))
    elif tr not in policy['roles'][sr]['merge_into']:
        violations.append(reason('merge_target_denied', 'PR 源角色不允许合入目标角色。'))
    records = []
    for commit in commits:
        raw = run(path, 'show', '-s', '--format=%an%x00%ae%x00%B', commit).stdout.decode().rstrip('\n').split('\0')
        if len(raw) != 3:
            raise FlowError('ci_metadata_invalid', '提交元数据无法完整解析。')
        author, email, body = raw
        context = {'author_name': author, 'author_email': email, 'message': body}
        scopes = ('message', 'author') if message_mode == 'commits' else ('author',)
        checks = rules.evaluate(policy, context, scopes)
        problems = rules.reasons(checks)
        if message_mode == 'commits' and policy['commit_message_pattern'] and (len(body) > 4096 or not re.fullmatch(policy['commit_message_pattern'], body)):
            problems.append(reason('commit_message_invalid', '提交不符合既有项目消息表达式。'))
        verdict = 'unverified' if rules.decision(checks) == 'unverified' else ('deny' if problems else 'allow')
        records.append({'oid': commit, 'decision': verdict, 'checks': checks, 'reasons': problems})
    squash_checks, squash_reasons = [], []
    if message_mode == 'squash':
        # 候选提交的作者尚未由托管平台确定；签署规则不能凭空冒用任一作者。
        context = {'message': message, 'author_name': None, 'author_email': None}
        squash_checks = rules.evaluate(policy, context, ('message',))
        squash_reasons = rules.reasons(squash_checks)
        if policy['commit_message_pattern'] and not re.fullmatch(policy['commit_message_pattern'], message):
            squash_reasons.append(reason('commit_message_invalid', 'squash 候选不符合项目消息表达式。'))
    tags = text(path, 'tag', '--points-at', head).splitlines()
    tag_checks = rules.evaluate(policy, {'tags': tags}, ('tag',))
    verdict = aggregate([r['decision'] for r in records] + [rules.decision(tag_checks), rules.decision(squash_checks), 'deny' if violations or squash_reasons else 'allow'])
    return report('check', verdict, violations + squash_reasons + rules.reasons(tag_checks), base=base, head=head,
                  source=source, target=target, policy_source='caller_supplied_no_distribution_attestation', policy_sha256=digest(policy), revision=policy['revision'],
                  commit_count=len(records), commits=records, message_mode=message_mode, squash_checks=squash_checks,
                  tag_checks=tag_checks, branch_origin='not_inferred', server_protection='unverified')

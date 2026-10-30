"""Explicit selection and initialization of the sole XML policy authority."""
from pathlib import Path
from .git import FlowError, discover, report, require_repo, run
from .storage import locked


def initialize(path, profile=None, mode='shared', apply=False, initialize_git=False):
    from .policy import activation_path, load, template
    from .xml_policy import policy_path, write_policy
    facts = discover(path, inspect_worktree=False)
    if mode not in ('shared', 'local'):
        raise FlowError('mode_invalid', '未知兼容模式。')
    absent = facts['git_state'] == 'absent'
    if absent and not initialize_git:
        raise FlowError('git_initialization_required', '需要显式 initialize-git，不能猜测初始化仓库。')
    root = Path(facts['root'] if not absent else path).resolve()
    if not absent and policy_path(facts).exists():
        policy, _ = load(facts)
        if profile and profile != policy['profile']:
            raise FlowError('policy_already_exists', '已有 XML 不由 init 替换。')
    else:
        if not profile:
            raise FlowError('profile_selection_required', '请选择八种工作流之一；非交互必须指定 --profile。')
        policy = template(profile)
        if not absent and (activation_path(facts).exists() or (root / '.gitflow/workflow.json').exists()):
            raise FlowError('legacy_migration_required', '发现旧 JSON；请显式 policy --operation migrate，不覆盖原规则。')
    result = report('init', 'applied' if apply else 'preview', profile=policy['profile'], mode='xml',
                    policy_location='git-common-dir/gitflow.xml', automatic_enforcement=False,
                    missing_required_roles=[k for k, role in policy['roles'].items()
                                            if role['required'] and role['name'] not in facts.get('branches', [])],
                    next_actions=[{'action': 'audit', 'message': '检查分支与实际接线。'},
                                  {'action': 'hooks', 'message': '预览并显式安装 Git 原生 hooks；已有管理器需核验接线。'}])
    if not apply:
        return result
    if absent:
        run(path, 'init', '-b', 'main')
        facts = require_repo(path, inspect_worktree=False)
    with locked(facts):
        if policy_path(facts).exists():
            current, _ = load(facts)
            if current != policy:
                raise FlowError('policy_changed', 'XML 发生变化。')
        else:
            write_policy(facts, policy)
    return result

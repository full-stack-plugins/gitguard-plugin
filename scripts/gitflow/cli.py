"""CLI 参数边界与统一 JSON 错误结果。"""
import argparse
import json
from .git import FlowError, VERSION, discover, reason, report
from .policy import activate
from .service import audit, gate, initialize
from .operations import branch, sync, release, recovery
from .context import context
from .hooks import hook_main, install_native, native_main


class FlowParser(argparse.ArgumentParser):
    """用法错误也输出机器可读结果，退出码为 2。"""
    def error(self, message):
        print(json.dumps(report('usage','error',[reason('usage_invalid',message)]),ensure_ascii=False))
        raise SystemExit(2)


def parser():
    p = FlowParser(description='项目 Git 分支治理；默认只读或预览。')
    p.add_argument('command', choices=['version', 'discover', 'init', 'audit', 'gate', 'policy', 'branch', 'sync', 'release', 'recovery', 'context', 'hooks', 'organization', 'doctor', 'check', 'status', 'report'])
    p.add_argument('path', nargs='?', default='.')
    p.add_argument('--json', action='store_true')
    p.add_argument('--profile')
    p.add_argument('--mode', choices=['shared', 'local'], default='shared')
    p.add_argument('--apply', action='store_true')
    p.add_argument('--initialize-git', action='store_true')
    p.add_argument('--operation', default='activate')
    p.add_argument('--action', choices=['commit', 'push', 'pull', 'merge', 'rebase'])
    p.add_argument('--source')
    p.add_argument('--target')
    p.add_argument('--message')
    p.add_argument('--name')
    p.add_argument('--remote')
    p.add_argument('--targets')
    p.add_argument('--commit')
    p.add_argument('--choice')
    p.add_argument('--operation-id')
    p.add_argument('--sha256')
    p.add_argument('--base')
    p.add_argument('--head')
    p.add_argument('--message-mode', choices=['commits', 'squash'], default='commits')
    p.add_argument('--message-file')
    return p


def dispatch(a):
    if a.command == 'version':
        return report('version', version=VERSION)
    if a.command == 'discover':
        return discover(a.path)
    if a.command == 'init':
        return initialize(a.path, a.profile, a.mode, a.apply, a.initialize_git)
    if a.command == 'audit':
        return audit(a.path)
    if a.command == 'check':
        from .ci import check
        if a.message_file:
            from pathlib import Path
            file = Path(a.message_file)
            if file.is_symlink() or not file.is_file() or file.stat().st_size > 4096:
                raise FlowError('ci_message_file_invalid', '候选消息文件无效。')
            if a.message is not None:
                raise FlowError('ci_message_ambiguous', '候选消息不能同时来自两个输入。')
            a.message = file.read_text().strip()
        return check(a.path, a.base, a.head, a.source, a.target, a.message_mode, a.message)
    if a.command == 'organization':
        from .organization import import_baseline
        return import_baseline(a.path, a.source, a.name, a.sha256, a.apply)
    if a.command == 'doctor':
        from .diagnostics import doctor
        return doctor(a.path)
    if a.command in ('status', 'report'):
        from .diagnostics import doctor
        facts = discover(a.path)
        diagnostics = doctor(a.path)
        result = report(a.command, discovery=facts, diagnostics=diagnostics)
        if diagnostics.get('decision') == 'unverified':
            result['decision'] = 'unverified'
        return result
    if a.command == 'policy':
        if a.operation == 'migrate':
            from .policy import migrate
            return migrate(a.path,a.apply)
        if a.operation == 'describe':
            from .diagnostics import describe
            return describe(a.path)
        if a.operation != 'activate':
            raise FlowError('operation_unknown', '未知规范操作。')
        return activate(a.path, a.apply)
    if a.command == 'gate':
        if not a.action:
            raise FlowError('action_required', 'gate 需要 action。')
        return gate(a.path, a.action, a.source, a.target, a.message)
    if a.command == 'branch':
        return branch(a.path, a.operation, a.name, a.source, a.target, a.apply)
    if a.command == 'sync':
        return sync(a.path, a.operation, a.source, a.target, a.remote, a.apply)
    if a.command == 'release':
        return release(a.path, a.operation, a.name, a.source, a.targets, a.commit, a.apply)
    if a.command == 'recovery':
        return recovery(a.path, a.operation, a.target, a.commit, a.apply, a.operation_id)
    if a.command == 'context':
        return context(a.path, a.choice, a.apply)
    if a.command == 'hooks':
        return install_native(a.path, a.apply)
    raise FlowError('command_unknown', '命令未实现。')


def main(argv=None):
    from .stdio import configure_stdio
    configure_stdio()
    import sys
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == 'mcp':
        from .mcp import serve
        return serve()
    if argv and argv[0] in ('hook', 'native'):
        hp = argparse.ArgumentParser()
        hp.add_argument('command')
        hp.add_argument('--event')
        hp.add_argument('--kind')
        hp.add_argument('arguments', nargs='*')
        # Python 3.11 的普通解析不能处理选项后的星号位置参数与 --。
        h = hp.parse_intermixed_args(argv)
        return hook_main(h.event) if h.command == 'hook' else native_main(h.kind, h.arguments)
    a = parser().parse_args(argv)
    try:
        if a.command=='init' and not a.profile and sys.stdin.isatty() and not a.json:
            from .policy import ASSETS
            from .xml_policy import policy_path
            facts=discover(a.path, inspect_worktree=False)
            if facts['git_state']=='absent' or not policy_path(facts).exists():
                choices=sorted(p.stem for p in ASSETS.glob('*.json'))
                print('Select GitFlow profile: '+', '.join(choices), file=sys.stderr)
                try: a.profile=input('Profile: ').strip()
                except (EOFError,KeyboardInterrupt) as exc:
                    raise FlowError('profile_selection_cancelled','未完成工作流选择；未写入。') from exc
        result = dispatch(a)
    except FlowError as exc:
        result = report(a.command, exc.decision, [reason(exc.code, exc.message)])
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError):
        result = report(a.command, 'error', [reason('internal_error', '处理失败，不能采用不完整结果。')])
    print(json.dumps(result, ensure_ascii=False, indent=None if a.json else 2))
    return {'allow': 0, 'preview': 0, 'applied': 0, 'deny': 1, 'unverified': 3, 'error': 4}[result['decision']]

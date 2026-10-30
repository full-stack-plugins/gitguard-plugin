"""Git 事实查询与版本化结果；只调用独立 argv。"""
import os
from pathlib import Path
import subprocess
import selectors
import signal
import time

VERSION = '0.1.0'


class FlowError(Exception):
    """不能可靠完成操作的明确原因。"""
    def __init__(self, code, message, decision='unverified'):
        super().__init__(message)
        self.code, self.message, self.decision = code, message, decision


def run(path, *args, check=True, timeout=20):
    """在目标目录执行 Git，返回完整进程结果；失败不暴露远端凭据。"""
    env = dict(os.environ)
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR'):
        env.pop(key, None)
    env['GIT_TERMINAL_PROMPT'] = '0'
    env['GIT_EDITOR'] = 'true'
    env['GIT_SEQUENCE_EDITOR'] = 'true'
    for key in ('GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CONFIG_PARAMETERS'):
        env.pop(key, None)
    if 'GIT_CONFIG_COUNT' in env:
        env.pop('GIT_CONFIG_COUNT')
        for key in list(env):
            if key.startswith(('GIT_CONFIG_KEY_', 'GIT_CONFIG_VALUE_')):
                env.pop(key)
    env['LC_ALL'] = 'C'
    proc = None
    try:
        proc = subprocess.Popen(['git', '-C', str(path), *args], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        buffers = [bytearray(), bytearray()]
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate((proc.stdout, proc.stderr)):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, index)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise FlowError('git_timeout', 'Git 操作超时；需要重新读取目标状态。')
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        buffers[key.data].extend(chunk)
                        if sum(map(len, buffers)) > 4 * 1024 * 1024:
                            raise FlowError('git_output_limit', 'Git 输出超过预算，不采用截断结果。')
        code = proc.wait(timeout=max(0.01, deadline-time.monotonic()))
        p = subprocess.CompletedProcess(proc.args, code, bytes(buffers[0]), bytes(buffers[1]))
    except FileNotFoundError as exc:
        raise FlowError('git_unavailable', 'Git 命令不可用，请先恢复已有工具。') from exc
    except subprocess.TimeoutExpired as exc:
        raise FlowError('git_timeout', 'Git 操作超时；需要重新读取目标状态。') from exc
    except OSError as exc:
        raise FlowError('git_io_error', 'Git 进程无法启动或读取。') from exc
    finally:
        if proc is not None:
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
            proc.stdout.close()
            proc.stderr.close()
    if check and p.returncode:
        raise FlowError('git_command_failed', 'Git 操作未完成，请检查仓库、身份、冲突或远端权限。')
    return p


def text(path, *args, check=True):
    return run(path, *args, check=check).stdout.decode('utf-8', errors='strict').strip()


def oid(path, ref='HEAD'):
    p = run(path, 'rev-parse', '--verify', ref + '^{commit}', check=False)
    return p.stdout.decode().strip() if p.returncode == 0 else None


def report(action, decision='allow', reasons=None, **fields):
    return {'schema_version': '1.0.0', 'action': action, 'decision': decision,
            'reasons': reasons or [], 'next_actions': [], **fields}


def reason(code, message, **fields):
    return {'code': code, 'message': message, **fields}


def discover(path):
    """发现父仓、linked worktree、空历史及操作状态；不会写入。"""
    requested = Path(path).expanduser().resolve()
    if not requested.is_dir():
        raise FlowError('path_not_directory', '项目路径必须是已存在目录。')
    p = run(requested, 'rev-parse', '--show-toplevel', check=False)
    if p.returncode:
        bare = text(requested, 'rev-parse', '--is-bare-repository', check=False)
        if bare == 'true':
            raise FlowError('bare_repository', '分支治理操作需要工作树，不能在 bare 仓库执行。')
        if any((parent / '.git').exists() for parent in (requested, *requested.parents)) or b'not a git repository' not in p.stderr:
            raise FlowError('repository_unreadable', 'Git 状态无法可靠读取；不能把损坏、权限或信任失败视为无 Git。')
        return report('discover', git_state='absent', root=str(requested), branch=None,
                      next_actions=[{'action': 'ask_git_initialization',
                                     'question': '当前项目未受 Git 管理。是否初始化 Git 并采用约定工作流，或暂不启用？'}])
    root = Path(p.stdout.decode().strip()).resolve()
    git_dir = Path(text(root, 'rev-parse', '--absolute-git-dir')).resolve()
    common = Path(text(root, 'rev-parse', '--path-format=absolute', '--git-common-dir')).resolve()
    symbolic = text(root, 'symbolic-ref', '--quiet', 'HEAD', check=False)
    branch = symbolic[11:] if symbolic.startswith('refs/heads/') else None
    head = oid(root)
    lines = text(root, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads').splitlines()
    ref_oids = {line.split(' ',1)[0][11:]:line.split(' ',1)[1] for line in lines}
    refs = list(ref_oids)
    remotes = text(root, 'remote').splitlines()
    status = run(root, 'status', '--porcelain=v1', '-z').stdout
    entries = [x for x in status.split(b'\0') if x]
    states = [name for name in ('MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD',
                              'REVERT_HEAD', 'BISECT_LOG') if (git_dir / name).exists()]
    return report('discover', git_state='unborn' if head is None else 'repository',
                  root=str(root), git_dir=str(git_dir), common_dir=str(common),
                  branch=branch, head=head, branches=refs, ref_oids=ref_oids, remotes=remotes,
                  dirty=bool(entries), dirty_entries=len(entries), operation_states=states,
                  shallow=text(root, 'rev-parse', '--is-shallow-repository') == 'true',
                  remote_observation='local_tracking_only')


def require_repo(path):
    facts = discover(path)
    if facts['git_state'] == 'absent':
        raise FlowError('git_absent', '当前项目未受 Git 管理；先确认是否初始化。')
    return facts


def valid_branch(path, name):
    if not isinstance(name, str) or not name or len(name) > 240 or name.startswith('@{-'):
        return False
    return run(path, 'check-ref-format', '--branch', name, check=False).returncode == 0


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description='只读 Git 仓库发现')
    parser.add_argument('path')
    args = parser.parse_args()
    try:
        result = discover(args.path)
    except FlowError as exc:
        result = report('discover', exc.decision, [reason(exc.code, exc.message)])
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(3 if result['decision'] == 'unverified' else 0)

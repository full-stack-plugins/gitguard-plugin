"""项目 .gitflow/state 定位与旧 Git 元数据的显式迁移。"""
import hashlib
import os
from pathlib import Path
import shlex
import shutil

from .git import FlowError, run, text
from .storage import atomic_json, read_json, safe_dir, _redirected


def state_dir(facts):
    """只读定位共享锚点；Git 配置仅保存相对定位信息。"""
    common = Path(facts['common_dir']).resolve()
    pointer = text(facts['root'], 'config', '--local', '--get', 'gitflow.statePath', check=False)
    records = run(facts['root'], 'worktree', 'list', '--porcelain', '-z').stdout.decode().split('\0\0')
    roots = []
    for record in records:
        fields = record.split('\0')
        if fields and fields[0].startswith('worktree ') and 'bare' not in fields:
            roots.append(Path(fields[0][9:]).resolve())
    if pointer:
        target = common / pointer
        root = target.parent.parent.resolve()
        if target.name != 'state' or target.parent.name != '.gitflow':
            raise FlowError('state_anchor_invalid', '状态锚点不属于本仓库的已登记工作树，需先恢复或迁移锚点。')
    else:
        # separate-git-dir 的 worktree list 可能将元数据目录列作主工作树。
        # 逐项核实实际顶层目录，不能把该输出直接当项目根。
        root = Path(facts['root'])
        if Path(facts['git_dir']) != common:
            for candidate in roots:
                if candidate.is_dir() and Path(text(candidate, 'rev-parse', '--show-toplevel', check=False)).resolve() == candidate.resolve():
                    root = candidate
                    break
    if not root.is_dir():
        raise FlowError('state_anchor_missing', '共享状态所在工作树不可用，不能另建空状态。')
    actual = text(root, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if Path(actual).resolve() != common or Path(text(root, 'rev-parse', '--show-toplevel')).resolve() != root.resolve():
        raise FlowError('state_anchor_invalid', '共享状态锚点的仓库身份已变化。')
    return safe_dir(root, '.gitflow/state')


def worktree_id(facts):
    """身份基于 Git 管理目录的相对名称，仓库整体搬迁后保持稳定。"""
    relative = Path(facts['git_dir']).relative_to(Path(facts['common_dir']))
    return 'main' if str(relative) == '.' else hashlib.sha256(relative.as_posix().encode()).hexdigest()[:16]


def state_file(facts, name, reading=True):
    """新文件优先，读取兼容旧文件；写入始终指向 .gitflow/state。"""
    directory = state_dir(facts)
    target = (safe_dir(directory, 'worktrees/' + worktree_id(facts)) if name == 'journal.json' else directory) / name
    if _redirected(target):
        raise FlowError('state_symlink', '状态文件不能是符号链接。')
    if reading and not target.exists():
        base = facts['git_dir'] if name == 'journal.json' else facts['common_dir']
        legacy = safe_dir(base, 'gitflow') / name
        if legacy.exists() or _redirected(legacy):
            return legacy
    return target


def wrapper(runtime, kind):
    return '#!/bin/sh\nexec python3 ' + shlex.quote(str(runtime / 'scripts/gitflow.py')) + ' native --kind ' + kind + ' -- "$@"\n'


def migration_plan(facts, directory):
    """先验证全部旧文件和冲突；未知文件整体保留，不猜测如何合并。"""
    common = Path(facts['common_dir'])
    locations = [(common, 'main')]
    worktrees = safe_dir(common, 'worktrees')
    if worktrees.exists():
        for child in sorted(worktrees.iterdir()):
            if _redirected(child):
                raise FlowError('state_symlink', '工作树管理目录不能是符号链接。')
            if child.is_dir():
                locations.append((child, worktree_id({**facts, 'git_dir': str(child)})))
    moves, copies = [], []
    for base, identity in locations:
        old = safe_dir(base, 'gitflow')
        if not old.exists():
            continue
        if not old.is_dir():
            raise FlowError('state_file_invalid', '旧状态目录不是目录。')
        for item in old.rglob('*'):
            if _redirected(item) or not (item.is_file() or item.is_dir()):
                raise FlowError('state_symlink', '旧状态含链接或非普通文件，拒绝自动迁移。')
        backup = safe_dir(directory, 'legacy/' + identity)
        if backup.exists():
            raise FlowError('state_migration_conflict', '旧状态备份已存在，请核验未完成的迁移。')
        for name in ('activation.json', 'origins.json', 'journal.json'):
            source = old / name
            if not source.exists() or (identity != 'main' and name != 'journal.json'):
                continue
            target = (safe_dir(directory, 'worktrees/' + identity) if name == 'journal.json' else directory) / name
            data = read_json(source)
            if target.exists() or _redirected(target):
                if read_json(target) != data:
                    raise FlowError('state_migration_conflict', '新旧状态不一致，保留双方数据，需复核后迁移。')
            copies.append((target, data))
        moves.append((old, backup))
    hooks = []
    old_runtime = safe_dir(common, 'gitflow/native-runtime')
    if old_runtime.exists():
        if (directory / 'native-runtime').exists():
            raise FlowError('state_migration_conflict', '新旧原生运行时同时存在，请先复核。')
        for kind in ('commit-msg', 'pre-push'):
            hook = safe_dir(common, 'hooks') / kind
            if _redirected(hook):
                raise FlowError('hooks_existing', '原生 Hook 是链接，不能自动迁移。')
            if hook.exists():
                if hook.read_text() != wrapper(old_runtime, kind):
                    raise FlowError('hooks_existing', '旧原生 Hook 已被编辑；保留文件，需先由现有管理器迁移。')
                hooks.append((hook, kind))
    return moves, copies, hooks


def prepare(facts, directory, plan):
    """锁内执行迁移；仅由显式 apply 调用。"""
    moves, copies, hooks = plan
    common = Path(facts['common_dir'])
    exclude = safe_dir(common, 'info') / 'exclude'
    if _redirected(exclude):
        raise FlowError('state_symlink', 'Git exclude 是链接，不能自动追加状态排除。')
    content = exclude.read_text() if exclude.exists() else ''
    if '/.gitflow/state/' not in content.splitlines():
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open('a') as stream:
            stream.write(('\n' if content and not content.endswith('\n') else '') + '/.gitflow/state/\n')
    run(facts['root'], 'config', '--local', 'gitflow.statePath', os.path.relpath(directory, common))
    for target, data in copies:
        atomic_json(target, data)
    if hooks:
        runtime = directory / 'native-runtime'
        shutil.copytree(Path(__file__).resolve().parents[1], runtime / 'scripts', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for hook, kind in hooks:
            # 保留可执行权限；只替换已通过逐字核验的本插件入口。
            hook.write_text(wrapper(runtime, kind))
    for old, backup in moves:
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old), str(backup))

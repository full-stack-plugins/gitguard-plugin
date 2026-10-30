"""只读解释有效规则与实际可观察的接线状态。"""
import os
from pathlib import Path
import re
import stat
from .git import FlowError, VERSION, discover, reason, report, require_repo, run
from .layout import state_dir, wrapper
from .policy import load
from .rules import CATALOG
from .storage import safe_dir, _redirected


def describe(path):
    facts = require_repo(path)
    policy, active = load(facts)
    entries = {}
    for ident, item in CATALOG.items():
        config = policy.get('rules', {}).get(ident, {'severity': 'off'})
        source = 'default'
        if ident in policy.get('rules', {}):
            source = 'xml'
        entries[ident] = {'name': item['name'], 'scope': item['scope'], 'severity': config['severity'],
                          'options': {**item['defaults'], **config.get('options', {})}, 'source': source}
    return report('policy.describe', revision=policy['revision'], policy_sha256=active['sha256'],
                  mode=active['mode'], organization=policy.get('extends'), rules=entries,
                  workflow_guards='branch role, creation base, merge direction and repository identity remain enforced')


def _snapshot(directory):
    """Bounded byte comparison of runtime scripts; never accept redirected paths."""
    directory=Path(directory)
    for parent in (*reversed(directory.parents), directory):
        if _redirected(parent):
            raise FlowError('native_runtime_unverified','Runtime path contains a redirected directory.')
    output={}; total=0; visited=0; pending=[directory]
    while pending:
        current=pending.pop()
        if _redirected(current) or not current.is_dir():
            raise FlowError('native_runtime_unverified','Runtime directory is missing or redirected.')
        for file in current.iterdir():
            visited+=1
            if visited>512:
                raise FlowError('native_runtime_budget','Runtime file count exceeds inspection budget.')
            if _redirected(file):
                raise FlowError('native_runtime_unverified','Runtime contains a redirected path.')
            if file.name=='__pycache__' or file.suffix=='.pyc':
                continue
            info=file.lstat()
            if stat.S_ISDIR(info.st_mode):
                pending.append(file); continue
            if not stat.S_ISREG(info.st_mode) or info.st_size>256*1024 or len(output)>=256:
                raise FlowError('native_runtime_budget','Runtime contains unsupported or oversized files.')
            descriptor=os.open(file,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
            with os.fdopen(descriptor,'rb') as stream:
                opened=os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode) or (opened.st_dev,opened.st_ino)!=(info.st_dev,info.st_ino):
                    raise FlowError('native_runtime_unverified','Runtime file changed while reading.')
                data=stream.read(256*1024+1)
            total+=len(data)
            if len(data)>256*1024 or total>8*1024*1024:
                raise FlowError('native_runtime_budget','Runtime content exceeds inspection budget.')
            output[file.relative_to(directory).as_posix()]=data
    return output


def doctor(path):
    facts = discover(path)
    if facts['git_state'] == 'absent':
        return report('doctor', git_state='absent', automatic_activation=False,
                      next_actions=[{'action': 'init', 'message': '仅显式接入才初始化 Git。'}])
    problems = []
    try:
        policy = describe(path)
    except FlowError as exc:
        policy = {'status': 'unverified', 'code': exc.code}
        problems.append(reason(exc.code, exc.message))
    override = run(facts['root'], 'config', '--get', 'core.hooksPath', check=False).returncode==0
    runtime = state_dir(facts) / 'native-runtime'
    hook_dir = safe_dir(facts['common_dir'], 'hooks')
    observed = {}
    for kind in ('commit-msg', 'pre-push'):
        file = hook_dir / kind
        if override:
            observed[kind] = 'external_manager'
        elif _redirected(file):
            observed[kind] = 'unverified'
        elif not file.exists():
            observed[kind] = 'missing'
        elif not file.is_file() or file.stat().st_size > 8192 or (os.name!='nt' and not os.access(file,os.X_OK)) or file.read_text() != wrapper(runtime, kind):
            observed[kind] = 'unverified'
        else:
            observed[kind] = 'configured'
    runtime_version = None
    runtime_status='unverified'
    try:
        expected=_snapshot(Path(__file__).resolve().parents[1])
        actual=_snapshot(runtime/'scripts')
        version_data=actual.get('gitflow/git.py',b'').decode('utf-8')
        match=re.search(r"^VERSION = ['\"]([^'\"]+)['\"]",version_data,re.M)
        runtime_version=match[1] if match else None
        runtime_status='current' if actual==expected and runtime_version==VERSION else 'outdated'
    except (FlowError,OSError,UnicodeError):
        runtime_status='unverified'
    status = 'configured' if all(v == 'configured' for v in observed.values()) else ('missing' if all(v == 'missing' for v in observed.values()) else 'unverified')
    if status=='configured' and runtime_status!='current':
        status=runtime_status
    workflows = safe_dir(facts['root'], '.github/workflows')
    candidates = []
    if workflows.is_dir():
        for file in sorted(workflows.iterdir()):
            if file.suffix in ('.yml', '.yaml') and not file.is_symlink() and file.is_file() and file.stat().st_size < 65536 and 'full-stack-plugins/gitflow-plugin' in file.read_text():
                candidates.append(file.name)
    integrations = {'native_hooks': {'status': status, 'entries': observed, 'runtime_version': runtime_version, 'runtime_status': runtime_status},
                    'ci': {'status': 'unconfigured', 'files': candidates, 'reason':'trusted XML distribution not configured'},
                    'host_mcp': {'status': 'unverified'}, 'server_protection': {'status': 'unverified'}}
    return report('doctor', 'unverified' if problems or status != 'configured' else 'allow', problems, policy=policy, integrations=integrations,
                  next_actions=[{'action': 'integration.review', 'message': 'missing 时使用 hooks 预览并显式安装；已有管理器或旧运行时须审查接线。CI 需先配置独立可信 XML 分发，required check 由管理员配置；宿主须实际调用验证。'}])

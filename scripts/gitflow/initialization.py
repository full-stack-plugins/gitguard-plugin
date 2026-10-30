"""Explicit XML initialization and recoverable managed guidance updates."""
import os
from pathlib import Path
import stat
import tempfile
from .git import FlowError, discover, report, require_repo, run
from .storage import _redirected, locked, safe_dir

START = '<!-- GITGUARD_START -->'
END = '<!-- GITGUARD_END -->'
BLOCK = (START + '\n## GitGuard\n\n'
         'GitGuard checks branch governance using the single authoritative '
         '`gitflow.xml` in `git rev-parse --git-common-dir`. Do not duplicate its rules here.\n'
         'Before Git writes, use the supported Agent pre-execution check; obey deny or unverified results. '
         'Use ordinary Git commands, not GitGuard operation wrappers. '
         'Run `gitguard doctor` to verify native commit-msg/pre-push wiring. '
         'This guidance is not enforcement; native hooks do not cover every local merge.\n'
         'A new clone requires explicit GitGuard initialization; never guess a missing policy.\n' + END + '\n').encode()


def guidance_snapshot(path):
    if _redirected(path):
        raise FlowError('agents_unsafe', 'AGENTS.md 不能是链接或重解析点。')
    try:
        info=path.lstat()
    except FileNotFoundError:
        return None, b''
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 256*1024:
        raise FlowError('agents_unsafe', 'AGENTS.md 必须是有界单链接普通文件。')
    with path.open('rb') as stream:
        opened=os.fstat(stream.fileno())
        if (opened.st_dev,opened.st_ino)!=(info.st_dev,info.st_ino):
            raise FlowError('agents_changed','AGENTS.md 身份变化。')
        raw=stream.read(256*1024+1)
    if len(raw)>256*1024:
        raise FlowError('agents_unsafe','AGENTS.md 超过预算。')
    try: raw.decode('utf-8')
    except UnicodeError as exc: raise FlowError('agents_encoding','AGENTS.md 需要 UTF-8。') from exc
    return (info.st_dev,info.st_ino,info.st_mode),raw


def guidance_content(raw):
    start,end=START.encode(),END.encode()
    if raw.count(start)!=raw.count(end) or raw.count(start)>1:
        raise FlowError('agents_markers_invalid','GitGuard 标记缺失或重复，保留用户文件。')
    if start in raw:
        a,b=raw.index(start),raw.index(end)
        if b<a: raise FlowError('agents_markers_invalid','GitGuard 标记顺序错误。')
        b+=len(end)
        # Replace only the marker span; keep all outside bytes, including its newline.
        result=raw[:a]+BLOCK.rstrip(b'\n')+raw[b:]
    else:
        result=raw+(b'\n' if raw and not raw.endswith(b'\n') else b'')+BLOCK
    if len(result)>256*1024:
        raise FlowError('agents_unsafe','生成的 AGENTS.md 超过预算；未写入 XML 或引导。')
    return result


def write_guidance(path, before, data):
    if guidance_snapshot(path)!=before:
        raise FlowError('agents_changed','AGENTS.md 已变化，重新预览。')
    if data==before[1]: return
    fd,name=tempfile.mkstemp(prefix='.gitguard-agents-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        if before[0]: os.chmod(name,stat.S_IMODE(before[0][2]))
        if guidance_snapshot(path)!=before:
            raise FlowError('agents_changed','AGENTS.md 写入前变化，保留原文件。')
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def initialize(path, profile=None, mode='shared', apply=False, initialize_git=False):
    from .policy import template, load
    from .xml_policy import policy_path, write_policy
    facts=discover(path)
    if mode not in ('shared','local'): raise FlowError('mode_invalid','未知兼容模式。')
    absent=facts['git_state']=='absent'
    if absent and not initialize_git:
        raise FlowError('git_initialization_required','需要显式 initialize-git，不能猜测初始化仓库。')
    root=Path(facts['root'] if not absent else path).resolve()
    agents=safe_dir(root,'AGENTS.md');before=guidance_snapshot(agents);content=guidance_content(before[1])
    if not absent and policy_path(facts).exists():
        policy,_=load(facts)
        if profile and profile!=policy['profile']:
            raise FlowError('policy_already_exists','已有 XML 不由 init 替换。')
    else:
        if not profile: raise FlowError('profile_selection_required','请选择八种工作流之一；非交互必须指定 --profile。')
        policy=template(profile)
        if not absent:
            from .policy import activation_path
            if activation_path(facts).exists() or (root/'.gitflow/workflow.json').exists():
                raise FlowError('legacy_migration_required','发现旧 JSON；请显式 policy --operation migrate，不覆盖原规则。')
    result=report('init','applied' if apply else 'preview',profile=policy['profile'],mode='xml',
                  policy_location='git-common-dir/gitflow.xml',guidance='AGENTS.md',
                  automatic_enforcement=False,missing_required_roles=[k for k,r in policy['roles'].items() if r['required'] and r['name'] not in facts.get('branches',[])],next_actions=[{'action':'audit','message':'检查分支与实际接线。'},{'action':'hooks','message':'预览并显式安装 Git 原生 hooks；已有管理器需核验接线。'}])
    if not apply:return result
    if absent:
        run(path,'init','-b','main');facts=require_repo(path)
    with locked(facts):
        # Recheck both identities before the first write. XML is authoritative even
        # if the second write fails; a repeated init repairs guidance, not policy.
        if guidance_snapshot(agents)!=before:raise FlowError('agents_changed','AGENTS.md 发生变化。')
        if policy_path(facts).exists():
            current,_=load(facts)
            if current!=policy:raise FlowError('policy_changed','XML 发生变化。')
        else:write_policy(facts,policy)
        try:write_guidance(agents,before,content)
        except (OSError,FlowError) as exc:
            raise FlowError('init_partial','XML 已保留，AGENTS 引导未完成；修复文件问题后重复 init，不覆盖 XML。') from exc
    return result

"""Claude-shape Hooks 与保守 shell 命令语义；不执行传入命令。"""
import json
import re
from pathlib import Path
import shlex
import shutil
import sys
from .context import context
from .git import FlowError, is_git_project, reason, report, require_repo, text, run
from .operations import sync
from .policy import load, role_for
from .service import gate, metadata_checks
from . import rules
from .layout import state_dir, state_file
from .storage import locked, read_json, safe_dir

READ={'status','diff','log','show','rev-parse','rev-list','for-each-ref','ls-files','ls-remote','merge-base','check-ref-format','remote','worktree','config','tag','branch'}


def original_oid(path, ref='HEAD'):
    result=run(path,'--no-replace-objects','rev-parse','--verify',ref+'^{commit}',check=False)
    return result.stdout.decode().strip() if result.returncode==0 else None


def decision(value,message):
    return {'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':value,'permissionDecisionReason':message}}


def git_target(path,args):
    """解析静态 -C 目标；路径只用于检测，不执行输入命令。"""
    while args and args[0].startswith('-C'):
        if args[0]=='-C':
            if len(args)<2:raise FlowError('command_unknown','git -C 缺少目录。')
            directory=args[1];args=args[2:]
        else:
            directory=args[0][2:];args=args[1:]
        path=str((Path(path)/directory).resolve())
    return path,args


def inspect_git(path,args):
    path,args=git_target(path,args)
    if not is_git_project(path):return None
    if not args:return None
    if args[0].startswith('-'):raise FlowError('command_unknown','Git 全局选项/配置需要单独复核。')
    verb,*rest=args
    if rest and rest[0] in ('--help','-h'):return report('hook.read')
    if any(x in rest for x in ('--force','-f','--force-with-lease','--mirror','--delete')) and verb in ('push','switch','checkout','branch'):
        raise FlowError('unsafe_git_option','强制、镜像、删除或覆盖操作未建模。','deny')
    if verb in ('config','remote','worktree','tag','branch'):
        if not rest or verb=='branch' and all(x in ('-a','-r','--list','-v','-vv','--show-current') or x.startswith('--format=') for x in rest):return report('hook.read')
        raise FlowError('command_unknown','此 Git 管理命令请使用插件预览并显式确认。')
    if verb in READ:return report('hook.read')
    if verb in ('add','restore','reset','clean','checkout','cherry-pick','revert','stash','init'):
        raise FlowError('command_unknown','此动作涉及修改或恢复，需明确范围和授权。')
    if verb=='commit':
        messages=[];i=0
        while i<len(rest):
            arg=rest[i]
            if arg=='-m' or arg=='--message':
                if i+1>=len(rest):raise FlowError('command_unknown','提交消息缺失。')
                messages.append(rest[i+1]);i+=2
            elif arg.startswith('--message='):messages.append(arg.split('=',1)[1]);i+=1
            elif arg in ('-a','--all','--allow-empty','--quiet','-q'):i+=1
            else:raise FlowError('command_unknown','提交中的文件/复用/重写/配置选项需要明确审查。')
        return gate(path,'commit',message='\n\n'.join(messages) if messages else None)
    if verb in ('merge','rebase'):
        if len(rest)!=1 or rest[0].startswith('-'):raise FlowError('command_unknown','集成命令需唯一明确本地分支；恢复请使用 recovery。')
        if verb=='merge':
            facts=require_repo(path)
            source=rest[0]
            if not source.startswith('refs/heads/') and original_oid(path,'refs/tags/'+source):
                raise FlowError('branch_identity_ambiguous','同名标签与分支不明确，请使用 refs/heads/。')
            if source.startswith('refs/heads/'):
                source=source[11:]
            declared='refs/heads/'+source
            resolved=run(path,'rev-parse','--symbolic-full-name','--verify',rest[0],check=False)
            actual=original_oid(path,rest[0])
            if (resolved.returncode or resolved.stderr or resolved.stdout.decode().strip()!=declared
                    or actual is None or actual!=original_oid(path,declared)):
                raise FlowError('branch_identity_ambiguous','Git merge 参数未唯一解析为声明的本地源分支。')
            return gate(path,'merge',source=source,target=facts['branch'])
        result=sync(path,verb,target=rest[0])
        raise FlowError('native_semantics_unverified','原生 merge/rebase 的目标与配置未绑定插件 argv；使用 sync。')
    if verb in ('push','pull','fetch'):
        if verb=='fetch' and len(rest)==1:
            sync(path,verb,remote=rest[0])
            raise FlowError('native_semantics_unverified','原生 fetch 的 tag/ref 配置未绑定，使用插件 sync。')
        if len(rest)!=2 or any(x.startswith('-') for x in rest):raise FlowError('command_unknown','远端命令必须明确单远端、单同名分支。')
        remote,ref=rest
        if ':' in ref or ref.startswith('+'):raise FlowError('remote_mapping_unknown','原生命令不接受任意 refspec，请使用 sync。','deny')
        result=sync(path,verb,target=ref,remote=remote)
        if verb=='pull':raise FlowError('native_semantics_unverified','原生 pull 可受 rebase 配置影响，使用插件的 ff-only 同步。')
        return result
    raise FlowError('command_unknown','Git 子命令未建模，不能报告已验证。')


def pretool(payload):
    path=payload.get('cwd')
    if not isinstance(path,str) or not path.strip():return {}
    inp=payload.get('tool_input',{})
    command=inp.get('command',inp.get('cmd')) if isinstance(inp,dict) else None
    if not isinstance(command,str):return {}
    active=False;managed=False
    try:
        active=is_git_project(path)
        if len(command)>16384:return decision('ask','命令超过语义检查预算。') if active else {}
        if ('\n' in command or '\r' in command) and re.search(r'\bgit\b', command):
            return decision('ask','多行 shell 命令必须拆分，不能把换行当普通 argv 空白。') if active else {}
        if re.search(r'\bgit\b', command) and ('$(' in command or '`' in command):
            if active:raise FlowError('command_dynamic', 'Git 出现在动态命令替换中，必须拆分验证。')
            return {}
        lexer=shlex.shlex(command,posix=True,punctuation_chars=';&|<>')
        lexer.whitespace_split=True;tokens=list(lexer)
        chunks=[[]]
        for token in tokens:
            if token=='&&':chunks.append([])
            elif token in (';','|','||','&','>','<','>>','<<'):
                if 'git' in tokens and active:return decision('ask','复合 shell 控制或重定向需独立 Git 操作预览。')
                return {}
            else:chunks[-1].append(token)
        mutation_seen=False
        for chunk in chunks:
            if not chunk:continue
            if chunk[0]=='cd' and len(chunk)==2:
                if any(x in chunk[1] for x in ('$','`','~')):
                    if active:raise FlowError('command_dynamic','动态 cwd 无法验证。')
                    return {}
                path=str((Path(path)/chunk[1]).resolve())
                active=is_git_project(path)
                continue
            if Path(chunk[0]).name=='git':
                chunk[0]='git'
            if chunk[0]!='git':
                if active and any(x=='git' for x in chunk[1:]) and chunk[0]!='echo':raise FlowError('command_wrapper','Git 包装器需独立审查。')
                continue
            if any('$' in x or '`' in x or '\n' in x for x in chunk):
                if active:raise FlowError('command_dynamic','动态命令或替换无法静态验证。')
                return {}
            target,args=git_target(path,chunk[1:])
            if not is_git_project(target):continue
            managed=True
            if mutation_seen:raise FlowError('command_future_state','链中先前变更会改变后续 Git 身份，请拆分操作。')
            result=inspect_git(target,args)
            if result and result['decision']!='allow':return decision('deny' if result['decision']=='deny' else 'ask',result['reasons'][0]['message'])
            mutation_seen=bool(result and (result['action'].startswith(('gate.','sync.'))))
        return decision('allow','已按当前项目分支规范检查；此结果不包含代码质量或用户写操作授权。') if managed else {}
    except (FlowError,ValueError) as exc:
        if not active and not managed and not (isinstance(exc,FlowError) and exc.code=='repository_unreadable'):return {}
        return decision('deny' if isinstance(exc,FlowError) and exc.decision=='deny' else 'ask',str(exc))


def hook_main(event):
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise FlowError('hook_budget','Hook 输入超过预算。')
        payload=json.loads(raw or b'{}')
        if not isinstance(payload,dict):raise FlowError('hook_input','Hook 输入必须是对象。')
        if event=='PreToolUse':result=pretool(payload)
        elif event in ('SessionStart','UserPromptSubmit','PostToolUse','Stop'):
            path=payload.get('cwd')
            result={}
            if isinstance(path,str) and path.strip() and is_git_project(path):
                r=context(path)
                if r['facts']['git_state']!='absent':
                    result={'hookSpecificOutput':{'hookEventName':event,'additionalContext':r['context']}}
                    if event=='Stop':result={'systemMessage':r['context']}
        else:raise FlowError('hook_event_unknown','未知 Hook 事件。')
    except (FlowError,ValueError,OSError) as exc:
        result=decision('ask',f'GitFlow 未验证：{exc}') if event=='PreToolUse' else {'systemMessage':'GitFlow 上下文未验证；请运行 discover。'}
    print(json.dumps(result,ensure_ascii=False))
    return 0


def install_native(path,apply=False):
    facts=require_repo(path);load(facts)
    if run(path,'config','--get','core.hooksPath',check=False).returncode==0:raise FlowError('hooks_path_existing','已有 core.hooksPath，需由现有 Hook 管理器集成，不能改写。')
    hooks=safe_dir(facts['common_dir'],'hooks')
    if any((hooks/name).exists() or (hooks/name).is_symlink() for name in ('commit-msg','pre-push')):
        raise FlowError('hooks_existing','已有 Hook，保留原文件；请审查后在现有管理器内调用 native 入口。')
    result=report('hooks.install','applied' if apply else 'preview',hooks=['commit-msg','pre-push'])
    if apply:
        with locked(facts):
            root=Path(__file__).resolve().parents[2]
            runtime=safe_dir(state_dir(facts), 'native-runtime')
            if runtime.exists():raise FlowError('native_runtime_existing','已有运行时，不自动覆盖。')
            runtime.mkdir(parents=True)
            shutil.copytree(root/'scripts',runtime/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
            hooks.mkdir(exist_ok=True)
            for kind in ('commit-msg','pre-push'):
                file=hooks/kind
                content='#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(runtime/'scripts/gitflow.py'))+' native --kind '+kind+' -- "$@"\n'
                with file.open('x') as stream:stream.write(content)
                file.chmod(0o755)
    return result


def managed_integration(facts):
    """集成提交只接受当前工作树日志绑定的源/目标/OID与生效修订。"""
    policy, active = load(facts)
    file = state_file(facts, 'journal.json')
    journal = read_json(file)
    entries = journal.get('entries', [])
    if not entries or entries[-1].get('status') != 'running':
        raise FlowError('integration_unbound', '集成提交未绑定受管日志，请使用显式 sync/recovery。')
    entry = entries[-1]
    steps = entry.get('steps', [])
    if not steps or steps[-1].get('status') != 'running' or entry.get('policy_sha256') != active['sha256']:
        raise FlowError('integration_unbound', '集成步骤或规则修订不一致。')
    step = steps[-1]
    if step['before'].get('branch') != facts['branch']:
        raise FlowError('integration_identity_changed', '集成目标工作树身份不一致。')
    args = step.get('argv', [])
    if 'MERGE_HEAD' in facts['operation_states'] and args and args[0] == 'merge':
        heads = Path(facts['git_dir'], 'MERGE_HEAD').read_text().splitlines()
        source = step.get('source_branch')
        target = facts['branch']
        sr, tr = role_for(policy, source), role_for(policy, target)
        if heads != [step.get('source_oid')] or original_oid(facts['root'], 'ORIG_HEAD') != step['before']['head']:
            raise FlowError('integration_identity_changed', '真实合并父提交与日志不同。')
        planned_targets=[c[1] for c in entry.get('commands',[]) if isinstance(c,list) and len(c)==2 and c[0]=='switch']
        integration_action=step.get('integration_action',entry['action'])
        classic_backfill=(policy['profile']=='classic-gitflow' and sr=='hotfix' and tr=='release'
                          and integration_action=='release.finish'
                          and (target in planned_targets or entry['action']=='recovery.continue'))
        if not sr or (tr not in policy['roles'][sr]['merge_into'] and not classic_backfill):
            raise FlowError('integration_direction_denied', '合并提交方向不符合项目规则。')
        return report('native.integration')
    if 'CHERRY_PICK_HEAD' in facts['operation_states'] and args and args[0] == 'cherry-pick':
        if original_oid(facts['root'], 'CHERRY_PICK_HEAD') != (step.get('source_oid') if args[-1] == '--continue' else args[-1]):
            raise FlowError('integration_identity_changed', 'cherry-pick 源 OID 与日志不同。')
        target_role = role_for(policy, facts['branch'])
        source_role = role_for(policy, step.get('integration_source', entry['before'].get('branch')))
        integration_action = step.get('integration_action', entry['action'])
        if integration_action == 'recovery.backport':
            if not source_role or target_role not in policy['roles'][source_role]['merge_into']:
                raise FlowError('integration_direction_denied', '回灌方向不符合工作流。')
        elif integration_action != 'recovery.move-commit' or not target_role or not policy['roles'][target_role]['allow_commit']:
            raise FlowError('integration_unbound', '迁移提交目标未获项目规则允许。')
        return report('native.integration')
    raise FlowError('integration_unbound', '中断提交未绑定明确集成步骤。')


def integration(facts):
    """Keep journal-bound exceptions; otherwise prove a single native merge source."""
    journal_file = state_file(facts, 'journal.json')
    if journal_file.exists():
        journal = read_json(journal_file)
        entries = journal.get('entries', [])
        if not isinstance(entries,list) or any(not isinstance(entry,dict) for entry in entries):
            raise FlowError('integration_unverified','Managed integration journal is malformed.')
        if entries and entries[-1].get('status') == 'running':
            return managed_integration(facts)
        if entries and entries[-1].get('status') != 'complete':
            raise FlowError('integration_unverified','Managed integration requires explicit recovery.')
    if facts['operation_states'] != ['MERGE_HEAD']:
        raise FlowError('integration_unverified', 'Only a single native merge can be verified without a managed journal.')
    heads = Path(facts['git_dir'], 'MERGE_HEAD').read_text().splitlines()
    if len(heads) != 1 or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', heads[0]):
        raise FlowError('integration_unverified', 'Native merge source is not a single commit.')
    rows = text(facts['root'], 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads').splitlines()
    sources = [row.split()[0][11:] for row in rows if len(row.split()) == 2 and row.split()[1] == heads[0]]
    if len(sources) != 1 or not facts['branch']:
        raise FlowError('integration_unverified', 'Native merge source branch is ambiguous or missing.')
    policy, _ = load(facts)
    sr, tr = role_for(policy, sources[0]), role_for(policy, facts['branch'])
    if not sr or not tr or tr not in policy['roles'][sr]['merge_into']:
        raise FlowError('integration_direction_denied', 'Native merge direction violates policy.', 'deny')
    return report('native.integration')


def push_metadata(facts, policy, local_oid, remote_oid):
    """Inspect every pending commit, using only locally available immutable objects."""
    if facts['shallow']:
        raise FlowError('push_history_unverified', 'Shallow history cannot prove the full pending range.')
    revision = local_oid if set(remote_oid) == {'0'} else remote_oid + '..' + local_oid
    commits = text(facts['root'], '--no-replace-objects', 'rev-list', '--max-count=257', revision).splitlines()
    if len(commits) > 256:
        raise FlowError('push_budget', 'Pending commit range exceeds 256 commits.')
    checks, reasons = [], []
    for commit in commits:
        raw = run(facts['root'], '--no-replace-objects', 'show', '-s', '--format=%an%x00%ae%x00%B', commit).stdout.decode('utf-8')
        name, email, message = raw.split('\0', 2)
        message = message.rstrip('\n')
        if len(message) > 4096 or len(name) > 4096 or len(email) > 4096:
            raise FlowError('push_metadata_budget', 'Commit metadata exceeds inspection budget.')
        pattern = policy['commit_message_pattern']
        if pattern and not re.fullmatch(pattern, message):
            reasons.append(reason('commit_message_invalid', 'Pending commit message violates policy.', commit=commit))
        checks.extend(rules.evaluate(policy, {'message': message, 'author_name': name, 'author_email': email}))
    reasons.extend(rules.reasons(checks))
    verdict = 'unverified' if rules.decision(checks) == 'unverified' else ('deny' if reasons else 'allow')
    return report('native.push', verdict, reasons, checks=checks)


def native_main(kind,args):
    try:
        if kind=='commit-msg':
            if len(args)!=1:raise FlowError('message_file_required','commit-msg 需要 Git 提供的消息文件。')
            file=Path(args[0])
            if file.is_symlink() or file.stat().st_size>4096:raise FlowError('message_file_invalid','提交消息文件超过预算或为链接。')
            facts=require_repo('.')
            message = file.read_text().strip()
            if facts['operation_states']:
                r = integration(facts)
                policy, active = load(facts)
                checks = metadata_checks(facts, policy, message)
                reasons = rules.reasons(checks)
                pattern = policy['commit_message_pattern']
                if pattern and not re.fullmatch(pattern, message):
                    reasons.append(reason('commit_message_invalid', 'Integration commit message violates policy.'))
                verdict = 'unverified' if rules.decision(checks) == 'unverified' else ('deny' if reasons else 'allow')
                r = report('native.integration', verdict, reasons, checks=checks, policy_sha256=active['sha256'])
            else:
                r = gate('.', 'commit', message=message)
            for item in r.get('checks', []):
                if item['severity'] == 'warn' and item['status'] == 'fail':
                    print('GitFlow warning: ' + item['message'], file=sys.stderr)
        elif kind=='pre-push':
            if len(args)!=2:raise FlowError('remote_required','pre-push 需要远端身份。')
            facts=require_repo('.');policy,_=load(facts)
            if args[0]!=policy['primary_remote']:raise FlowError('remote_mapping_denied','native pre-push 仅支持权威远端。')
            raw=sys.stdin.buffer.read(16385)
            if len(raw)>16384:raise FlowError('push_budget','推送引用超过预算。')
            lines=raw.decode().splitlines()
            if len(lines)!=1:raise FlowError('push_refs_unknown','native 只验证单一分支推送。')
            parts=lines[0].split()
            if len(parts)!=4 or not parts[0].startswith('refs/heads/') or not parts[2].startswith('refs/heads/') or set(parts[1])=={'0'}:
                raise FlowError('push_ref_invalid','不支持标签、删除或非分支来源。')
            if any(not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', value) for value in (parts[1],parts[3])) or len(parts[1])!=len(parts[3]):
                raise FlowError('push_oid_invalid','Push OIDs must be full, matching object identifiers.')
            source,target=parts[0][11:],parts[2][11:]
            if original_oid('.',parts[0]) != parts[1]:raise FlowError('push_identity_changed','推送源提交与实际引用不一致。')
            if set(parts[3]) != {'0'}:
                if original_oid('.',parts[3]) != parts[3]:raise FlowError('remote_history_unknown','远端提交对象不可核验，不能放行非快进未知历史。')
                ancestry=run('.', '--no-replace-objects', 'merge-base', '--is-ancestor', parts[3], parts[1], check=False)
                if ancestry.returncode==1:raise FlowError('non_fast_forward_denied','拒绝会重写远端分支历史的推送。','deny')
                if ancestry.returncode:raise FlowError('remote_history_unknown','Original-object ancestry could not be verified.')
            r=gate('.','push',source=source,target=target)
            if r['decision']=='allow':
                r=push_metadata(facts,policy,parts[1],parts[3])
        else:raise FlowError('native_kind_unknown','未知 native Hook。')
        if r['decision']!='allow':print('GitFlow '+r['decision']+': '+r['reasons'][0]['message'],file=sys.stderr);return 1
        return 0
    except (FlowError,OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        print('GitFlow '+(exc.decision if isinstance(exc,FlowError) else 'unverified')+': '+str(exc),file=sys.stderr);return 1

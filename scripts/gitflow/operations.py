"""显式变更、逐步日志与可恢复的 Git 操作。"""
import re
import uuid
from pathlib import Path
from .git import FlowError, discover, oid, reason, report, require_repo, run, text, valid_branch
from .policy import load, role_for
from .service import gate
from .provenance import read_origins
from .layout import state_file
from .storage import atomic_json, locked, read_json, safe_dir


def deny(code, message):
    raise FlowError(code, message, 'deny')


def clean(facts):
    if facts['dirty'] or facts['operation_states'] or not facts['head'] or not facts['branch']:
        raise FlowError('clean_branch_required', '需要有初始提交、无修改、无中断操作的工作分支。')


def local(path, name):
    if not valid_branch(path, name) or oid(path, 'refs/heads/' + name) is None:
        raise FlowError('local_branch_required', '需要存在且名称有效的本地分支。')
    return oid(path, 'refs/heads/' + name)


def available(path, name, root):
    # 不切换/重命名其他工作树已经检出的分支。
    worktree = None
    for line in text(path, 'worktree', 'list', '--porcelain').splitlines():
        if line.startswith('worktree '):
            worktree = line[9:]
        elif line == 'branch refs/heads/' + name and (worktree is None or Path(worktree).resolve() != Path(root).resolve()):
            raise FlowError('branch_worktree_occupied', '此分支已在另一工作树检出。')


def ancestor(path, source, target):
    p = run(path, 'merge-base', '--is-ancestor', source, target, check=False)
    if p.returncode not in (0, 1):
        raise FlowError('history_unverified', '无法可靠检查祖先关系。')
    return p.returncode == 0


def checked_gate(path, action, source, target):
    r = gate(path, action, source, target)
    if r['decision'] != 'allow':
        first = r['reasons'][0]
        deny(first['code'], first['message'])


def origins(facts):
    return read_origins(facts)


def execute(facts, action, commands, apply=False, update=None):
    result = report(action, 'applied' if apply else 'preview', commands=commands,
                    before={k:facts[k] for k in ('branch','head','ref_oids','operation_states')})
    if not apply:
        return result
    with locked(facts):
        now = require_repo(facts['root'])
        if any(now[k] != facts[k] for k in ('branch','head','branches','ref_oids','dirty','operation_states')):
            raise FlowError('repository_changed', '仓库身份发生变化，需重新预览。')
        _, active = load(now)  # 候选漂移再次检查，不能在等待锁期间换约定。
        if facts.get('policy_sha256') != active['sha256']:
            raise FlowError('policy_changed', '规划时的生效修订已变化，请重新预览。')
        journal_file = state_file(facts, 'journal.json')
        journal = read_json(journal_file) if journal_file.exists() else {'schema_version':'1.0.0','entries':[]}
        if not isinstance(journal, dict) or journal.get('schema_version') != '1.0.0' or not isinstance(journal.get('entries'), list) or any(not isinstance(e,dict) or e.get('status') not in ('running','unknown','incomplete','complete') or not isinstance(e.get('steps'),list) for e in journal.get('entries',[])):
            raise FlowError('journal_invalid', '操作日志结构损坏，先恢复可信记录。')
        if not action.startswith('recovery.') and any(e.get('status') in ('running','unknown') for e in journal['entries']):
            raise FlowError('operation_unknown', '先前操作未确定完成，先读取 recovery diagnose/resume 并复核实际引用。')
        if len(journal['entries']) >= 512:
            raise FlowError('journal_limit', '操作日志达到预算；保留审计记录后再接入。')
        entry = {'id': str(uuid.uuid4()), 'action':action, 'status':'running',
                 'before':result['before'], 'steps':[], 'commands':commands, 'policy_sha256':active['sha256']}
        journal['entries'].append(entry)
        atomic_json(journal_file, journal)
        result['operation_id'] = entry['id']
        try:
            for command in commands:
                step = {'argv': command, 'status':'running', 'before':discover(facts['root'])}
                if command[0] in ('merge','cherry-pick') and command[-1] == '--continue':
                    marker = 'MERGE_HEAD' if command[0] == 'merge' else 'CHERRY_PICK_HEAD'
                    actual = oid(facts['root'], marker)
                    for previous in reversed(journal['entries'][:-1]):
                        for original_step in reversed(previous.get('steps', [])):
                            original_args = original_step.get('argv', [])
                            original_oid = original_step.get('source_oid') if command[0] == 'merge' else (original_args[-1] if original_args else None)
                            if original_args and original_args[0] == command[0] and original_oid == actual and previous.get('policy_sha256') == active['sha256']:
                                step['source_branch'] = original_step.get('source_branch')
                                step['source_oid'] = actual
                                step['integration_action'] = previous['action']
                                step['integration_source'] = previous['before']['branch']
                                break
                        if step.get('source_oid'):break
                if command[0] == 'merge' and command[-1].startswith('refs/heads/'):
                    step['source_branch'] = command[-1][11:]
                    step['source_oid'] = oid(facts['root'], command[-1])
                entry['steps'].append(step);atomic_json(journal_file,journal)
                run(facts['root'], *command, timeout=60)
                step['status']='complete';step['after']=discover(facts['root'])
                atomic_json(journal_file,journal)
            if update:
                update()
            entry['status']='complete'
        except (FlowError, OSError) as exc:
            if not isinstance(exc, FlowError):
                exc = FlowError('journal_io_error', '操作或记录写入中断，必须复核当前状态。')
            entry['status']='unknown' if exc.code in ('git_timeout','git_cancelled','git_cleanup_failed','journal_io_error','git_output_limit') else 'incomplete'
            entry['error']=reason(exc.code,exc.message)
            result['decision']='unverified';result['reasons']=[entry['error']]
            result['next_actions']=[{'action':'recovery.diagnose','operation_id':entry['id']}]
        finally:
            try:
                entry['after']=discover(facts['root'])
            except FlowError:
                entry['after']={'observation':'unverified'};entry['status']='unknown'
                result['decision']='unverified'
            atomic_json(journal_file,journal)
        result['after']=entry['after']
    return result


def branch(path, operation, name=None, source=None, target=None, apply=False):
    facts=require_repo(path);policy,active=load(facts);facts['policy_sha256']=active['sha256']
    origin_file,origin_items=origins(facts)
    commands=[];changes={}
    if operation in ('create','reconcile'):
        clean(facts)
        if operation=='reconcile':
            missing=[(k,r) for k,r in policy['roles'].items() if r['required'] and r['name'] not in facts['branches']]
            for key,role in missing:
                bases=[policy['roles'][s]['name'] for s in role['create_from'] if policy['roles'][s]['name'] in facts['branches']]
                if len(bases)!=1:
                    raise FlowError('branch_base_required','缺失长期分支需唯一已存在来源，不能猜测。')
                commands.append(['branch',role['name'],'refs/heads/'+bases[0]])
                changes[role['name']]={'source':bases[0],'oid':local(path,bases[0]),'role':key,'policy_sha256':active['sha256']}
        else:
            if not valid_branch(path,name):deny('branch_name_invalid','Git 不接受此分支名称。')
            key=role_for(policy,name)
            if not key:deny('branch_name_unmatched','分支名不符合项目规则。')
            if name in facts['branches']:deny('branch_exists','目标分支已经存在。')
            source_oid=local(path,source);sr=role_for(policy,source)
            if sr not in policy['roles'][key]['create_from']:deny('branch_base_denied','创建来源不符合角色约定。')
            commands=[['branch',name,'refs/heads/'+source]]
            changes[name]={'source':source,'oid':source_oid,'role':key,'policy_sha256':active['sha256']}
    elif operation=='switch':
        clean(facts);local(path,name);available(path,name,facts['root'])
        if not role_for(policy,name):deny('branch_name_unmatched','目标分支不符合项目规则。')
        commands=[['switch',name]]
    elif operation=='rename':
        clean(facts);local(path,source);available(path,source,facts['root'])
        sr=role_for(policy,source);nr=role_for(policy,name)
        if not valid_branch(path,name) or not sr or nr!=sr:deny('branch_rename_denied','重命名必须保留原角色并满足 Git 名称规则。')
        if policy['roles'][sr]['name'] or name in facts['branches']:deny('protected_branch_change','不能重命名固定角色或覆盖已有分支。')
        commands=[['branch','-m',source,name]]
    elif operation=='delete':
        clean(facts);local(path,name);available(path,name,facts['root'])
        key=role_for(policy,name)
        if not key or policy['roles'][key]['name'] or name==facts['branch']:deny('protected_branch_change','不能清理固定角色或当前检出分支。')
        local(path,target);checked_gate(path,'merge',name,target)
        if facts['shallow']:raise FlowError('history_unverified','浅历史不能证明分支已完整合入。')
        if not ancestor(path,'refs/heads/'+name,'refs/heads/'+target):deny('branch_unmerged','目标尚未包含此分支，拒绝删除。')
        # 已独立检查目标祖先；-d 还要求 HEAD/upstream 合入，为避免误删拒绝不符合 Git 安全条件的场景。
        commands=[['branch','-d',name]]
    else:raise FlowError('operation_unknown','未知分支操作。')
    def update():
        file,items=origin_file,origin_items
        items.update(changes)
        if operation=='rename' and source in items:items[name]=items.pop(source)
        if operation=='delete':items.pop(name,None)
        atomic_json(file,items)
    return execute(facts,'branch.'+operation,commands,apply,update)


def merge_command(policy, source):
    method=policy['merge_method']
    if method=='squash':
        raise FlowError('squash_requires_commit','squash 需要独立提交审批，当前集成执行不自动生成 squash 提交。')
    return ['merge','--no-edit','--'+method if method in ('no-ff','ff-only') else '--ff','refs/heads/'+source]


def sync(path, operation, source=None, target=None, remote=None, apply=False):
    facts=require_repo(path);policy,active=load(facts);facts['policy_sha256']=active['sha256'];clean(facts)
    commands=[]
    if operation in ('merge','rebase'):
        if operation=='merge':
            local(path,source);target=target or facts['branch']
            if target!=facts['branch']:raise FlowError('target_not_current','合并目标必须是当前分支。')
            checked_gate(path,'merge',source,target);commands=[merge_command(policy,source)]
        else:
            source=source or facts['branch'];local(path,target)
            if source!=facts['branch']:raise FlowError('source_not_current','rebase 来源必须是当前分支。')
            checked_gate(path,'rebase',source,target)
            if text(path,'for-each-ref','--format=%(refname)','--contains','HEAD','refs/remotes'):
                deny('published_rebase_denied','已有远端引用包含此提交，拒绝重写公开历史。')
            commands=[['rebase','refs/heads/'+target]]
    elif operation in ('fetch','pull','push'):
        if remote is None:raise FlowError('remote_required','明确远端名称，不能猜测推送目的地。')
        if remote not in facts['remotes']:raise FlowError('remote_unknown','远端不存在。')
        if remote!=policy['primary_remote'] and policy['collaboration']!='fork':deny('remote_mapping_denied','此工作流未允许额外协作远端。')
        if operation=='fetch':commands=[['fetch','--no-tags',remote]]
        else:
            if not target:raise FlowError('target_required','需要明确同名远端分支。')
            checked_gate(path,operation,facts['branch'],target)
            if operation=='push':commands=[['push','--no-follow-tags',remote,'refs/heads/'+facts['branch']+':refs/heads/'+target]]
            else:commands=[['fetch','--no-tags',remote,'refs/heads/'+target],['merge','--ff-only','FETCH_HEAD']]
    else:raise FlowError('operation_unknown','未知同步操作。')
    return execute(facts,'sync.'+operation,commands,apply)


def release(path, operation, name=None, source=None, targets=None, commit=None, apply=False):
    facts=require_repo(path);policy,active=load(facts);facts['policy_sha256']=active['sha256']
    key=role_for(policy,name)
    if operation=='start':
        if key not in ('release','hotfix','maintenance'):deny('release_role_required','发布入口需要 release、hotfix 或维护角色。')
        return branch(path,'create',name,source,apply=apply)
    if operation=='backport':
        return recovery(path,'backport',target=targets,commit=commit,apply=apply)
    if operation!='finish':raise FlowError('operation_unknown','未知发布操作。')
    clean(facts);local(path,name)
    if key not in ('release','hotfix'):deny('release_role_required','finish 需要工作流定义的发布/修复角色。')
    # Classic Git Flow 的 hotfix 在活跃 release 存在时必须显式包含该目标。
    default=[]
    for role in policy['roles'][key]['merge_into']:
        fixed=policy['roles'][role]['name']
        if fixed:default.append(fixed)
    active_releases=[b for b in facts['branches'] if role_for(policy,b)=='release' and b!=name]
    if policy['profile']=='classic-gitflow' and key=='hotfix':default.extend(active_releases)
    selected=targets.split(',') if targets else default
    if not selected or len(set(selected))!=len(selected) or set(selected)!=set(default):
        raise FlowError('release_targets_required','finish 必须包含全部工作流回灌目标，不能仅完成一个 merge。')
    commands=[]
    for target in selected:
        local(path,target);available(path,target,facts['root'])
        if not ancestor(path,'refs/heads/'+name,'refs/heads/'+target):
            commands.append(['switch',target]);commands.append(merge_command(policy,name))
    if commands:commands.append(['switch',facts['branch']])
    result=execute(facts,'release.finish',commands,apply)
    result['targets']=selected;result['source']=name;result['push_performed']=False
    result['remaining_targets']=[t for t in selected if not ancestor(path,'refs/heads/'+name,'refs/heads/'+t)] if apply else selected
    return result


def recovery(path, operation, target=None, commit=None, apply=False, operation_id=None):
    facts=require_repo(path);policy,active=load(facts);facts['policy_sha256']=active['sha256']
    if operation == 'resume':
        from .resume import resume
        return resume(path, operation_id, apply)
    if operation == 'diagnose':
        file=state_file(facts, 'journal.json')
        journal=read_json(file) if file.exists() else {'entries':[]}
        result=report('recovery.'+operation,facts=facts,journal=journal,
                      next_actions=[{'action':'inspect_current_state','message':'按实际 HEAD/冲突复核；resume 不重放已提交步骤。'}])
        return result
    commands=[]
    if operation=='move-changes':
        if facts['operation_states'] or not facts['head']:raise FlowError('recovery_state_invalid','中断操作期间不能迁移未提交修改。')
        local(path,target);available(path,target,facts['root'])
        role=role_for(policy,target)
        if not role or not policy['roles'][role]['allow_commit']:deny('recovery_target_denied','修改应迁入允许提交的角色。')
        commands=[['switch',target]] # Git 自身拒绝覆盖修改；无需 stash/drop。
    elif operation in ('move-commit','backport'):
        clean(facts)
        if not commit or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}',commit) or oid(path,commit)!=commit:
            raise FlowError('commit_oid_required','迁移需要完整且存在的提交 OID。')
        parents=text(path,'rev-list','--parents','-n','1',commit).split()
        if len(parents)!=2:deny('merge_commit_unsupported','自动迁移只支持单父提交，合并提交需明确主线。')
        selected=target.split(',') if target else []
        if not selected or len(set(selected))!=len(selected):raise FlowError('target_required','需要明确迁移目标。')
        original=facts['branch']
        for name in selected:
            local(path,name);available(path,name,facts['root']);role=role_for(policy,name)
            if not role:deny('recovery_target_denied','迁移目标不符合工作流。')
            if operation=='move-commit' and not policy['roles'][role]['allow_commit']:deny('recovery_target_denied','错分支提交应迁入任务分支。')
            if operation=='backport':
                sr=role_for(policy,original)
                if not sr or role not in policy['roles'][sr]['merge_into']:deny('backport_direction_denied','回灌必须符合本工作流传播方向。')
                if not ancestor(path,commit,'refs/heads/'+original):deny('commit_source_denied','回灌提交不属于声明来源分支。')
            if ancestor(path,commit,'refs/heads/'+name):continue
            # patch-id 等价的已迁移提交不再次创建，失败查询不能当作未迁移。
            equivalent=text(path,'cherry','refs/heads/'+name,commit,commit+'^')
            if equivalent.startswith('- '):continue
            commands.extend([['switch',name],['cherry-pick',commit]])
        if operation=='backport' and commands:commands.append(['switch',original])
    elif operation in ('abort','continue'):
        state=facts['operation_states']
        mapping=[('MERGE_HEAD','merge'),('rebase-merge','rebase'),('rebase-apply','rebase'),('CHERRY_PICK_HEAD','cherry-pick'),('REVERT_HEAD','revert')]
        verbs={verb for marker,verb in mapping if marker in state}
        if len(verbs)!=1:raise FlowError('recovery_state_ambiguous','需要唯一已中断 merge/rebase/cherry-pick/revert 操作。')
        if operation=='continue' and text(path,'diff','--name-only','--diff-filter=U'):
            raise FlowError('conflicts_unresolved','请先解决并暂存冲突，不能继续。')
        commands=[[verbs.pop(),'--'+operation]]
    else:raise FlowError('operation_unknown','未知恢复操作。')
    return execute(facts,'recovery.'+operation,commands,apply)

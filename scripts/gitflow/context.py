"""项目上下文与无 Git 的持久决定；状态不代表后续写操作授权。"""
import hashlib
import os
from pathlib import Path
from .git import FlowError, discover, reason, report
from .policy import load
from .storage import atomic_json, read_json, safe_dir


def choice_file(root):
    data=os.environ.get('PLUGIN_DATA')
    if not data:raise FlowError('plugin_data_required','记住决定需要宿主提供 PLUGIN_DATA；不能写入插件代码目录。')
    return safe_dir(Path(data),'context')/(hashlib.sha256(root.encode()).hexdigest()+'.json')


def context(path,choice=None,apply=False):
    facts=discover(path)
    if choice:
        if choice not in ('defer','initialize','clear'):raise FlowError('choice_invalid','决定只能为 defer/initialize/clear。')
        file=choice_file(facts['root'])
        if apply:atomic_json(file,{'root':facts['root'],'choice':choice})
        return report('context.choice','applied' if apply else 'preview',choice=choice,authorization='not_granted')
    if facts['git_state']=='absent':
        choice=None
        if os.environ.get('PLUGIN_DATA'):
            file=choice_file(facts['root'])
            if file.exists():choice=read_json(file).get('choice')
        text='当前项目未受 Git 管理。'
        text+= ('你已选择暂不启用；继续工作时保留此上下文。' if choice=='defer' else '你已选择接入 Git；执行前确认当前目录、工作流与写入范围。' if choice=='initialize' else '是否初始化 Git 并采用项目工作流，或暂不启用？')
        return report('context',context=text,facts=facts)
    try:
        policy,active=load(facts)
        role=next((k for k,r in policy['roles'].items() if r['name']==facts['branch']),None)
        text=f"项目 {facts['root']}；分支 {facts['branch']}；工作流 {policy['profile']} 修订 {policy['revision']}；定义模式 {active['mode']}。普通 Git 操作由已接线的 Agent 执行前检查与 Git 原生 hooks 守护；运行 doctor 核验接线。"
        if facts['git_state']=='unborn':text+='尚无初始提交；长期分支创建延后，初始提交需单独确认规范。'
        return report('context',context=text,facts=facts)
    except FlowError as exc:
        return report('context','unverified',[reason(exc.code,exc.message)],context=exc.message,facts=facts)

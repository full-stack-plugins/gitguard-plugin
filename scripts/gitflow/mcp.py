"""无依赖、逐行 JSON-RPC 的 MCP stdio 服务。"""
import argparse
import json
import sys
from .git import FlowError, VERSION, reason, report

FIELDS={
 'discover':[], 'audit':[],
 'gate':['action','source','target','message'],
 'init':['profile','mode','apply','initialize_git'],
 'policy':['operation','apply'],
 'branch':['operation','name','source','target','apply'],
 'sync':['operation','source','target','remote','apply'],
 'release':['operation','name','source','targets','commit','apply'],
 'recovery':['operation','target','commit','apply','operation_id'],
 'context':['choice','apply'], 'hooks':['apply'],
 'check':['base','head','source','target','message_mode','message'],
 'doctor':[], 'organization':['source','name','sha256','apply'], 'rules':[]}
READ={'discover','audit','gate','doctor','rules','check'}


def descriptors():
    result=[]
    for command,fields in FIELDS.items():
        props={'path':{'type':'string','description':'明确项目或其子目录，真实根由 Git 发现。','maxLength':4096}}
        for key in fields:
            props[key]={'type':'boolean'} if key in ('apply','initialize_git') else {'type':'string','maxLength':4096}
        result.append({'name':'gitflow_'+command,'description':command+'：项目 Git 工作流治理；写操作默认预览，apply 需当前用户授权。',
                       'inputSchema':{'type':'object','properties':props,'required':['path'],'additionalProperties':False},
                       'annotations':{'readOnlyHint':command in READ,'destructiveHint':command not in READ,'idempotentHint':command in READ,'openWorldHint':command in ('sync','organization')}})
    return result


def call(name,args):
    command=name.removeprefix('gitflow_') if isinstance(name,str) else ''
    if name!='gitflow_'+command or command not in FIELDS or not isinstance(args,dict):raise FlowError('mcp_tool_invalid','未知工具或参数不是对象。')
    if set(args)-set(['path',*FIELDS[command]]) or 'path' not in args:raise FlowError('mcp_arguments_invalid','工具参数必须闭合且含明确项目 path。')
    for key,value in args.items():
        if key in ('apply','initialize_git'):
            if type(value) is not bool:raise FlowError('mcp_arguments_invalid','apply/init 标志必须为真实布尔值。')
        elif not isinstance(value,str) or len(value)>4096 or '\x00' in value:raise FlowError('mcp_arguments_invalid','字符串参数超过预算或类型错误。')
    if command == 'rules':
        from .diagnostics import describe
        return describe(args['path'])
    from .cli import dispatch, parser
    defaults=vars(parser().parse_args([command,args['path']]))
    defaults.update(args)
    return dispatch(argparse.Namespace(**defaults))


def serve():
    initialized=False
    while True:
        raw=sys.stdin.buffer.readline(65537)
        if not raw:break
        if len(raw)>65536:
            while raw and not raw.endswith(b'\n'):raw=sys.stdin.buffer.readline(65537)
            print(json.dumps({'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Request too large'}}),flush=True)
            continue
        ident=None
        try:
            if len(raw)>65536:raise ValueError('request limit')
            msg=json.loads(raw)
            if not isinstance(msg,dict) or msg.get('jsonrpc')!='2.0' or not isinstance(msg.get('method'),str):raise ValueError('invalid envelope')
            ident=msg.get('id')
            if ident is not None and (type(ident) not in (str,int)):raise ValueError('invalid id')
            method=msg['method'];params=msg.get('params',{})
            if not isinstance(params,dict):raise ValueError('invalid params')
            if method=='initialize':
                requested=params.get('protocolVersion')
                if not isinstance(requested,str):raise ValueError('protocol version required')
                protocol=requested if requested in ('2024-11-05','2025-03-26','2025-06-18','2025-11-25') else '2025-11-25'
                result={'protocolVersion':protocol,'capabilities':{'tools':{'listChanged':False}},'serverInfo':{'name':'gitflow','version':VERSION}}
                initialized=True
            elif method=='notifications/initialized':continue
            elif method=='ping':result={}
            elif not initialized:
                reply={'jsonrpc':'2.0','id':ident,'error':{'code':-32002,'message':'Initialize required'}}
                if 'id' in msg:print(json.dumps(reply),flush=True)
                continue
            elif method=='tools/list':result={'tools':descriptors()}
            elif method=='tools/call':
                if 'id' not in msg:continue
                try:
                    if set(params)-{'name','arguments','_meta'}:raise FlowError('mcp_arguments_invalid','工具调用含未知字段。')
                    if '_meta' in params and not isinstance(params['_meta'],dict):
                        raise FlowError('mcp_arguments_invalid','MCP 元数据必须为对象。')
                    # Standard transport metadata is not forwarded as tool arguments
                    # and cannot grant apply or change the requested operation.
                    r=call(params.get('name'),params.get('arguments',{}))
                except FlowError as exc:r=report('mcp.call',exc.decision,[reason(exc.code,exc.message)])
                except (OSError,ValueError,KeyError,TypeError,AttributeError):r=report('mcp.call','error',[reason('internal_error','工具未完成，不采用部分结果。')])
                result={'content':[{'type':'text','text':json.dumps(r,ensure_ascii=False)}], 'isError':r['decision'] in ('deny','unverified','error')}
            else:
                if 'id' in msg:print(json.dumps({'jsonrpc':'2.0','id':ident,'error':{'code':-32601,'message':'Method not found'}}),flush=True)
                continue
            if 'id' in msg:print(json.dumps({'jsonrpc':'2.0','id':ident,'result':result},ensure_ascii=False),flush=True)
        except (ValueError,UnicodeError,TypeError,RecursionError):
            print(json.dumps({'jsonrpc':'2.0','id':ident,'error':{'code':-32600,'message':'Invalid bounded JSON-RPC request'}}),flush=True)
    return 0

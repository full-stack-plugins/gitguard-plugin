"""Standard MCP request metadata is transport data, never tool authorization."""
import json
import subprocess
import sys
from test_core import GitTestCase, CLI


class MetadataTests(GitTestCase):
    def invoke(self, params):
        requests = [
            {'jsonrpc':'2.0','id':1,'method':'initialize',
             'params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'fixture','version':'1'}}},
            {'jsonrpc':'2.0','method':'notifications/initialized'},
            {'jsonrpc':'2.0','id':2,'method':'tools/call','params':params},
        ]
        result = subprocess.run([sys.executable, '-B', str(CLI), 'mcp'],
                                input=''.join(json.dumps(r)+'\n' for r in requests),
                                capture_output=True, text=True, env=self.env, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        reply = next(json.loads(line) for line in result.stdout.splitlines() if json.loads(line).get('id') == 2)
        return json.loads(reply['result']['content'][0]['text'])

    def test_codex_metadata_does_not_change_tool_result_or_authorize_writes(self):
        self.repository()
        params = {'name':'gitflow_discover','arguments':{'path':str(self.path)}}
        before = self.git('status','--porcelain')
        expected = self.invoke(params)
        actual = self.invoke({**params, '_meta':{'progressToken':'p-1','threadId':'t-1', 'apply':True}})
        self.assertEqual(actual, expected)
        self.assertEqual(actual['git_state'], 'repository')
        self.assertEqual(self.git('status','--porcelain'), before)
        self.assertFalse((self.path/'.gitflow').exists())

    def test_invalid_metadata_and_unknown_fields_remain_closed(self):
        self.repository()
        params = {'name':'gitflow_discover','arguments':{'path':str(self.path)}}
        variants = [{**params,'_meta':value} for value in (None, [], 'token', True, 1)]
        variants += [{**params,'unknown':{}}, {**params,'arguments':{'path':str(self.path),'apply':True}}]
        for invalid in variants:
            with self.subTest(params=invalid):
                result = self.invoke(invalid)
                self.assertEqual(result['decision'], 'unverified')
                self.assertEqual(result['reasons'][0]['code'], 'mcp_arguments_invalid')

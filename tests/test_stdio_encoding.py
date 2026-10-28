"""UTF-8 command/MCP wire output must not depend on Windows pipe codepages."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EncodingTests(unittest.TestCase):
    def execute(self, script, arguments, data=None):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'scripts' / script), *arguments],
                              input=data, capture_output=True, timeout=15,
                              env={**os.environ, 'PYTHONIOENCODING':'cp1252'})

    def test_help_preserves_chinese_as_utf8_under_non_utf8_pipe(self):
        for script in ('gitflow.py', 'cli_entry.py'):
            with self.subTest(script=script):
                result = self.execute(script, ['--help'])
                self.assertEqual(result.returncode, 0, result.stderr.decode('ascii', errors='replace'))
                self.assertIn('项目 Git 分支治理', result.stdout.decode('utf-8'))
                self.assertNotIn(b'Traceback', result.stderr)

    def test_lifecycle_usage_error_is_utf8_json_without_traceback(self):
        for script in ('install_cli.py', 'cli_entry.py'):
            with self.subTest(script=script):
                result = self.execute(script, ['install', '--unsupported-中文'])
                self.assertEqual(result.returncode, 2, result.stderr.decode('ascii', errors='replace'))
                payload = json.loads(result.stdout.decode('utf-8'))
                self.assertEqual(payload['decision'], 'error')
                self.assertIn('中文', payload['message'])
                self.assertNotIn(b'Traceback', result.stderr)

    def test_mcp_error_preserves_utf8_transport(self):
        requests = [
            {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25'}},
            {'jsonrpc':'2.0','id':2,'method':'tools/call',
             'params':{'name':'未知工具','arguments':{'path':'中文项目'}}},
        ]
        data = ''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in requests).encode('utf-8')
        result = self.execute('gitflow.py', ['mcp'], data)
        self.assertEqual(result.returncode, 0, result.stderr.decode('ascii', errors='replace'))
        response = json.loads(result.stdout.decode('utf-8').splitlines()[1])
        report = json.loads(response['result']['content'][0]['text'])
        self.assertEqual(report['reasons'][0]['code'], 'mcp_tool_invalid')
        self.assertIn('未知工具', report['reasons'][0]['message'])

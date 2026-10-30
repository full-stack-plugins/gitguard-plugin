"""规则的可观察结果、兼容边界及真实提交入口。"""
import json
import subprocess
from test_core import GitTestCase, ROOT


class RuleCase(GitTestCase):
    def configured(self, rules, profile='github-flow'):
        self.repository()
        policy = json.loads((ROOT / 'profiles' / (profile + '.json')).read_text())
        policy.update(schema_version='2.0.0', rules=rules, extends=None)
        folder = self.path / '.gitflow'
        folder.mkdir()
        (folder / 'workflow.json').write_text(json.dumps(policy))
        self.cli('policy', self.path, '--operation','migrate','--apply')
        self.git('add', '.gitflow', 'app.txt')
        self.git('commit', '-m', 'chore: configure')
        self.git('switch', '-c', 'feature/rules')
        return policy

    def check(self, message, code=0):
        return self.cli('gate', self.path, '--action', 'commit', '--message', message, code=code)


class PolicyRuleTests(RuleCase):
    def test_conventional_message_gives_mechanical_fix_without_mutation(self):
        self.configured({'GF001': {'severity': 'error'}})
        before = self.git('status', '--porcelain')
        r = self.check('Fix: 修复登录超时', code=1)
        check = next(x for x in r['checks'] if x['rule_id'] == 'GF001')
        self.assertEqual(check['fix'], 'fix: 修复登录超时')
        self.assertEqual(check['status'], 'fail')
        self.assertEqual(self.git('status', '--porcelain'), before)
        r = self.check('修复登录超时', code=1)
        self.assertIsNone(next(x for x in r['checks'] if x['rule_id'] == 'GF001')['fix'])
        self.check('feat(auth)!: 更新接口\n\nBREAKING CHANGE: 接口变化')

    def test_warning_reports_failure_without_blocking(self):
        self.configured({'GF002': {'severity': 'warn', 'options': {'max_length': 12}}})
        r = self.check('feat: add a very long description')
        check = next(x for x in r['checks'] if x['rule_id'] == 'GF002')
        self.assertEqual((r['decision'], check['severity'], check['status']), ('allow', 'warn', 'fail'))

    def test_invalid_configuration_cannot_be_silently_disabled(self):
        self.configured({'GF001': {'severity': 'error'}})
        from gitflow.xml_policy import read_policy, _element
        import xml.etree.ElementTree as ET
        file=self.path/'.git/gitflow.xml'
        original=read_policy({'common_dir':str(self.path/'.git')})
        for rules in ({'GF999': {'severity': 'off'}}, {'GF002': {'severity': 'error', 'options': {'max_length': True}}}, {'GF001': {'severity': 'error', 'options': {'unknown': 1}}}):
            # Serialize deliberately invalid XML without the production writer's validation.
            file.write_bytes(ET.tostring(_element('policy',{**original,'rules':rules})))
            self.cli('policy',self.path,'--apply',code=3)

    def test_author_signoff_and_ai_disclosure(self):
        self.configured({'GF101': {'severity': 'error', 'options': {'pattern': '^Tester$'}},
                         'GF102': {'severity': 'error', 'options': {'pattern': '^test@example[.]invalid$'}},
                         'GF103': {'severity': 'error'},
                         'GF104': {'severity': 'error', 'options': {'mode': 'disclose'}}})
        self.check('fix: repair', code=1)
        self.check('fix: repair\n\nSigned-off-by: Tester <test@example.invalid>\nAssisted-by: Claude Code')
        self.check('fix: repair\n\nSigned-off-by: Tester <test@example.invalid>\nAssisted-by: Claude Code\nCo-authored-by: Claude <noreply@anthropic.com>', code=1)

    def test_native_hook_blocks_and_then_accepts_same_policy(self):
        self.configured({'GF001': {'severity': 'error'}})
        self.cli('hooks', self.path, '--apply')
        p = subprocess.run(['git', '-C', str(self.path), 'commit', '--allow-empty', '-m', 'bad message'], env=self.env, capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('GF001', p.stdout + p.stderr)
        self.git('commit', '--allow-empty', '-m', 'fix: proper message')

    def test_protected_branch_is_not_relaxed_by_off_rules(self):
        self.configured({'GF001': {'severity': 'off'}})
        self.git('switch', 'main')
        r = self.check('anything', code=1)
        self.assertIn('protected_branch_commit', [x['code'] for x in r['reasons']])

    def test_mcp_rule_result_matches_cli(self):
        self.configured({'GF001': {'severity': 'error'}})
        import sys
        requests = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05'}},
                    {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'gitflow_gate', 'arguments': {'path': str(self.path), 'action': 'commit', 'message': 'Fix: repair'}}}]
        p = subprocess.run([sys.executable, str(ROOT / 'scripts/gitflow.py'), 'mcp'], input=''.join(json.dumps(x)+'\n' for x in requests), env=self.env, capture_output=True, text=True, check=True)
        result = json.loads(json.loads(p.stdout.splitlines()[-1])['result']['content'][0]['text'])
        self.assertEqual(result['checks'], self.check('Fix: repair', code=1)['checks'])

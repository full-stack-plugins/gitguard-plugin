"""真实提交图及 GitHub event 回放，不执行被检仓库代码。"""
import json
import os
import subprocess
import sys
from test_policy_rules import RuleCase
from test_core import ROOT


class CIGovernanceTests(RuleCase):
    def prepare(self, extra=None):
        self.configured(extra or {'GF001': {'severity': 'error'}})
        self.base = self.git('rev-parse', 'HEAD')
        from gitflow.xml_policy import read_policy
        self.trusted_policy=read_policy({'common_dir':str(self.path/'.git')})

    def commit(self, message):
        self.git('commit', '--allow-empty', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def run_check(self, head, *args, code=0, source='feature/rules', target='main'):
        # Evaluate an explicitly supplied trusted test policy, not the disabled
        # public CI trust integration. Public CLI fail-closed is tested separately.
        from gitflow.ci import evaluate_range
        from gitflow.git import FlowError, report, reason
        options=dict(zip(args[::2],args[1::2]))
        try:r=evaluate_range(str(self.path),self.base,head,source,target,self.trusted_policy,
                             options.get('--message-mode','commits'),options.get('--message'))
        except FlowError as exc:r=report('check',exc.decision,[reason(exc.code,exc.message)])
        self.assertEqual({'allow':0,'deny':1,'unverified':3}[r['decision']],code,r)
        return r

    def test_all_commits_checked_and_detached_checkout_is_readonly(self):
        self.prepare()
        bad = self.commit('missing type')
        head = self.commit('fix: valid latest commit')
        self.git('switch', '--detach')
        before = self.git('show-ref')
        r = self.run_check(head, code=1)
        self.assertEqual(r['commit_count'], 2)
        self.assertEqual(r['policy_source'], 'caller_supplied_no_distribution_attestation')
        self.assertNotIn('policy_ref',r)
        self.assertIn(bad, [x['oid'] for x in r['commits'] if x['decision'] == 'deny'])
        self.assertEqual(self.git('show-ref'), before)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_head_policy_cannot_disable_base_rules(self):
        self.prepare()
        file = self.path / '.gitflow/workflow.json'
        policy = json.loads(file.read_text());policy['rules'] = {};file.write_text(json.dumps(policy))
        self.git('add', str(file))
        head = self.commit('unformatted bypass')
        self.run_check(head, code=1)

    def test_merge_direction_is_enforced(self):
        self.prepare()
        r = self.run_check(self.commit('feat: valid'), target='feature/other', code=1)
        self.assertIn('merge_target_denied', [x['code'] for x in r['reasons']])

    def test_missing_object_and_unrelated_history_are_unverified(self):
        self.prepare()
        self.run_check('a'*40, code=3)
        tree = self.git('rev-parse', 'HEAD^{tree}')
        root_commit = self.git('commit-tree', tree, '-m', 'feat: disconnected')
        self.run_check(root_commit, code=3)

    def test_squash_needs_candidate_and_checks_it(self):
        self.prepare()
        head = self.commit('wip draft')
        self.run_check(head, '--message-mode', 'squash', code=3)
        r = self.run_check(head, '--message-mode', 'squash', '--message', 'feat: squash candidate')
        self.assertEqual(r['message_mode'], 'squash')
        self.run_check(head, '--message-mode', 'squash', '--message', 'bad candidate', code=1)

    def test_tag_metadata_is_checked(self):
        self.prepare({'GF401': {'severity': 'error'}})
        head = self.commit('feat: version')
        self.git('tag', 'bad-tag')
        r = self.run_check(head, code=1)
        self.assertTrue(any(x['rule_id'] == 'GF401' and x['status'] == 'fail' for x in r['tag_checks']))

    def test_ci_requires_trusted_distribution_not_local_activation(self):
        self.prepare()
        r=self.cli('check',self.path,'--base',self.base,'--head',self.base,'--source','feature/rules','--target','main',code=3)
        self.assertEqual(r['reasons'][0]['code'],'ci_policy_unconfigured')

    def test_action_event_runner_rejects_bad_pr_without_shell_execution(self):
        self.prepare()
        head = self.commit('wip draft')
        marker = self.path.parent / 'injected'
        event = {'pull_request': {'base': {'sha': self.base, 'ref': 'main'}, 'head': {'sha': head, 'ref': 'feature/rules'}, 'title': f'$(touch {marker}) <script>', 'body': 'body'}}
        event_file = self.path.parent / 'event.json';event_file.write_text(json.dumps(event))
        output = self.path.parent / 'report.json'
        summary = self.path.parent / 'summary.md'
        p = subprocess.run([sys.executable, str(ROOT/'scripts/ci_check.py'), '--repo', str(self.path), '--event', str(event_file), '--message-mode', 'squash', '--output', str(output), '--summary', str(summary)], env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 3, p.stdout+p.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual(json.loads(output.read_text())['decision'], 'unverified')
        self.assertNotIn('<script>', summary.read_text())

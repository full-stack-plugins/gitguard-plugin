# ci-governance Specification

> **Authority update — XML native guard:** The current contract is [XML native governance](../../changes/xml-native-guard/specs/xml-native-guard/spec.md). Runtime policy is exclusively `<git-common-dir>/gitflow.xml`; legacy JSON and organization snapshots are explicit migration inputs, then flattened into XML. Public CI `check` remains unconfigured until separately trusted XML distribution exists. Conflicting JSON authority, implicit activation, baseline runtime lookup, and public CI enablement statements below describe the historical contract and are superseded.

## Purpose
让业务仓库在 PR 和 CI 中验证真实提交范围、工作流合并方向及候选 squash 消息，绑定明确 Git 对象和受信规则来源，使远端复核与本地规则引擎保持一致而不执行 PR 中的代码。
## Requirements
### Requirement: Read-only commit range validation
系统 SHALL 接受明确完整 base/head OID、源分支和目标分支，检查 base..head 全部提交（最多 500）、各提交真实作者及消息和头提交标签；不依赖当前检出分支，不写入本机激活。缺对象、浅克隆、无共同祖先、范围超预算返回未验证，不能只检查最后一个提交后报告全通过。

#### Scenario: Earlier bad commit is caught
- **WHEN** PR 包含一条错误提交和一条合规提交
- **THEN** 范围结果拒绝，标出错误提交 OID，绑定 base/head 和 policy SHA

#### Scenario: Detached CI checkout is supported
- **WHEN** 当前 HEAD 分离，但完整 OID 与源/目标分支明确
- **THEN** 按提供的 PR 身份验证，不因 checkout 分离而跳过规则

### Requirement: Trusted policy and merge direction
系统 MUST 从 base 提交中的 .gitflow/workflow.json 及其固定摘要组织快照加载策略。head 对规则的修改不能用于放行同一个 PR。源角色到目标角色必须符合规则；配置为 squash 时只检查显式候选消息，缺少候选消息不得采用最后一个提交代替。仍核验实际提交作者，提交范围不可省略。

#### Scenario: Pull request cannot weaken its own policy
- **WHEN** head 修改规则以允许非法合并或禁用提交检查
- **THEN** 继续使用 base 策略，拒绝违规并报告受信 policy_ref

#### Scenario: Squash candidate is explicit
- **WHEN** check 模式为 squash 且未提供候选消息文件或消息
- **THEN** 返回未验证；提供候选后按相同消息规则检查

### Requirement: Reusable GitHub Action
系统 SHALL 提供可复用 Action 和最小 PR 工作流示例。Action 使用自身发布版本的引擎，解析 GitHub event 文件获取 base/head/source/target，受控读取业务仓库 Git 对象；不执行 PR 脚本，不采用 head 中替换的引擎；产生 JSON 与 Markdown 摘要及非零违规退出码。文档明确 required status check 需仓库管理员配置，Action 自测不能冒充真实宿主/业务仓库安装。

#### Scenario: Untrusted message does not execute shell
- **WHEN** PR 标题或提交消息包含 shell 元字符、换行或 HTML
- **THEN** 作为数据检查/转义展示，不执行；实际失败使 Action 失败


# policy-rules Specification

> **Authority update — XML native guard:** The current contract is [XML native governance](../../changes/xml-native-guard/specs/xml-native-guard/spec.md). Runtime policy is exclusively `<git-common-dir>/gitflow.xml`; legacy JSON and organization snapshots are explicit migration inputs, then flattened into XML. Public CI `check` remains unconfigured until separately trusted XML distribution exists. Conflicting JSON authority, implicit activation, baseline runtime lookup, and public CI enablement statements below describe the historical contract and are superseded.

## Purpose
为 AI、CLI 和原生 Hook 提供一致、可解释的项目 Git 规则检查，允许团队渐进启用元数据约定，同时保持既有工作流保护、退出码和显式变更授权不被弱化。
## Requirements
### Requirement: Versioned rule configuration
系统 SHALL 继续接受 workflow 1.0.0 且不新增默认拦截；workflow 2.0.0 增加 rules、extends 字段。每条已知规则可配置 off/warn/error 和闭合参数；未知规则、未知参数、错误类型、非法正则 MUST 返回未验证。既有分支保护/来源/流转及未知 Git 状态不能通过规则级别关闭。

#### Scenario: Existing repository remains compatible
- **WHEN** v1 项目执行旧 gate、branch、release 和恢复动作
- **THEN** 维持原有判定和状态目录，不隐式升级规则

#### Scenario: Warning is not an error
- **WHEN** 提交标题超限且该规则为 warn
- **THEN** 返回带失败事实的 warning 检查结果，单凭此项不阻断；error 时阻断；off 时标记 skipped

### Requirement: Deterministic metadata rules
系统 SHALL 提供稳定编号 GF001 提交格式、GF002 标题长度、GF101 作者名称、GF102 作者邮箱、GF103 Signed-off-by、GF104 AI 声明、GF401 Tag 格式；不启用未配置规则。AI 声明支持 ignore/forbid/disclose，disclose 要求 Assisted-by 且不允许已识别 AI 作为 Co-authored-by/Signed-off-by。声明检查不推断代码作者，Signed-off-by 不表示密码学签名。格式规则接受中文描述与 breaking 标记，可配置允许 merge 消息。

#### Scenario: Mechanical correction is provided
- **WHEN** 格式规则检查 Fix: 修复超时
- **THEN** 返回稳定 rule_id、severity、status、actual、expected、message、suggestion、fix=fix: 修复超时；不修改消息或仓库

#### Scenario: Semantic correction remains a suggestion
- **WHEN** 消息缺少可判断的提交类型
- **THEN** fix 为 null，仅给建议，不能猜测 feat/fix

#### Scenario: Missing identity is not success
- **WHEN** 已启用作者或标签规则，但对应检查上下文缺失
- **THEN** 适用的检查返回未验证；不适用的规则明确 skipped，不伪造 pass

### Requirement: Shared engine across entry points
系统 SHALL 在 gate、MCP、原生 commit-msg 和 CI 使用同一元数据引擎，报告 effective policy 摘要。普通提交及受管集成提交都检查已启用元数据；受管集成仍须通过原日志身份验证。检查及修复建议不写工作树、不 fetch、不自动修复或提交。

#### Scenario: Native hook matches CLI policy
- **WHEN** v2 项目通过 CLI、MCP 或实际 git commit 提交同一不合规消息
- **THEN** 三入口均拒绝，warning-only 均不因此拒绝，原生 Hook 输出规则原因


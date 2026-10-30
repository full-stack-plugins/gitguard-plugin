# organization-policy Specification

> **Authority update — XML native guard:** The current contract is [XML native governance](../../changes/xml-native-guard/specs/xml-native-guard/spec.md). Runtime policy is exclusively `<git-common-dir>/gitflow.xml`; legacy JSON and organization snapshots are explicit migration inputs, then flattened into XML. Public CI `check` remains unconfigured until separately trusted XML distribution exists. Conflicting JSON authority, implicit activation, baseline runtime lookup, and public CI enablement statements below describe the historical contract and are superseded.

## Purpose
为多个项目复用可追踪、固定摘要的组织 Git 元数据规则，并以显式更新、锁定覆盖边界、只读规则解释和接线诊断防止配置漂移及误报宿主已正确启用。
## Requirements
### Requirement: Pinned organization baseline
系统 SHALL 支持 workflow v2 extends 引用 .gitflow/baselines/ 下普通 JSON 文件和固定 SHA-256。组织文件包含 schema_version、rules、locked_rules，禁止递归继承；项目规则覆盖非锁定规则。基线缺失、摘要不同、链接、路径越界、未知规则或覆盖锁定规则返回未验证。激活时保存合并后的有效规则；本地生效快照仍可独立使用。

#### Scenario: Baseline cannot silently disappear
- **WHEN** 共享候选引用缺失或摘要不匹配的组织基线
- **THEN** 激活/检查失败，不退回空规则或只用项目规则

#### Scenario: Locked organization rule cannot be relaxed
- **WHEN** 组织锁定某规则，项目设置不同参数或严重级别
- **THEN** 返回明确冲突，既有快照不改变

### Requirement: Explicit baseline import
系统 SHALL 提供 organization import 默认预览、显式 apply 导入本地文件或 HTTPS 资源到 .gitflow/baselines/<name>.json，要求调用方提供预期原始文件 SHA-256；验证大小、JSON、规则与摘要后原子写入。不覆盖不同的已有文件，不自动修改 workflow 或激活，不经网络静默更新规则。HTTPS 设置超时和响应预算且拒绝降级重定向。

#### Scenario: Import preview has no side effects
- **WHEN** 预览一个 HTTPS 组织快照
- **THEN** 不联网、不创建目录，返回拟导入来源、目标和摘要

### Requirement: Explain and diagnose without overstating enforcement
系统 SHALL 提供 CLI/MCP 规则解释，显示有效规则、严重级别、组织/项目来源、修订和摘要；提供 doctor 检查 Git 状态、规则、Hook 路径/入口和项目 CI 配置线索。宿主 MCP 接线与服务端保护未实际验证时标记 unverified；不得因插件自带 MCP 清单或文件存在报告宿主已启用。

#### Scenario: Missing integration is visible
- **WHEN** 项目已激活规则但未安装原生 Hook
- **THEN** doctor 报告 missing Hook 和明确接入指引，执行前后文件不变


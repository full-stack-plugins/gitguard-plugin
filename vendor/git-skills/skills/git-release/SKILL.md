---
name: git-release
description: 在开始/完成 release、hotfix、维护分支及选择性回灌任务时使用；校验工作流传播方向、全部目标与中断状态。
---

# 发布、修复与版本回灌

## 什么时候使用与不适用

本技能不适用于代替 CodeGuard 质量、平台保护或部署验收。它可单独安装；没有 GitFlow 插件时，使用只读 Git 观察与逐条规则核验。不会依赖相邻技能文件或假定宿主自动加载其他技能。

## 前置条件与授权

- Git 可用，项目目录明确。先确认父仓真实根与项目指令，保留用户修改。
- 既有规范优先；无 Git、无规范、detached、浅历史与未知来源需要明确报告。
- 只读观察和预览可执行；Git 初始化、分支创建/切换、提交、推送、集成、清理、安装 Hook 与规则激活按用户已有授权范围执行。
- [项目规则与证据](references/contract.md) 是本技能自包含参考；[权威目录](references/workflows.md) 用于模型与来源核验。

## 执行步骤

### Step 1

先确认项目模型与具体版本，不把 release 标签、维护分支和环境部署混为同一流程。
### Step 2

Classic release 从 develop，hotfix 从 main；start 记录确切基线，命名满足项目约定，不自动切换或发布。
### Step 3

finish 列出所有合入角色：release→main/develop；hotfix→main/develop，并覆盖活跃 release。列出每个目标 OID。
### Step 4

目标 worktree 占用、dirty、候选漂移等先处理。已授权后逐目标集成并记录 before/after；冲突停在真实目标。
### Step 5

Microsoft Release Flow 先主线修复再 cherry-pick 到维护线；Git maintainer 从最老适用维护线起向上 merge。
### Step 6

回灌限定完整单父提交 OID，检查已合入/等价补丁避免重复。merge commit 需明确主线，不默认 -m 1。
### Step 7

核对每个目标包含修复、余下目标及冲突；finish 不自动 push/tag/部署，版本发布需独立授权与验收。

## 独立工具与插件路径

先定位本技能 scripts/inspect_repository.py，按 [契约](references/contract.md) 中的命令读取状态。Python 3.11+ 标准库，只读且不初始化。实际命令使用当前技能所在目录；挂载示例为：

```bash
python3 /mnt/skills/user/git-release/scripts/inspect_repository.py /absolute/project
```

GitFlow 插件可用时调用其实际路径对应命令，详见 [操作样例](references/action.md)。不得把未安装的 CLI 名称当已存在命令。

## v2 治理补充

GF401 仅检查本地已观察到、指向 head 的标签；仍逐目标核验回灌，不将标签格式通过当发布完成。 细节见本技能 references/contract.md。

## 验证与输出

保留源分支与日志直到所有目标核验。原生流程并不默认删除分支或发布 tag。

输出必须区分：事实、规则来源、建议、用户授权和未验证项。写操作后核对当前 refs/HEAD/status；计划和预览不是完成证据。安全边界：不泄露凭据，不上传工作树；不在日志暴露凭据、整段工作树内容或敏感远端 URL。

## 正例

hotfix/security 完成时覆盖 main、develop、活跃 release/1.0，任意冲突留下未完成列表。

## 反例

main merge 完了就宣称发布完成，遗漏 develop；或将 Microsoft 维护线整体 merge 回 main。

## Gotchas（容易误判的情形）

- `.git` 是文件时仍可能是有效工作树；先查询 Git/common-dir。
- 分支模式符合不证明来源正确；人工创建但缺记录应单列 unknown。
- 远端跟踪和保护配置文字不能证明实时远端已落实。
- 新项目空历史不预创建虚假的长期 refs；初始提交须明确 bootstrap 方案。
- 定义改动先复核激活修订；通过质量检查不能豁免分支规则。
- 已经完成的步骤不因超时无响应而盲重放；先查 Git 状态和操作日志。

## 异常处理

规则缺失/漂移/损坏、身份不明、操作中断或来源证据不足：停止相关写动作，报告 unverified 和具体所需信息，继续可独立完成的只读工作。明确命名/流转违规：deny 并给出保留式修复方向。Git 不可用或网络失败：不自动安装，不把失败当成功。冲突保留真实现场，按恢复步骤处理。

## 可选交接

需要其他职责时按名称调用，不假定该技能已安装。例如工作流选型可交给 **`git-workflow`**；Install: `npx skills add full-stack-skills/git-skills --skill git-workflow`。任何交接都不能扩大用户授权。

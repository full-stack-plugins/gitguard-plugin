---
name: git-commit
description: 在 AI 或开发者提交代码前检查当前 Git 分支角色、名称、项目提交消息和允许提交策略时使用；分支批准不代表代码质量批准。
---

# 提交前分支与消息门禁

## 什么时候使用与不适用

本技能不适用于代替 CodeGuard 质量、平台保护或部署验收。它可单独安装；没有 GitFlow 插件时，使用只读 Git 观察与逐条规则核验。不会依赖相邻技能文件或假定宿主自动加载其他技能。

## 前置条件与授权

- Git 可用，项目目录明确。先确认父仓真实根与项目指令，保留用户修改。
- 既有规范优先；无 Git、无规范、detached、浅历史与未知来源需要明确报告。
- 只读观察和预览可执行；Git 初始化、分支创建/切换、提交、推送、集成、清理、安装 Hook 与规则激活按用户已有授权范围执行。
- [项目规则与证据](references/contract.md) 是本技能自包含参考；[权威目录](references/workflows.md) 用于模型与来源核验。

## 执行步骤

### Step 1

在 add/commit 之前发现真实分支、HEAD 与状态；detached 或中断操作进入恢复，不猜测当前角色。
### Step 2

验证当前名称匹配唯一角色与已激活规则；候选漂移/损坏/规则缺失返回未验证。
### Step 3

检查 allow_commit；保护 main/develop 等按项目约定禁止日常直接提交，提示正确任务分支。
### Step 4

检查完整提交消息与项目模式；没有设置消息模式时不强加 Conventional Commits。
### Step 5

首次空历史提交单独说明 bootstrap 边界：默认 classic main 禁止日常直提，需用户确认初始提交方案，不暗设例外。
### Step 6

分别完成用户要求的代码质量检查；git gate 的 allow 仅指分支规则，不代替 CodeGuard/测试。
### Step 7

已授权提交前检查暂存范围、防止混入无关修改；提交后核验 SHA、branch、status，不自动推送。

## 独立工具与插件路径

先定位本技能 scripts/inspect_repository.py，按 [契约](references/contract.md) 中的命令读取状态。Python 3.11+ 标准库，只读且不初始化。实际命令使用当前技能所在目录；挂载示例为：

```bash
python3 /mnt/skills/user/git-commit/scripts/inspect_repository.py /absolute/project
```

GitFlow 插件可用时调用其实际路径对应命令，详见 [操作样例](references/action.md)。不得把未安装的 CLI 名称当已存在命令。

## v2 治理补充

提交前检查 v2 checks 的逐条结果与真实作者；确定性 fix 仅作建议，warning 不阻断但未知不放行。GF103 不等同 GPG 签名。 细节见本技能 references/contract.md。

## 验证与输出

插件 gate --action commit --message 提供机器结果；native commit-msg 可显式安装，现有 Hook 保留。

输出必须区分：事实、规则来源、建议、用户授权和未验证项。写操作后核对当前 refs/HEAD/status；计划和预览不是完成证据。安全边界：不泄露凭据，不上传工作树；不在日志暴露凭据、整段工作树内容或敏感远端 URL。

## 正例

feature/123-login 提交消息满足项目格式，分支 gate 通过，再按当前任务授权提交并报告 SHA。

## 反例

在 main 直提，因为测试全通过而跳过角色约定；或把 amend 当普通提交改写公开历史。

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

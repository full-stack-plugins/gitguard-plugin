---
name: git-branch
description: 在按项目规则创建、切换、重命名或清理 Git 分支，以及补齐缺失长期分支时使用；校验名称、角色、基线和 worktree 占用。
---

# 分支生命周期

## 什么时候使用与不适用

本技能不适用于代替 CodeGuard 质量、平台保护或部署验收。它可单独安装；没有 GitFlow 插件时，使用只读 Git 观察与逐条规则核验。不会依赖相邻技能文件或假定宿主自动加载其他技能。

## 前置条件与授权

- Git 可用，项目目录明确。先确认父仓真实根与项目指令，保留用户修改。
- 既有规范优先；无 Git、无规范、detached、浅历史与未知来源需要明确报告。
- 只读观察和预览可执行；Git 初始化、分支创建/切换、提交、推送、集成、清理、安装 Hook 与规则激活按用户已有授权范围执行。
- [项目规则与证据](references/contract.md) 是本技能自包含参考；[权威目录](references/workflows.md) 用于模型与来源核验。

## 执行步骤

### Step 1

先发现仓库并读取已生效规则；记录 HEAD 与未提交修改，未知规范不先建 feature 分支。
### Step 2

创建时双重校验 git check-ref-format --branch 和项目角色 pattern；拒绝 @{-n} 这类动态前一分支语法。
### Step 3

查询确切本地来源 refs/heads 与 OID，检查 create_from 角色；不要用共同祖先倒推过去创建来源。
### Step 4

列出创建/切换计划，得到对应授权后执行；插件 create 不自动 switch，切换是单独操作。
### Step 5

切换前保护 dirty；若需携带修改用恢复路径，不自动 stash/drop。查询 worktree list 避免争抢其他工作树分支。
### Step 6

重命名保持原角色，拒绝覆盖已有分支和重命名固定保护角色；更新 provenance。
### Step 7

清理前检查真实目标完全包含源分支、合入方向、当前/worktree 占用；不强制删除未合入历史。reconcile 仅补长期固定角色。

## 独立工具与插件路径

先定位本技能 scripts/inspect_repository.py，按 [契约](references/contract.md) 中的命令读取状态。Python 3.11+ 标准库，只读且不初始化。实际命令使用当前技能所在目录；挂载示例为：

```bash
python3 /mnt/skills/user/git-branch/scripts/inspect_repository.py /absolute/project
```

GitFlow 插件可用时调用其实际路径对应命令，详见 [操作样例](references/action.md)。不得把未安装的 CLI 名称当已存在命令。

## v2 治理补充

分支角色、命名、来源和流转是硬门禁；关闭提交格式规则不能豁免保护分支或创建基线。 细节见本技能 references/contract.md。

## 验证与输出

执行后核验新旧 refs、当前分支、HEAD 与 origin 记录；空历史不假造 main/develop 指针。

输出必须区分：事实、规则来源、建议、用户授权和未验证项。写操作后核对当前 refs/HEAD/status；计划和预览不是完成证据。安全边界：不泄露凭据，不上传工作树；不在日志暴露凭据、整段工作树内容或敏感远端 URL。

## 正例

classic feature/123-login 从 develop 创建并记录来源 OID，显式 switch 后开始工作。

## 反例

feature 从 main 起步却因为命名正确就通过；清理 release 时忽略未完成 develop 回灌。

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

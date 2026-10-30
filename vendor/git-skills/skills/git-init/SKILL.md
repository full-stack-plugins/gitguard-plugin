---
name: git-init
description: 在开始处理项目、发现没有 Git、空历史、新工作树或已有仓库首次接入 Git 规范时使用；先只读检测，初始化必须明确授权。
---

# Git 状态发现与接入

## 什么时候使用与不适用

本技能不适用于代替 CodeGuard 质量、平台保护或部署验收。它可单独安装；没有 GitFlow 插件时，使用只读 Git 观察与逐条规则核验。不会依赖相邻技能文件或假定宿主自动加载其他技能。

## 前置条件与授权

- Git 可用，项目目录明确。先确认父仓真实根与项目指令，保留用户修改。
- 既有规范优先；无 Git、无规范、detached、浅历史与未知来源需要明确报告。
- 只读观察和预览可执行；Git 初始化、分支创建/切换、提交、推送、集成、清理、安装 Hook 与规则激活按用户已有授权范围执行。
- [项目规则与证据](references/contract.md) 是本技能自包含参考；[权威目录](references/workflows.md) 用于模型与来源核验。

## 执行步骤

### Step 1

运行本技能只读脚本，确认父仓真实根、HEAD、Git/common/worktree 目录；别用 .git 是否是目录做判断。
### Step 2

无 Git：注入“当前项目未受 Git 管理”上下文，询问初始化或暂不启用，不执行 git init。暂不启用则记住会话决定。
### Step 3

插件有 PLUGIN_DATA 时通过 context --choice defer --apply 记住决定；它不是未来 Git 初始化授权。状态变化重新发现。
### Step 4

空历史：可推荐团队 classic-gitflow 默认，先预览规范文件与本地快照；初始提交和分支创建分开授权。
### Step 5

已有历史：读取既有约定；明确选定 profile 或现有 JSON 后接入，不重写名称、远端、历史或用户修改。
### Step 6

初始化前列出预计 `.gitflow/` 文件、Git 定位配置与本地排除项；共享定义便于版本化，`.gitflow/state/` 保存不提交的本机状态，本地模式明确不随 clone 传播。
### Step 7

明确授权后才 initialize-git/apply；重新发现，验证没有伪造初始提交；读取缺失长期角色，执行只读审计，再按独立授权 reconcile。已有生效约定幂等复用，不用 init 替换。

## 独立工具与插件路径

先定位本技能 scripts/inspect_repository.py，按 [契约](references/contract.md) 中的命令读取状态。Python 3.11+ 标准库，只读且不初始化。实际命令使用当前技能所在目录；挂载示例为：

```bash
python3 /mnt/skills/user/git-init/scripts/inspect_repository.py /absolute/project
```

GitFlow 插件可用时调用其实际路径对应命令，详见 [操作样例](references/action.md)。不得把未安装的 CLI 名称当已存在命令。

## v2 治理补充

只有真实 Git 工作树才自动触发；新规则与组织导入都先预览，导入不等于激活，初始化后用 doctor 检查接线事实。 细节见本技能 references/contract.md。

## 验证与输出

插件 init 示例见 references/action.md。无插件先用 git init 的预览计划让用户审阅，按实际授权执行，绝不冒充 activation 已建立。

输出必须区分：事实、规则来源、建议、用户授权和未验证项。写操作后核对当前 refs/HEAD/status；计划和预览不是完成证据。安全边界：不泄露凭据，不上传工作树；不在日志暴露凭据、整段工作树内容或敏感远端 URL。

## 正例

子目录在父仓 main 下：绑定父仓，输出当前规则；独立空目录用户选暂不启用则继续保留此上下文。

## 反例

在每个子目录 git init，或者将“可以考虑 Git”理解为已授权初始化和创建分支。

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

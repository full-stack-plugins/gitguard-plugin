---
name: git-recovery
description: 在提交错分支、创建错基线、冲突、中断 merge/rebase/cherry-pick 或操作超时需要恢复时使用；先诊断，保留原引用与修改。
---

# 诊断与保留式恢复

## 什么时候使用与不适用

本技能不适用于代替 CodeGuard 质量、平台保护或部署验收。它可单独安装；没有 GitFlow 插件时，使用只读 Git 观察与逐条规则核验。不会依赖相邻技能文件或假定宿主自动加载其他技能。

## 前置条件与授权

- Git 可用，项目目录明确。先确认父仓真实根与项目指令，保留用户修改。
- 既有规范优先；无 Git、无规范、detached、浅历史与未知来源需要明确报告。
- 只读观察和预览可执行；Git 初始化、分支创建/切换、提交、推送、集成、清理、安装 Hook 与规则激活按用户已有授权范围执行。
- [项目规则与证据](references/contract.md) 是本技能自包含参考；[权威目录](references/workflows.md) 用于模型与来源核验。

## 执行步骤

### Step 1

只读诊断 HEAD、branch、status、中断标志与逐步日志；超时状态记 unknown，不立刻重试写操作。
### Step 2

未提交修改在兼容目标上可 switch 携带；Git 拒绝覆盖时保留现场，不自动 reset、checkout -- 或 stash drop。
### Step 3

错分支提交先确定完整 OID 与正确任务分支，保留原分支引用，再 cherry-pick 单父提交；不自动删除错误分支历史。
### Step 4

错基线先核对创建记录、公开 refs 与团队契约；已经公开或证据不足时提出新正确分支迁移方案，不强行 rebase。
### Step 5

中断操作唯一识别为 merge/rebase/cherry-pick/revert；abort/continue 明确授权，continue 前冲突已解决且暂存。
### Step 6

resume 读取日志与实际状态，识别已完成步骤，不盲目重放提交。等价补丁核验防重复，目标不明确返回未验证。
### Step 7

恢复后报告原引用保留、目标 OID、dirty 与剩余回灌，不以没有冲突标志当作代码正确。

## 独立工具与插件路径

先定位本技能 scripts/inspect_repository.py，按 [契约](references/contract.md) 中的命令读取状态。Python 3.11+ 标准库，只读且不初始化。实际命令使用当前技能所在目录；挂载示例为：

```bash
python3 /mnt/skills/user/git-recovery/scripts/inspect_repository.py /absolute/project
```

GitFlow 插件可用时调用其实际路径对应命令，详见 [操作样例](references/action.md)。不得把未安装的 CLI 名称当已存在命令。

## v2 治理补充

元数据门禁拒绝 merge commit 时保留 MERGE_HEAD 与日志；核对状态后修正候选消息再继续，不重复 merge 或清空现场。 细节见本技能 references/contract.md。

## 验证与输出

插件 resume 是观察和恢复建议，不自动重放 unknown 命令。冲突解法必须结合当前文件与业务行为核验。

输出必须区分：事实、规则来源、建议、用户授权和未验证项。写操作后核对当前 refs/HEAD/status；计划和预览不是完成证据。安全边界：不泄露凭据，不上传工作树；不在日志暴露凭据、整段工作树内容或敏感远端 URL。

## 正例

feature/wrong 的单父提交复制到 feature/right，原引用保持不变；明确后续错误分支处理需另授权。

## 反例

reset --hard 清掉用户修改、强推重写别人历史，或网络超时后重复 cherry-pick。

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

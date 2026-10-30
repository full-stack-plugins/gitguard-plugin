---
name: git-sync
description: 在需要按项目策略 fetch、pull、push、merge 或 rebase，确认源目标分支与远端映射时使用；不猜测上游、不强推。
---

# 同步与集成

## 什么时候使用与不适用

本技能不适用于代替 CodeGuard 质量、平台保护或部署验收。它可单独安装；没有 GitFlow 插件时，使用只读 Git 观察与逐条规则核验。不会依赖相邻技能文件或假定宿主自动加载其他技能。

## 前置条件与授权

- Git 可用，项目目录明确。先确认父仓真实根与项目指令，保留用户修改。
- 既有规范优先；无 Git、无规范、detached、浅历史与未知来源需要明确报告。
- 只读观察和预览可执行；Git 初始化、分支创建/切换、提交、推送、集成、清理、安装 Hook 与规则激活按用户已有授权范围执行。
- [项目规则与证据](references/contract.md) 是本技能自包含参考；[权威目录](references/workflows.md) 用于模型与来源核验。

## 执行步骤

### Step 1

读取已激活策略，发现当前仓库/分支/HEAD 与远端名称；避免输出含凭据的 URL。
### Step 2

明确动作、单一 source/target/ref、remote 与合并方式。Fork 模式分别确认个人 origin 与权威 upstream，名称本身不授权推送。
### Step 3

fetch 也修改跟踪 refs，默认预览；pull 明确来源后 fetch+ff-only，非快进交给显式集成方案。
### Step 4

merge 检查来源 merge_into 包含当前目标角色；rebase 检查 create_from，拒绝重写已有远端引用包含的提交。
### Step 5

push 限定同名映射与单一分支；强推、删除、mirror、多 ref 操作不自动放行，需要单独方案。
### Step 6

得到范围内授权后执行；前后记录 Git 身份。网络超时可能已发生远端副作用，查询实际 ref 再决定恢复。
### Step 7

冲突保留现场，给出实际分支与中断标记。清楚区分本地 refs、ls-remote 观察、CI 和生产。

## 独立工具与插件路径

先定位本技能 scripts/inspect_repository.py，按 [契约](references/contract.md) 中的命令读取状态。Python 3.11+ 标准库，只读且不初始化。实际命令使用当前技能所在目录；挂载示例为：

```bash
python3 /mnt/skills/user/git-sync/scripts/inspect_repository.py /absolute/project
```

GitFlow 插件可用时调用其实际路径对应命令，详见 [操作样例](references/action.md)。不得把未安装的 CLI 名称当已存在命令。

## v2 治理补充

集成提交也检查元数据和绑定日志；CI 不自动 fetch，不执行 PR 中脚本，浅历史需由获授权的接入步骤补齐。 细节见本技能 references/contract.md。

## 验证与输出

拉取默认 ff-only；squash 需独立提交审阅，首版插件拒绝自动 squash 集成而不是造一个批准。

输出必须区分：事实、规则来源、建议、用户授权和未验证项。写操作后核对当前 refs/HEAD/status；计划和预览不是完成证据。安全边界：不泄露凭据，不上传工作树；不在日志暴露凭据、整段工作树内容或敏感远端 URL。

## 正例

feature 合入 develop：切到 develop 后明确来源，预览再 merge；push origin develop 单独授权。

## 反例

省略目标后按不可信 upstream 自动 push，或以 --force-with-lease 当作默认安全同步。

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

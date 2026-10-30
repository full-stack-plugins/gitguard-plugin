---
name: git-audit
description: 在审计仓库分支覆盖、命名、流转关系、保护要求、来源证据或规范漂移时使用；审计只读，未知与违规分别报告。
---

# 分支与规范审计

## 什么时候使用与不适用

本技能不适用于代替 CodeGuard 质量、平台保护或部署验收。它可单独安装；没有 GitFlow 插件时，使用只读 Git 观察与逐条规则核验。不会依赖相邻技能文件或假定宿主自动加载其他技能。

## 前置条件与授权

- Git 可用，项目目录明确。先确认父仓真实根与项目指令，保留用户修改。
- 既有规范优先；无 Git、无规范、detached、浅历史与未知来源需要明确报告。
- 只读观察和预览可执行；Git 初始化、分支创建/切换、提交、推送、集成、清理、安装 Hook 与规则激活按用户已有授权范围执行。
- [项目规则与证据](references/contract.md) 是本技能自包含参考；[权威目录](references/workflows.md) 用于模型与来源核验。

## 执行步骤

### Step 1

发现真实根和状态，加载定义与激活修订；候选漂移先报告，不能自动生效。
### Step 2

按模型检查必需长期固定角色；临时类型仅检查已有实例，不因为没有 feature/release/hotfix 报缺失。
### Step 3

逐分支检验 Git 名称与角色，检测多角色匹配、未识别命名和固定名称冲突。
### Step 4

检查 provenance、记录来源 OID 与操作日志；没有来源记录为 unknown，浅历史注明限制。
### Step 5

检查 dirty、detached、merge/rebase/cherry-pick 中断；不用合并关系取代命名与来源检查。
### Step 6

本地跟踪与服务端事实分开；保护规则存在于 JSON 不证明 GitHub/GitLab 已阻止直推。
### Step 7

输出违规、未知、明确通过与最小修复建议。修改分支/激活规范须独立授权，不在审计中修复。

## 独立工具与插件路径

先定位本技能 scripts/inspect_repository.py，按 [契约](references/contract.md) 中的命令读取状态。Python 3.11+ 标准库，只读且不初始化。实际命令使用当前技能所在目录；挂载示例为：

```bash
python3 /mnt/skills/user/git-audit/scripts/inspect_repository.py /absolute/project
```

GitFlow 插件可用时调用其实际路径对应命令，详见 [操作样例](references/action.md)。不得把未安装的 CLI 名称当已存在命令。

## v2 治理补充

用 policy describe 解释项目/组织/快照来源，用 doctor 区分 missing/configured/unverified；PR 审计使用受信 base 的完整范围。 细节见本技能 references/contract.md。

## 验证与输出

报告应携带仓库身份、规则修订和证据层级。CodeGraph 或静态关系不能代替 Git 状态与真实服务保护。

输出必须区分：事实、规则来源、建议、用户授权和未验证项。写操作后核对当前 refs/HEAD/status；计划和预览不是完成证据。安全边界：不泄露凭据，不上传工作树；不在日志暴露凭据、整段工作树内容或敏感远端 URL。

## 正例

classic 仅 main+develop 的空闲项目覆盖通过；人工 feature 分支缺来源记录另列未知。

## 反例

把无临时分支当失败，或者在没有访问远端保护 API 时声称分支受平台保护。

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

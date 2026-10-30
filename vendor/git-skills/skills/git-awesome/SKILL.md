---
name: git-awesome
description: 在需要查找权威 Git 工作流、比较 GitFlow/GitHub/GitLab/主干/维护者模型、解释术语或追踪来源时使用；不自动修改仓库。
---

# 权威资料导航与比较

## 什么时候使用与不适用

本技能不适用于代替 CodeGuard 质量、平台保护或部署验收。它可单独安装；没有 GitFlow 插件时，使用只读 Git 观察与逐条规则核验。不会依赖相邻技能文件或假定宿主自动加载其他技能。

## 前置条件与授权

- Git 可用，项目目录明确。先确认父仓真实根与项目指令，保留用户修改。
- 既有规范优先；无 Git、无规范、detached、浅历史与未知来源需要明确报告。
- 只读观察和预览可执行；Git 初始化、分支创建/切换、提交、推送、集成、清理、安装 Hook 与规则激活按用户已有授权范围执行。
- [项目规则与证据](references/contract.md) 是本技能自包含参考；[权威目录](references/workflows.md) 用于模型与来源核验。

## 执行步骤

### Step 1

明确要比较的发布周期、维护版本、团队人数、部署方式与贡献者权限，不先假定需要 develop。
### Step 2

读取本技能工作流目录，优先原作者、Git 官方、平台官方和 DORA；第三方 awesome 列表只是入口。
### Step 3

打开与问题相关的一手来源，记录 URL、出版者、检查日期和相关主张；链接失效时报告快照日期。
### Step 4

分开官方模型、模板选择和项目扩展。明确 main/master 重命名与 feature/ 前缀属于项目约定。
### Step 5

比较分支角色、创建基线、传播方向、短期/长期生命周期、版本维护和协作远端，输出选择依据。
### Step 6

提出模型建议后核对当前项目既有规范，交给工作流选型；本技能不激活、不写入。

## 独立工具与插件路径

先定位本技能 scripts/inspect_repository.py，按 [契约](references/contract.md) 中的命令读取状态。Python 3.11+ 标准库，只读且不初始化。实际命令使用当前技能所在目录；挂载示例为：

```bash
python3 /mnt/skills/user/git-awesome/scripts/inspect_repository.py /absolute/project
```

GitFlow 插件可用时调用其实际路径对应命令，详见 [操作样例](references/action.md)。不得把未安装的 CLI 名称当已存在命令。

## v2 治理补充

比较资料时区分已验证功能与宣传；Commit Check 的统一规则与多入口可作参考，GitFlow 仍管理分支生命周期。 细节见本技能 references/contract.md。

## 验证与输出

输出来源表、比较表、适用条件与未核实问题。不要使用“官方 Git 标准要求 GitFlow”的说法。

输出必须区分：事实、规则来源、建议、用户授权和未验证项。写操作后核对当前 refs/HEAD/status；计划和预览不是完成证据。安全边界：不泄露凭据，不上传工作树；不在日志暴露凭据、整段工作树内容或敏感远端 URL。

## 正例

比较一个月发布一次、同时维护两个版本的库与每天部署的服务；前者评估 Classic Git Flow，后者评估 GitHub Flow/主干开发。

## 反例

将来源汇总成“所有项目必须有 develop、release、hotfix”；或把 Microsoft 和 Git maintainer 修复方向混在同一规则。

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

---
name: git-workflow
description: 在项目需要选择 Git 工作流、解释既有分支约定、将团队规则形成可审查项目契约或修订规范时使用；已有规则优先。
---

# 工作流识别、选择与定义

## 什么时候使用与不适用

本技能不适用于代替 CodeGuard 质量、平台保护或部署验收。它可单独安装；没有 GitFlow 插件时，使用只读 Git 观察与逐条规则核验。不会依赖相邻技能文件或假定宿主自动加载其他技能。

## 前置条件与授权

- Git 可用，项目目录明确。先确认父仓真实根与项目指令，保留用户修改。
- 既有规范优先；无 Git、无规范、detached、浅历史与未知来源需要明确报告。
- 只读观察和预览可执行；Git 初始化、分支创建/切换、提交、推送、集成、清理、安装 Hook 与规则激活按用户已有授权范围执行。
- [项目规则与证据](references/contract.md) 是本技能自包含参考；[权威目录](references/workflows.md) 用于模型与来源核验。

## 执行步骤

### Step 1

先运行只读发现，读取已有贡献与发布规范；区分空仓、已有历史、团队既定规范。
### Step 2

询问实质影响选型的发布方式、版本维护和 PR/直接提交政策；可推断常规命名需注明假设。
### Step 3

依据权威目录选择一个分支模型，再单独确定 shared/fork 协作映射；不能机械拼接所有模型。
### Step 4

形成候选 JSON：角色固定 name 或 pattern、required、allow_commit、create_from、merge_into，主远端和合并/消息策略。
### Step 5

阅读本技能内 profiles 模板；模板主线默认 main，保护策略和前缀为项目扩展，按确认契约调整。
### Step 6

给出旧规则到新规则的差异与已有分支不兼容项，优先保留历史并规划接入，不静默迁移。
### Step 7

插件可用时 init/activate 默认预览；当前用户明确授权后激活，再 audit 与 gate。无插件时说明候选尚未激活。

## 独立工具与插件路径

先定位本技能 scripts/inspect_repository.py，按 [契约](references/contract.md) 中的命令读取状态。Python 3.11+ 标准库，只读且不初始化。实际命令使用当前技能所在目录；挂载示例为：

```bash
python3 /mnt/skills/user/git-workflow/scripts/inspect_repository.py /absolute/project
```

GitFlow 插件可用时调用其实际路径对应命令，详见 [操作样例](references/action.md)。不得把未安装的 CLI 名称当已存在命令。

## v2 治理补充

保留 v1 项目约定；确需 v2 时明确 rules/extends、warning 迁移策略、锁定组织项及激活修订，不默认开启全部规则。 细节见本技能 references/contract.md。

## 验证与输出

输出候选规则、来源、差异、适用场景、例外与授权边界。profile JSON 的闭合字段见本技能 references/policy.md。

输出必须区分：事实、规则来源、建议、用户授权和未验证项。写操作后核对当前 refs/HEAD/status；计划和预览不是完成证据。安全边界：不泄露凭据，不上传工作树；不在日志暴露凭据、整段工作树内容或敏感远端 URL。

## 正例

已有 main+feature 团队选 github-flow，记录无需 develop；在候选中选择消息格式，再审阅激活。

## 反例

在有 GitHub Flow 历史的项目里默认切到 develop，或直接编辑 allow_commit 后声称已放行。

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

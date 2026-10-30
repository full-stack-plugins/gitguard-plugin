# 项目规则、授权与证据契约

## 规则事实源

先读项目 AGENTS.md/CLAUDE.md/CONTRIBUTING、发布文档与已有 Git 约定。规范不得由远端默认分支或名字推断。共享模式 `.gitflow/workflow.json` 是定义；生成的 workflow.md 只是说明。插件在项目根 `.gitflow/state/activation.json` 保存已确认快照，`origins.json` 保存创建来源，`worktrees/<id>/journal.json` 隔离各工作树日志。多个 worktree 共用锚定项目的 state/；Git 本地配置只保存定位信息，info/exclude 排除 state/。候选修订须预览并显式激活，编辑候选不会立即放宽门禁。local 模式仅写 `.gitflow/state/`，不写共享定义，不随 clone 分发。旧 Git 元数据中的 gitflow/ 只读兼容，显式 apply 时迁移并保留备份；冲突或自定义 Hook 不能自动覆盖。

没有安装插件时依本文步骤读取、解释并人工逐条核验；不要声称插件门禁或已激活快照存在。仅有文档允许提出候选规则，不自动授权初始化、创建/切换分支、合并、提交、推送、清理或发布。用户已有明确授权持续有效；新的影响需明确范围。

## 独立可执行发现

本技能包含只读脚本 inspect_repository.py，无第三方依赖。在支持技能挂载的环境执行：

```bash
python3 /mnt/skills/user/git-init/scripts/inspect_repository.py /absolute/project
```

其他安装方式应以当前技能实际目录定位脚本，不虚构上述挂载存在。也可直接查询：

```bash
git -C /absolute/project rev-parse --show-toplevel
git -C /absolute/project rev-parse --absolute-git-dir
git -C /absolute/project rev-parse --path-format=absolute --git-common-dir
git -C /absolute/project symbolic-ref --quiet --short HEAD
git -C /absolute/project status --porcelain=v1
git -C /absolute/project for-each-ref --format='%(refname:short)' refs/heads
```

路径是参数，不拼接 shell 字符串；实际命令必须使用用户项目绝对路径。脚本不 fetch、不建立索引、不写配置、不初始化、不提交。Git 命令不存在、权限失败、损坏元数据、bare 仓库或超时返回未验证，不能当空项目。

## 判定与失败

允许（allow）表示本动作分支规则通过；deny 表示明确违反；unverified 表示缺少身份、历史、授权范围或可信规则。未知不会自动降为成功。CodeGuard 质量验收是另一项独立检查。

真实仓库根可在当前目录之上；linked worktree 的 `.git` 为文件。不能在子目录重复 init。空历史无法预先创建多个有效分支；先确认初始提交，再补长期角色。临时 feature/release/hotfix 不要求总是存在。merge-base 不证明分支创建来源；没有 provenance 应报告未知。远端跟踪不等于实时远端，浅历史不能证明完整合入。服务端保护须独立核实。

任何写动作先输出具体计划：仓库、当前 branch/HEAD、来源/目标 refs、规则修订、保留修改方式、预计命令及验收。执行后重新读取 refs/HEAD/status；出现冲突留在实际中断现场，不虚称原分支已恢复，不自动 reset --hard、强推、stash drop。副作用超时可能已发生，先观察再恢复，不重复 cherry-pick 或发布。

## 插件可用时

从当前插件实际目录调用 `python3 <plugin-root>/scripts/gitflow.py <command> <project> --json`；默认预览，受管写操作显式 `--apply`。插件位置需由宿主或用户提供，本技能不依赖插件安装。

退出码：0 本动作允许/预览/完成；1 违规；2 用法错误；3 未验证；4 内部错误。不要将预览或退出码 0 扩大为整体 Git 规范、CI、部署或生产验收。

## v2 元数据、CI 与组织规则（GitFlow 0.2.0）

既有 workflow 1.0.0 保持兼容，不强制新增格式检查。workflow 2.0.0 在完整定义中增加 rules 与 extends（无继承为 null），规则按稳定编号配置 severity=off/warn/error 和闭合 options。GF001 提交格式、GF002 标题长度、GF101 作者名、GF102 邮箱、GF103 作者 Signed-off-by、GF104 AI 声明、GF401 标签。未配置为 off；未知规则/参数、缺元数据或配置损坏不是通过。分支保护、来源和合并方向不能用 off 关闭。

每条检查返回 rule_id、severity、status、actual、expected、message、suggestion、fix。warning 的明确失败可以继续，但 unverified 不能当成功。fix 仅建议：可确定的类型大小写能修正，不猜测语义、不伪造作者、不自动 amend。Signed-off-by 不是密码学签名；AI 声明检查不检测代码来源，disclose 使用 Assisted-by。

插件可用时：policy --operation describe 解释有效规则与来源；doctor 只读观察原生 Hook/CI 线索，宿主 MCP 和服务端保护仍需真实验证；check --base FULL_BASE_OID --head FULL_HEAD_OID --source SOURCE --target TARGET 检查 base..head 全部提交。squash 需明确候选 --message 或 --message-file，仍检查每个提交的作者。浅历史、缺对象、超过500条、缺受信 base 定义均未验证；不能只看最后提交。CI 从 base 提交读取定义和组织文件，不执行 PR 项目脚本，不采用 head 的放宽规则。

组织基线为 .gitflow/baselines/NAME.json 加预期 SHA-256；仅含 schema_version=1.0.0、rules、locked_rules，不递归继承。organization --source FILE_OR_HTTPS --name NAME --sha256 DIGEST 默认只预览，显式 --apply 才导入，不能覆盖不同已有文件或自动激活。项目按规则整项覆盖未锁定项；锁定项不可放宽。缺失、链接、摘要变化都未验证。规则及组织快照需提交进业务仓库，.gitflow/state 仍为本机状态。

业务 PR Action 和完整配置见 https://github.com/full-stack-plugins/gitflow-plugin/blob/main/docs/governance.md 。仅在实际安装插件时调用上述命令；独立技能按同一契约逐项核验，不声称有确定性运行时或服务端阻断。

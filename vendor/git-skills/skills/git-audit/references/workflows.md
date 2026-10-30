# 权威工作流目录

核验：2026-10-07。这里是来源导航与中文摘要；打开原文确认当前版本，项目既有约定优先，未经授权不迁移。

| 模型 | 权威来源 | 适用场景 | 注意事项 |
|---|---|---|---|
| classic-gitflow | [Vincent Driessen](https://nvie.com/posts/a-successful-git-branching-model/) | 分期发布与多版本软件；main/develop 长期存在，任务、发布、修复分支按需创建。 | 持续交付团队先比较简化模型；原作者 2020 反思不主张所有产品采用。 |
| github-flow | [GitHub Docs](https://docs.github.com/en/get-started/using-github/github-flow) | main 与短期任务分支，审查后集成；无需 develop。 | 本文模板采用 feature/ 前缀是项目约定，官方没有强制该前缀。 |
| gitlab-environment | [GitLab](https://about.gitlab.com/topics/version-control/what-is-gitlab-flow/) | main 后向 staging/production 推进的环境变体。 | 环境分支不是所有 GitLab 项目的必需项；上线时仍需单独部署验证。 |
| gitlab-release | [GitLab Docs](https://docs.gitlab.com/user/project/repository/branches/strategies/) | 主线加版本稳定分支；选择性修复传播。 | stable/ 命名与禁止直接提交为模板扩展，团队应确认。 |
| trunk-based | [DORA](https://dora.dev/capabilities/trunk-based-development/) | 小批变更、高频主干集成，短期分支寿命通常小于一天。 | 模板是受审查短分支变体；分支数与寿命目标不是已实现的自动度量。 |
| microsoft-release | [Microsoft Azure DevOps](https://devblogs.microsoft.com/devops/release-flow-how-we-do-branching-on-the-vsts-team/) | 在主线修复，再选择性 cherry-pick 到版本发布分支。 | 不要与 Git 维护者 oldest-first 合并方向混用。 |
| git-maintainer | [Git Project](https://git-scm.com/docs/gitworkflows) | maint/main/next/seen 的稳定层级；修复先在最老适用维护线，向上 merge。 | 模板把上游 master 映射 main；集成分支不能自动当发布线。 |
| centralized | [Pro Git](https://git-scm.com/book/en/v2/Distributed-Git-Distributed-Workflows) | 共享主线、集中协作；可直接在项目指定主线提交。 | 直接提交是明确选型，不是其他模型的隐含例外。 |
| fork | [Atlassian Git Tutorials](https://www.atlassian.com/git/tutorials/comparing-workflows/forking-workflow) | 贡献者写自己的远端，维护者负责上游集成。 | Fork 是协作/远端模式，可与不同分支模型组合，不能代替合入方向。 |

## 分清模型与项目扩展

Classic Git Flow 的 feature 从 develop 起，release 从 develop 起并回到 main/develop，hotfix 从 main 起并回到 main/develop。活跃 release 存在时 hotfix 还需进入该发布线。命名前缀、main 代替 master、提交消息格式、保护权限均需记录为项目选择。

GitHub Flow 不要求 develop；GitLab 环境/版本两种变体分别确认，不默认创建 staging 和 production。主干开发的短寿命与频繁集成是协作实践，不能只看命名宣称采用成功。Microsoft Release Flow 主线优先后 cherry-pick；Git 维护者修复从最老适用分支开始，向更不稳定层级传播，不能统一写“主线永远优先”。

Fork 模式单独确定 origin/upstream 等映射；远端名称不是可信 URL 的证明。服务端保护、审批与 CI 必须在宿主另行核验。

## Git 行为一手参考

- [仓库布局](https://git-scm.com/docs/gitrepository-layout)：.git 可能是指针文件，common-dir 与 worktree-dir 不相同。
- [worktree](https://git-scm.com/docs/git-worktree)：同一分支通常不能同时检出到多个工作树。
- [分支名称](https://git-scm.com/docs/git-check-ref-format)：项目模式和 Git 自身合法性都要通过。
- [merge](https://git-scm.com/docs/git-merge)、[rebase](https://git-scm.com/docs/git-rebase)、[push](https://git-scm.com/docs/git-push)：冲突、中断、非快进与远端事实分别核验。

来源冲突时说明差异与团队目标，不以多个教程“多数投票”覆盖项目契约。网络失效时仅引用已核验快照，标明日期与限制。

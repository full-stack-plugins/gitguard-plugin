# GitGuard 技能名称迁移

用户可见入口统一为 gitguard-*，不改原生 git 命令、仓库名 git-skills、内部 gitflow 模块、XML文件名或CLI子命令。没有提供旧别名，以免宿主继续显示错误命名；旧提示词和会话需切换到新名称并重新加载本地候选包。

| 旧名称 | 当前候选名称 |
|---|---|
| git-awesome | gitguard-awesome |
| git-workflow | gitguard-workflow |
| git-init | gitguard-init |
| git-branch | gitguard-branch |
| git-audit | gitguard-audit |
| git-commit | gitguard-commit |
| git-sync | gitguard-sync |
| git-release | gitguard-release |
| git-recovery | gitguard-recovery |

技能事实源仍为 full-stack-skills/git-skills；先修改源包，再通过 scripts/vendor_skills.py 同步并重锁90个文件。SKILL frontmatter、目录、agents/openai.yaml显示名/默认提示、独立挂载路径、技能交接和插件入口提示同步。历史证据及归档规格不重写。

当前技能提示明确XML唯一权威、install拥有AGENTS、init仅选择GitFlow/初始化XML；兼容旧JSON资料不是当前授权或规则来源。原生Git操作及Hook覆盖边界不变。现有Rust安装引导未使用旧九技能名称，原本的gitguard-policy-check入口已符合前缀，不为改名修改引擎或共享GuardEngine。

候选仅本地验证，未推送、合main或发版。后续先发布/推送审阅技能源包，再发布包含该锁定快照的gitguard-plugin；使用者重新加载/安装插件，避免宿主缓存旧目录。不能声称旧远端tag已含新入口。

## 本地验收

2026-10-30 Linux：完整 unittest 249 项（232 通过，17 项需要真实 Windows cmd/Job Objects/junction/rename sharing）；名称专项3项通过；源技能验证9项无错误；源包与插件快照90文件一致。真实Rust安装/init顺序8项通过，配套安装11项中10通过，1项因需要全部六守卫工具跳过。离线ZIP解包后包校验通过。独立审查发现的旧JSON当前流程冲突已修正并复核。

源技能提交 `6e3b61b9fd25878b4dd62bc16f1c23aaeb04904b`。当前环境无 openspec、quick_validate、TRACE 命令，因此没有声称这些检查通过。Windows/macOS及真实Agent加载未在本轮运行；不代表生产就绪。

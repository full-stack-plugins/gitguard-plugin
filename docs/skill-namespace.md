# 技能源与 GitGuard 插件职责

本轮候选纠正此前将通用九技能机械改为 gitguard-* 的范围错误。

- git-skills 恢复 git-awesome、git-workflow、git-init、git-branch、git-audit、git-commit、git-sync、git-release、git-recovery，保持独立通用技能。
- GitGuard 仅注册插件专属 gitguard-init；先前九个 gitguard-* 注册入口不作为本轮产品合同保留。已有 CLI 能力未删除。
- skills/gitguard-init 由插件维护，调用实际插件启动器的 init。通用源在 vendor/git-skills/ 保留原始字节，非宿主注册目录；不对通用源做名称映射或注入插件规则。
- skills.lock.json v2 分别记录 source_commit、90个原始 source_files 与101个包内 files。后者包括专属技能、原始快照及运行时模板。vendor --check 校验包内摘要、原始快照和运行时模板一致性；带 --source 还校验上游内容。生成器不覆盖插件专属技能。
- profiles/ 和 sources.json 保持原始源字节。原生 Git 命令、内部 gitflow/XML、兼容 CLI 不改名。

## 使用

先核对 gitguard 来自本插件的 CLI 启动器，而非同名 Rust 项目安装器：

```bash
gitguard init PROJECT --profile github-flow --json
gitguard init PROJECT --profile github-flow --apply --json
```

交互终端可用 gitguard init PROJECT 选择八预设；Agent 非交互调用必须明确 profile。普通仓库写 .git/gitflow.xml，linked worktree 使用 common-dir；init 不读改 AGENTS.md。Rust项目 install 管理 AGENTS 引导，插件启动器 install --bin-dir 只安装命令。均不代表自动守护已启用。

## 复用与待定范围

现有 audit、status、doctor 可做只读检查和接线诊断，gate 可供已有提交/推送检查链复用。它们继续是 CLI，尚未新建专属技能。是否新增 gitguard-check 或 gitguard-doctor 等入口及交互范围需用户确定，不把兼容 branch/sync/release 包装当主流程。

## 发布边界

本轮仅本地修正，涉及 git-skills 和 gitguard-plugin；未推送、合main或发布。旧远端仍有九技能改名，不能将本地候选说成已发布。真实 Agent 宿主自动发现/触发尚未验收。

## 本地验证记录（2026-10-30）

源仓恢复提交：fdda88a8f1fd800cf371e02996a4aed752a7732f；内容与恢复前原通用基线 f3ef639 完全一致，9技能校验通过。插件完整 unittest 254 项：237通过，17真实Windows依赖项跳过，无失败。实际安装后的CLI init预览/应用/重复与AGENTS不变回归通过；Rust安装/init顺序8项通过。ZIP解包后仅注册gitguard-init，9通用技能在vendor目录；包校验和101文件锁校验通过。来源commit内容、篡改、符号链接输出拒绝、重复生成都有回归；独立审查通过。

未安装或运行缺失的 openspec/quick_validate/TRACE；本轮未运行远端CI、Windows/macOS或真实Agent宿主，不将历史CI结果当作当前候选验收。

# GitGuard（分支规范防护）

GitGuard 依据一份本地 XML 规则，检查分支名称、提交权限、合并方向及已配置的提交元数据。显式初始化并核实接线后，继续使用普通 Git 命令。

[English](README.md) · [详细用法与安全边界](docs/xml-native-guard.md) · [XML 契约](openspec/changes/xml-native-guard/specs/xml-native-guard/spec.md)

## 在已有仓库中开始

安装后的命令为 `gitguard`；在源码目录可用 `python3 scripts/gitflow.py` 加相同参数。

```bash
gitguard init . --profile github-flow       # 预览，不写文件
gitguard init . --profile github-flow --apply
gitguard hooks .                           # 预览原生 Hook 安装
gitguard hooks . --apply                   # 明确安装到当前仓库
gitguard doctor .
gitguard status .
gitguard audit .
git switch -c feature/example
# 编辑并暂存文件，包括生成的 AGENTS.md 引导
git commit -m "feat: add example"
```

请按项目约定选择模板。八个初始化模板是：`centralized`、`classic-gitflow`、`git-maintainer`、`gitlab-environment`、`gitlab-release`、`github-flow`、`microsoft-release`、`trunk-based`。模板不是运行时规则来源。非交互初始化必须提供 `--profile`；未建立 Git 仓库时，还须明确传入 `--initialize-git`。

初始化写入 `<git-common-dir>/gitflow.xml`，并在项目 `AGENTS.md` 中维护一个引导块，保留块外内容。关联 worktree 共用 XML，但检查各自的 Git 状态。独立 clone 必须重新明确初始化；Git 克隆不会传输该元数据规则。

## 接线与覆盖范围

[已声明的 Agent hooks](hooks/hooks.json) 使用 Claude 协议，`PreToolUse` 匹配 `Bash`。可明确解析的普通原生 merge 会在执行前，依据实际本地引用检查方向；动态、歧义或不支持的命令进入 ask／未验证状态。这不表示所有终端、IDE 命令均被拦截，也未声明 Codex hook 接线或修改其登录、信任设置。

显式安装的 Git `commit-msg`、`pre-push` 提供补充检查；已有自定义 hook 和管理器不会被自动覆盖。`doctor` 报告实际接线和不确定性；缺少 hook 时返回未验证。快进合并、`--no-commit`、`--no-verify`、第三方 Git 库及宿主集成存在覆盖边界，详见[使用指南](docs/xml-native-guard.md#integration-boundaries)。

公共 CI `check` 尚未配置可信 XML 分发通道，因此不会用 PR 自带 XML 或旧 JSON 放行。内部范围计算内核不等于远端强制保护。

## 从旧配置迁移

运行时只加载 XML，不回退到 JSON。先审查旧定义或激活快照，再明确迁移：

```bash
gitguard policy . --operation migrate
gitguard policy . --operation migrate --apply
```

迁移保留旧文件，校验组织引用、摘要与锁定规则，并将解析后的规则展开到 XML。已有 XML 时拒绝迁移覆盖。旧 `branch`、`sync`、`release`、`recovery` 和 activation 入口保留为兼容接口，新用户主路径使用普通 Git。Rust 适配器继续调用相同的 Python 规则加载实现；本轮已本地重建未改动的 Rust 源码，并验证 XML CLI/MCP 配套。打包 `skills/` 保留冻结的兼容引导。

## 本地验证

运行时为 Python 3.11+ 标准库。源码目录执行：

```bash
python3 tests/run_isolated.py
python3 scripts/validate_package.py
```

单元测试和隔离仓库回放不等于真实宿主安装验收，不代表生产就绪，也未证明当前 macOS／Windows 平台验收。本说明不表示已在真实仓库安装 Hook、运行远端 CI、推送或发布。

[当前 XML 设计](openspec/changes/xml-native-guard/design.md)和[使用指南](docs/xml-native-guard.md)取代旧 `docs/`、`product-docs/` 中冲突的 JSON 运行时说明。

许可证：[Apache-2.0](LICENSE)。

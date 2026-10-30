---
name: gitguard-init
description: 选择 GitGuard 工作流并预览或初始化 gitflow.xml；不安装项目引导或自动启用 Hook。
---

# 初始化 GitGuard 工作流

这是 GitGuard 插件专属技能，不是通用 git-init 的别名，不替代 Git 客户端。

## 前置条件与授权

确认项目路径和真实 Git common-dir，保留现有文件。先定位本插件实际安装目录；使用本插件 `bin/gitguard`（POSIX）或已安装且确认指向本插件的 `gitguard` 启动器。不要误用同名 Rust 项目安装器，它不提供此 init 入口。Windows 使用本插件安装器生成的 `gitguard.cmd`，未安装时可用 `python <plugin-root>/scripts/gitflow.py` 执行相同参数。不虚构可用命令，不自动安装。

## 执行步骤

1. 通过 `gitguard discover PROJECT --json` 只读确认仓库。先核对该命令来自本插件；没有 Git 元数据时不擅自创建。
2. 交互终端可运行 `gitguard init PROJECT` 选择预设并预览；非交互 Agent 必须请用户选择或沿用已明确选择的 `--profile`。
3. 八预设为 centralized、classic-gitflow、git-maintainer、gitlab-environment、gitlab-release、github-flow、microsoft-release、trunk-based。不替用户默认选经典 GitFlow。
4. 先预览：`gitguard init PROJECT --profile github-flow --json`。仅按用户明确授权追加 `--apply`。需要新建 Git 仓库时另需明确授权 `--initialize-git`。
5. 初始化后执行 `gitguard status PROJECT --json` 和 `gitguard doctor PROJECT --json`，分别报告策略状态和接线状态；不得把 XML 创建成功等同自动守护已启用。

实际路径示例（把占位路径换为已核实位置）：

```bash
/absolute/gitguard-plugin/bin/gitguard init /absolute/project --profile github-flow --json
/absolute/gitguard-plugin/bin/gitguard init /absolute/project --profile github-flow --apply --json
```

## 规则与职责

唯一运行时规则是 `<git-common-dir>/gitflow.xml`；普通仓库为 `.git/gitflow.xml`，linked worktree 共享 common-dir。init 只选择工作流和初始化 XML，不读改 AGENTS.md。项目 AGENTS 引导由独立 Rust `gitguard install` 管理；插件启动器的 `install --bin-dir` 只安装 CLI。不要混淆两个 install。缺失或损坏 XML 不回退 JSON；旧规则迁移需单独明确授权，不在此技能自动执行。已有 hooks、宿主信任和远端保护均不改动。

## 验证与异常处理

预览应无写入；成功应用后核验 XML，并确认 AGENTS.md 字节不变或仍不存在。已有冲突或损坏配置、工具缺失和未知结果须报告错误/未验证，不假定成功，不删除现有文件或绕过检查。此技能不能证明真实 Agent Hook 或所有人工终端 merge 都受保护。原生 Git 操作继续使用 Git；audit、gate、status、doctor 为现有 CLI，不因此新增同名技能。

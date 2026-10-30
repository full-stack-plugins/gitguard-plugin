# 分支生命周期操作样例

下列 `<plugin-root>` 是宿主提供的真实安装目录；`PROJECT` 应替换真实项目路径。没有插件时仅按 SKILL.md 逐条核验，不执行不存在的命令。

```text
python3 <plugin-root>/scripts/gitflow.py branch PROJECT --operation create --name feature/123-login --source develop --json
```

这是查询或预览；只有当前用户已授权对应具体操作才追加 --apply。gate/audit/discover 本身只读。branch create 不切换；sync merge 目标是当前分支；release finish 包含全部固定与活跃 release 回灌目标；recovery diagnose/resume 不重放操作。

返回 decision/reasons/next_actions，保存 Git 身份与规则修订。拒绝或未验证时保留原现场，不调用更原始的 Git 命令来绕过结果。

初始空仓若明确采用 classic-gitflow，主线日常提交仍受保护：先提出初始提交范围与临时规范修订，用户确认激活后首提交，再恢复保护并 reconcile；不可用 --no-verify 偷渡。

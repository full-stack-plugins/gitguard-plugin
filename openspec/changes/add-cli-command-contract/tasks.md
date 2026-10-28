# GitGuard CLI 命令契约任务

状态：规划完成，按实现证据勾选。

## 1. P0 生命周期

- [ ] 1.1 实现 install/uninstall，区分宿主接入与项目文件；支持 --dry-run。规格：CLI-001。
- [ ] 1.2 实现 version/doctor/status，输出 JSON；doctor 不执行代码检查。规格：CLI-004。
- [ ] 1.3 实现 discover，只读识别项目、语言、构建系统和可用工具。规格：CLI-002。

## 2. P0 项目事实

- [ ] 2.1 实现/补齐 init，幂等，不覆盖已有配置，支持 --dry-run。规格：CLI-003。
- [ ] 2.2 实现/补齐 check，只读门禁，输出统一 decision。规格：CLI-005。
- [ ] 2.3 实现 report，读取已有证据，不重新执行。规格：CLI-006。

## 3. P1 专业能力

- [ ] 3.1 按命令表补齐领域命令：install,uninstall,upgrade,version,doctor,status,discover,init,check,audit,policy,branch,sync,release,hooks,report。规格：CLI-007。
- [ ] 3.2 未实现能力必须输出 DESIGN_ONLY/UNVERIFIED；不得伪造 PASS。规格：CLI-008。

## 4. P1 Hook

- [ ] 4.1 实现 hooks install/status，只写当前仓库 Hook。规格：CLI-009。
- [ ] 4.2 确认 Hook 事件所有权，不与其他 Guard 抢占同一事件。规格：CLI-010。

## 5. P2 兼容

- [ ] 5.1 保留旧命令别名并输出弃用提示。规格：CLI-011。
- [ ] 5.2 增加 golden JSON 与退出码矩阵测试。规格：CLI-012。

## 2026-10-28 生产验收补充：CLI + Codex 本地辅助门禁

此检查点沿用 CLI-001~012，不解冻 integrate-engineering-guard-git，也不声称远端强制合入。目标平台：Windows x64、macOS arm64、Linux x64。插件是 Python GitFlow CLI/MCP/Hook 实现；Rust gitguard 是受信适配器下的只读 policy/install/MCP，不替代插件操作执行器。两者同名 CLI 必须选择单一 PATH 所有者，禁止安装器覆盖另一实现。

- [x] 生命周期安装链接解析、卸载 dry-run、参数完整验证：本地提交 fcfe55de 与 18fed623，Linux 隔离测试通过。
- [ ] 对目标平台的发行包解压、安装后异 cwd CLI、JSON/退出码和卸载逐一提供真实证据；源码目录调用不能替代安装验收。
- [ ] 验证 Linux 插件 CLI/MCP、脏工作区保护、冲突/恢复、超时、取消与未知结果不重放；测试仅临时仓和本地 bare remote。
- [ ] 修复并验证 Windows Python 进程/管道/启动入口的可移植性，保留输出预算与超时终止；未验证平台不得标通过。
- [ ] 三平台 CI 显式断言 OS/架构，并执行同一验收，不以 CI 配置文件存在冒充远端执行。
- [ ] Codex 真实安装、技能发现、MCP 和 Hook 触发验证；若缺真实宿主则列阻塞，stdio 重放不算宿主通过。
- [ ] Rust 只读引擎安装与 policy/MCP 验收，固定适配器来源；引擎/插件分别记录包和版本，明确不提供最终候选审批或服务器强制保障。

允许行为：默认预览/只读；明确 apply 的既有 Git 操作。生产通过需平台证据、安装包证据和真实 Codex 接线同时具备。无额外授权不得推送、发版、修改分支保护或运行真实业务仓库破坏操作。

### Windows 原生操作验收增量（同一 CLI-007/008/012 合同）

- [ ] Windows Server 2022 x64 原生 Job Object runner：真实 Git 查询、进程树/输出预算/超时/取消/失败清理，单列故障注入与真实执行。
- [ ] Windows 原生状态锁：跨进程互斥、异常/崩溃释放、链接/重解析点拒绝、新旧布局同时持锁迁移，释放失败返回未验证。
- [ ] 同一提交执行现有 `test_operations.py`、`test_storage_layout.py` 和新增 `test_native_git_safety.py`；真实临时 Git 仓与本地 bare remote，不执行用户业务仓。
- [ ] 候选引用变化、脏工作区、冲突 abort、unknown 阻断与 resume 不重放逐项记录结果，不以安装器或 runner 单独通过替代完整操作验收。
- [ ] 远端 CI 结束后记录准确提交、平台、通过/失败/跳过及制品；当前文件仅定义可执行候选，不能据此勾选生产就绪。

状态锁为协作式本地互斥，与 POSIX flock 既有信任范围一致；不承诺阻止同 OS 用户恶意替换状态或提供远端不可绕过门禁。独立 skills、真实 Codex Hook、发行包仍须分别验收。

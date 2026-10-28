# Local CLI readiness checkpoint — 2026-10-28

Scope: Windows x64, macOS arm64 and Linux x64 CLI + Codex local assistance. This is not protected-branch enforcement, independent approval, or exact final-merge-candidate admission. The engineering-guard integration plan remains frozen.

## Linux x64 evidence

At plugin baseline `18fed62321316bb5181fc681f02b64e59b979892`, the unchanged existing tests plus lifecycle regressions passed: 136 tests, 42.245 seconds. Tests create temporary repositories and local bare remotes; no user repository writes were performed. Coverage includes CLI/MCP/native hook replay, policy drift, dirty branch refusal, partial release conflict recovery, unknown/running journal refusal and package integrity. This does not establish protection against external concurrent Git writes or independently authorized approvals.

Command: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py'`. The environment had a pre-existing `/tmp/.git`, so ordinary temporary directories did not satisfy the absent-repository fixtures. The successful run used an explicitly authorized `/dev/shm/gitguard-validation-20261028`, created in the same execution session, with assertions that `tempfile.gettempdir()` equalled it and no ancestor contained `.git`. No fixture or fail-closed check was weakened.

A separate real package check generated the existing ZIP, extracted with `unzip` (preserving executable permissions), installed to a temporary bin directory, executed installed `gitguard version --json`, then uninstalled. All five commands exited 0. Package extraction methods that discard executable permissions are not covered by this result.

Cloud evidence root: `/workspace/guard-update-20261028/`:
- `gitguard-linux-acceptance.log`
- `gitguard-package-installed-cli.json`
- `gitguard-package-clean-tmp.log`
- `gitguard-bin-dir-red.log`, `gitguard-bin-dir-trailing-red.log`, `gitguard-bin-dir-green.log`

## Engine versus plugin

The separate Rust `gitguard` main baseline `6d017a43c270e768360c6abc2e1f69568c210f86` builds with its sibling GuardEngine source dependency. Its read-only policy adapter requires explicitly trusted plugin source and Python. It does not execute Git writes or approve technical quality. The Python plugin remains the owner of its existing explicit `--apply` operations. Choose one PATH owner; do not overwrite one implementation with the other.

Engine checks performed locally: `cargo build --locked`; policy CLI/MCP five tests passed after correcting the test adapter checkout name to `gitguard-plugin` and permitting explicit `GITGUARD_ADAPTER_ROOT`. Shared installation checks passed 9 tests; one all-six-tools integration test was skipped, as only GitGuard was supplied. Portable package structure and three MCP tools were verified through stdio; `host_loaded` remains false for that replay. Logs: `gitguard-engine-build.log`, `gitguard-adapter-{red,green}.log`, `gitguard-engine-install.log`, `gitguard-engine-package.log`.

## Remaining release gates

- Windows: plugin process runner uses POSIX pipe selectors and `os.killpg`; shell/symlink installation and native hooks require Windows validation. Nine locked skill snapshots contain the same process implementation. They must be fixed through the `full-stack-skills/git-skills` source and normal vendoring, not edited behind the source lock.
- macOS arm64: previous main CI is not evidence for this local revision or architecture. Run the accepted package/CLI suite on that target.
- Timeout/cancellation: existing bounded runner and unknown-result journal semantics are not evidence of exhaustive crash, cancellation or child-process cleanup testing. Targeted tests and platform evidence remain required.
- Codex: CLI/MCP/Hook replay is not real host acceptance. Actual isolated Codex loading, tool discovery and hook events must be recorded separately. No production readiness claim is made from the replay.
- Remote CI and release: these local changes have not been pushed or released. Current v0.4.0 installation content does not gain local fixes until an authorized new immutable release and catalog update.

## Linux process-lifecycle safety follow-up

Real Git subprocess tests reproduced and fixed a timeout leak when the Git leader exited but a descendant retained stdout/stderr. Cleanup now retires the process group even after the leader exits. SIGINT received while waiting for an established Git process is projected to `git_cancelled` / unverified; an interrupted write is journaled `unknown`, so unrelated apply operations remain blocked pending reconciliation. Cleanup permission errors return `git_cleanup_failed` / unknown, attempt bounded reaping and pipe closure, and never claim the process tree was stopped merely because the leader was killed.

Evidence: `gitguard-runner-red.log`, `gitguard-cancellation-red.log`, `gitguard-cleanup-red.log`, and `gitguard-process-regression-clean.log` (51/51 in the asserted clean TMPDIR). The ordinary `/tmp` run retains two pre-existing ancestor-metadata fixture failures in `gitguard-process-regression.log`. Tests use real local Git aliases/descendants and a real local bare push with an interrupted pre-push hook; only the cleanup-permission error is injected around a real short-lived Git command. Output over the existing 4 MiB budget remains unverified rather than truncated success.

This patch covers the plugin CLI/MCP execution module only. Nine independently installable locked skill scripts still use their upstream implementation; the source was inspected at `full-stack-skills/git-skills` commit `f3ef639aba4c499e4a69ff47e24dd816bd431600`, without modifying or relocking snapshots. Cancellation before `Popen` returns, repeated SIGINT during cleanup, and descendants that deliberately escape the created process group are not proven by these tests. Windows process-tree supervision remains unverified; no `taskkill` fallback is claimed equivalent to a job-object guarantee.

## MCP request metadata compatibility

The real Codex host sends `tools/call` parameters containing standard `_meta` (including `progressToken` and `threadId`). The plugin now accepts this optional object per [CallToolRequestParams](https://modelcontextprotocol.io/specification/2025-11-25/schema#calltoolrequestparams), while continuing to reject unknown top-level parameters and unsupported tool arguments. Metadata values are not interpreted or forwarded to the operation, and cannot authorize `apply`. Null/non-object metadata is rejected. Regression evidence: `gitguard-mcp-meta-red.log` and `gitguard-mcp-meta-green.log`; real-host revalidation is recorded separately and is not inferred from these stdio tests.

Independent follow-up used an isolated copy of this MCP fix with the real Codex app-server, the original plugin manifest and no proxy: plugin installation, MCP handshake and a read-only `gitflow_discover` call returned allow/unborn/isError=false; the target project remained clean. Evidence: `codex-gitguard-meta-fixed.json` and `codex-gitguard-meta-fixed.events.json` in the cloud evidence root (host source fingerprint recorded separately). This is not model execution, Hook event acceptance, or write-operation authorization. Final-commit host validation follows the remaining packaging changes.

## Windows launcher candidate (not Windows Git-operation acceptance)

Bootstrap with `python scripts/cli_entry.py install --bin-dir C:\trusted\bin --dry-run`; remove `--dry-run` only to install. Windows writes a regular managed `gitguard.cmd` file, not a symlink. Exact generated bytes establish ownership; foreign or modified files are preserved, repeat install is idempotent, and uninstall dry-run does not delete. Existing POSIX shell entry remains unchanged. The Python entry delegates to the existing lifecycle and GitFlow modules and preserves their command/argument/exit behavior.

Generated launcher paths (interpreter, package entry and target) must be ASCII and exclude batch metacharacters; paths with spaces are supported. Unicode/codepage compatibility is explicitly unverified and refused before writing. The `.cmd` convenience entry is for trusted interactive invocation, not arbitrary untrusted arguments. Agents should invoke `python scripts/cli_entry.py` using an argv array directly.

The plugin's Windows Git subprocess backend now fails closed with `windows_process_control_unverified` before starting Git. Version/help/lifecycle commands can be exercised independently, but a working launcher does not mean branch/sync/recovery operations are supported on Windows. The separate Rust engine's restricted read-only Windows adapter is a different path and is not changed by this boundary. Nine standalone source-locked skill scripts remain outside this patch.

Linux-hosted file-contract tests and Python-entry parity tests passed, with the actual `cmd.exe` test explicitly skipped outside Windows. A dedicated Windows CI job is a candidate verification path, not an executed result. Logs: `gitguard-windows-entry-{red,green}.log`, `gitguard-windows-posix-regression.log`, `gitguard-windows-process-{red,green}.log`.

## First remote matrix result and Windows UTF-8 correction

Plugin run `40671009152` at `5fc0775` passed Linux x64 (152 passed, one Windows-only skip) and actual macOS arm64 (147 passed, six platform-specific skips). The Windows x64 launcher job failed: both legacy/new `--help` paths attempted to write the Chinese description to a cp1252 pipe, raising `UnicodeEncodeError`. No assertion or Chinese text was removed. CLI/lifecycle standard streams now explicitly use UTF-8; MCP JSON-RPC shares that encoding. A real child-process regression forces `PYTHONIOENCODING=cp1252` and verifies help, structured lifecycle errors and MCP error text remain complete UTF-8. Windows test clients decode the declared UTF-8 protocol explicitly. Real Windows rerun is still required for this correction.

Engine run `40671003756` at `effc0929` passed Ubuntu and Windows, each with 9 installation passes/one unrelated all-tools skip, five policy passes and portable stdio checks. That run checked out GuardEngine `fe36a46b1711d84d21e6bea75358bb6b55c579ce` and plugin main `b4ed2d04a4ce6e934ed595941e8e0426a3467984`; it does not verify the new plugin revision. Subsequent integration CI must pin and verify the intended dependency commits.

## Windows native Git-operation candidate — pending native validation

This later candidate supersedes the launcher-only implementation described above; it does **not** retroactively change those earlier test results. The plugin's proposed Windows runner uses suspended creation and Job Object containment, and the storage backend uses a nonblocking `LockFileEx` byte-range lock. A successful installation, an unsupported-platform rejection, or a Linux test that skips Windows cases is not Windows operation acceptance.

The existing `validate.yml` now has a separate Windows Server 2022 x64 candidate job. It records the runtime architecture and runs these independent, failure-preserving suites:

- `test_windows_runner_safety.py`: actual native process-tree lifecycle, deadlines, cancellation, output bounds and failure cleanup. Fault injection is labelled by each test; it does not replace real descendant execution.
- `test_native_storage_lock.py`: real kernel contention, crash/exception release, single-link lock identity, and continued exclusion while a legacy state directory is moved. Windows-only tests require actual junction rejection and directory pin lifetime.
- `test_operations.py`: all existing real temporary-repository branch/sync/release/recovery cases, including a local bare remote. No network publication or user repository is involved.
- `test_native_git_safety.py`: candidate ref drift before lock acquisition, conflict/explicit abort, dirty-worktree preservation, and an explicitly synthesized crash-window journal followed by recovery without replaying a completed merge.
- `test_storage_layout.py`: the existing state-layout/migration contract. This remains separate from runner validation.

Each suite retains its real exit status and bounded UTF-8 diagnostics through `scripts/candidate_test.py`; logs are candidate artifacts bound to the checked-out commit. Later suites still execute after an earlier failure, without making that failed job successful. Native results, exact commit, run and artifact identifiers must be recorded separately after CI ends.

The Windows lock shares deletion on the locked **file** so migration can move the old directory while its original kernel lock remains held. Both the current-layout and legacy locks stay active through migration. Ordinary primary-directory ancestors are pinned against rename/deletion; legacy migration deliberately allows the legacy directory itself to move. Final-file handle metadata and explicit reparse checks reject links and junctions. These are cooperative local GitFlow concurrency controls, matching the existing POSIX trust model; they are not a sandbox against a malicious process running as the same OS user, and do not establish remote enforcement. Unlock/handle-release failure is an unverified error, not a successful release.

Remaining separate acceptance: Windows native outcomes at the final commit; installed package invocation; actual Codex tools and Hook events; and the nine independently source-locked skill executors. POSIX shell hooks and Linux SIGINT tests are not claimed as Windows Hook or cancellation acceptance. No Hook trust, release, tag or repository protection is changed by this candidate.

A release-only lock error is distinct from interrupted Git execution: if the Git command, after-state observation, and journal commit already completed, the journal retains that proven `complete` outcome while the CLI reports `state_lock_release_failed` as unverified cleanup. It must not fabricate an unknown Git result. The fault-injection acceptance case performs a real locked branch creation, injects only the final release error, then proves the completed branch is not recreated and the journal is unchanged on retry. Actual timeout/cancellation/output-limit failures during execution continue to record `unknown` and block unrelated apply. The candidate also checks canonical worktree identity and explicit UTF-8 CLI decoding; the legacy-locale decoder regression is labelled simulation, not Windows host execution.

Native run `40705552547` at `52e37de` passed the Windows process, ordinary-operation and safety suites, but exposed an NTFS migration limitation: renaming an entire directory containing the open locked file returned WinError 5. The follow-up Windows migration primitive moves each child on the same volume, with `state.lock` last, while retaining its original handle/byte lock and the new-layout lock; only then does it remove the empty old directory. It never unlocks to make migration succeed, copies a lock across volumes, or merges an existing backup. Partial failure retains both sides and reports `state_migration_incomplete`; the existing migration planner blocks automatic overwrite/retry. Regression checks retain file identity, exclusion at the new path, unknown-file preservation and rejection of partial-backup reuse. Actual native revalidation remains required.

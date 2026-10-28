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

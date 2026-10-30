# XML native guard local acceptance — 2026-10-30

This is a local implementation candidate, not a release or production-readiness claim.
The exact local commit and full logs are recorded in the delivery report outside the repository.
No remote CI, push, release, real-repository hook changes, host login or trust changes were performed.

## Verified implementation

- XML-only policy load, eight profile round trips, explicit JSON migration with flattened organization rules.
- Init selects a profile and initializes XML only; absent or arbitrary AGENTS remains unchanged. Rust project install alone owns receipt-protected guidance. Both command orders and repeated calls pass.
- Init and explicit migration use metadata-only discovery: no git status, no project clean-filter execution. Ordinary operation discovery retains all worktree safety checks; uninspected cleanliness is unknown, never clean.
- Real native commit/push fixture acceptance and before-execution Agent merge checks with unchanged refs/index/worktree on refusal.
- Review regressions: ambiguous DWIM refs, Git replacement-object metadata masking, native merge message constraints, AGENTS output size.
- Doctor detects same-version stale native runtime by exact bounded script snapshot, empty hooksPath overrides, redirected paths and missing executable permissions.
- Actual offline candidate ZIP unpacked into a temporary directory: init, hooks, doctor, denied main commit, allowed feature commit and bare-remote push; damaged XML blocks another commit.
- Actual Rust engine binary built offline against the existing locked GuardEngine dependency: XML-backed CLI/MCP negative/fix/recheck, corrupt/missing XML, legacy JSON non-fallback, linked worktree and all eight profile contexts verified. The companion Rust context now exports a versioned XML reference rather than copying rules into guidance; policy CLI/MCP continue to evaluate the full XML.

## Commands and results

`python3 tests/run_isolated.py --temp-root /var/tmp`: **238 methods; 221 passed, 17 original Windows skips, zero failures/errors**. No tests are filtered. Three harness tests preserve contaminated metadata and require genuine isolated child temporary directories.

`python3 scripts/validate_package.py`, `python3 scripts/vendor_skills.py --check` and `git diff --check`: passed; 90 frozen skill files unchanged.

Rust companion offline build passed; cargo test has **zero Rust unit tests**. Actual binary Python suites: **7 policy/context tests passed**, **8 install/init responsibility tests passed**, **11 installation methods: 10 passed, 1 existing six-tool combined test skipped** because only GitGuard is selected. Portable package structure and actual stdio discovery passed (`host_loaded: false`).

Independent review reproduced the clean-filter defect and verified its fix with a live ordinary-status control; metadata-only regression 5/5 and initialization 12/12 passed. No outstanding concrete review findings.

### Closed environment failures

The earlier 227-method run had 26 subtest failure records plus one error across the following 12 methods. Inspection of `/proc/self/mountinfo` proved the sandbox mounted readonly empty `.git` directories at writable roots. Granting another writable root created the same mount there, explaining why merely changing TMPDIR failed. Git returned “not a repository”, while GitGuard correctly saw the marker and returned `repository_unreadable` rather than absent. A formally approved command outside that synthetic filesystem view verified a fresh `/var/tmp` tree with **no ancestor metadata**, then ran the complete suite there. No ancestor was deleted/modified, no product check was relaxed, and no hidden bypass flag was used.

| Test method | Original expectation → observed mismatch | Final result |
|---|---|---|
| `CoreTests.test_no_git_apply_requires_explicit_initialization` | explicit init 0 → unverified 3 | pass |
| `CoreTests.test_no_git_discovery_does_not_initialize_or_write` | absent/0 → unreadable/3 | pass |
| `PackageTests.test_each_skill_can_run_in_isolation` | plain-directory inspector 0 → 3 | pass |
| `PackageTests.test_pack_and_run_from_other_directory` | absent git_state → unverified response, KeyError | pass |
| `ProjectActivationTests.test_cd_updates_activation_before_unknown_dynamic_target` | unmanaged target empty response → ask | pass |
| `ProjectActivationTests.test_effective_command_target_controls_activation` | managed target deny / unmanaged empty → ask | pass |
| `ProjectActivationTests.test_git_environment_cannot_activate_unmanaged_directory` | empty response → unverified/ask | pass |
| `ProjectActivationTests.test_plain_directory_is_silent_for_every_event_without_writes` | empty response → unverified/ask | pass |
| `ProjectActivationTests.test_state_changes_are_observed_without_cached_activation` | initial unmanaged empty → unverified | pass |
| `ProjectActivationTests.test_unmanaged_dynamic_commands_do_not_activate_or_execute` | unmanaged empty → ask | pass |
| `ProtocolTests.test_hook_follows_git_C_and_simple_cd_chains` | effective managed target deny → preliminary cwd ask | pass |
| `ProtocolTests.test_session_context_and_no_git_choice_persistence` | unmanaged empty → unverified | pass |

The harness now rejects contaminated roots before running tests, with explicit environment-error exit 2. This is an error, not a success or skip. Genuine damaged-repository negative tests remain and pass. Product detection still inspects ancestors exactly as before.

## Platform gaps

Linux only: Linux-6.18.55-x86_64-with-glibc2.41; Python 3.12.14.

Seventeen original platform skips remain: two Windows locking/junction tests, one actual cmd.exe installer test, and fourteen Windows Job Object/process tests. They are not passes. Current candidate macOS and Windows execution has not run.

## Remaining external actions

1. Local Linux full-suite isolation is closed; retain the preflight when reproducing tests.
2. Obtain separate approval for pushing this new local branch and running candidate macOS/Windows CI; original branch authorization is not reused.
3. Validate declared Agent hook protocol on a real approved host; Codex trust/login remains untouched and unverified.
4. Define a separately trusted XML provisioning contract before enabling public CI `check`. Until then it fails unverified.
5. Review existing hook-manager integration separately; never overwrite custom hooks or quietly replace native-runtime snapshots.

No remote protection or universal local merge guarantee is claimed. Native hooks remain bypassable and cannot intercept every fast-forward, no-commit, no-verify, or non-Git-library operation.

## Candidate CI checklist (prepared, not executed)

- Pushes require separate approval for both new `feat/xml-native-guard-20261030` branches; no workflows were dispatched here.
- The engine workflow now accepts an immutable full `plugin_sha`, with a fixed paired candidate default. It verifies engine/plugin/GuardEngine checkout identities. See the companion workflow for the exact pin; the external delivery report records both final commits.
- Run plugin `tests/run_isolated.py` on Linux x64, macOS arm64 and Windows x64; confirm all 17 Windows-only tests actually execute on Windows. Keep applicability skips visible.
- Run the companion engine policy, responsibility, installation and package steps against those exact checkouts. All four steps passed locally on Linux.
- The shared GuardEngine verifier is unchanged. The local `tests/run_installation_xml.py` preserves its ten test methods, overrides only its obsolete JSON fixture, and adds an installation responsibility test. The workflow calls this adapter.
- Validate newly assembled platform packages from those same commits; no formal runtime/default-lock changes or release are included.

## First native candidate CI and compatibility repair

Candidate plugin 229f3d2 / engine 0641d67 ran remotely after explicit approval: Linux and macOS passed; Windows exposed strict-default-encoding fixture/package errors and CPython 3.12 path/descriptor ctime disagreement. These failures are retained, not reclassified as skips.

The compatibility repair normalizes only Windows path-versus-descriptor comparison (device/inode/size/mtime/birthtime); full descriptor-before/after and pathname-before/after signatures retain ctime. Reparse/type/link-count/resource checks remain. Strict UTF-8 package reads and native diagnostic captures remove dependence on the Windows ANSI locale. Semantic-mismatch regression failed before the fix. Local complete regression after the fix: **242 tests, 225 passed, 17 existing Windows skips**. Independent review passed XML15 + encoding/diagnostics9 + native hooks12. Native candidate CI on the new paired commits is required; simulations are not native Windows evidence.

### Packaging and registry consistency
Native Windows additionally exposed snapshot path separators and checkout newline conversion. Snapshot keys now use POSIX spelling, and narrowly scoped Git attributes preserve the original frozen bytes; hashes and the 90-file lock are unchanged. A real autocrlf=true checkout with an unprotected CRLF control verifies every frozen byte/hash. All local plugin manifests, DSH metadata, local marketplace entry and runtime version are 0.4.0; the validator rejects drift, including nested local marketplace entries. No tag or release was created. Latest workflow conclusions are recorded separately against immutable paired SHAs.

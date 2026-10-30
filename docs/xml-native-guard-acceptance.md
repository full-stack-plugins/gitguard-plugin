# XML native guard local acceptance — 2026-10-30

This is a local implementation candidate, not a release or production-readiness claim.
The exact local commit and full logs are recorded in the delivery report outside the repository.
No remote CI, push, release, real-repository hook changes, host login or trust changes were performed.

## Verified implementation

- XML-only policy load, eight profile round trips, explicit JSON migration with flattened organization rules.
- Managed AGENTS block preservation/idempotence, expanded-output budget, interactive selection/cancellation, recoverable second-file failure.
- Real native commit/push fixture acceptance and before-execution Agent merge checks with unchanged refs/index/worktree on refusal.
- Review regressions: ambiguous DWIM refs, Git replacement-object metadata masking, native merge message constraints, AGENTS output size.
- Doctor detects same-version stale native runtime by exact bounded script snapshot, empty hooksPath overrides, redirected paths and missing executable permissions.
- Actual offline candidate ZIP unpacked into a temporary directory: init, hooks, doctor, denied main commit, allowed feature commit and bare-remote push; damaged XML blocks another commit.
- Actual Rust engine binary built offline against the existing locked GuardEngine dependency: XML-backed CLI/MCP negative/fix/recheck, corrupt/missing XML, legacy JSON non-fallback, linked worktree and all eight profile contexts verified. Rust source is unchanged; its old JSON-only test fixtures were migrated in the companion local GitGuard branch.

## Commands and results

`python3 -m unittest discover -s tests -p 'test_xml*.py' -v`: 41 passed before adding the packaged-fixture test; that additional real package test passed separately. Independent reviewer reproduced the 41-test pass.

`python3 scripts/validate_package.py`: allow, no errors.
`python3 scripts/vendor_skills.py --check`: allow, 90 snapshot files unchanged.
`git diff --check`: passed.

Final full discovery via `python3 tests/run_isolated.py --temp-root /var/tmp`: **230 methods; 213 passed, 17 original Windows skips, zero failures/errors**. All tests are discovered; none are filtered or converted to skips. Three added harness tests verify detection/preservation of ancestor metadata and actual child-process temporary-directory isolation.

Rust companion validation: `cargo build --locked --offline` and `cargo test --locked --offline` succeeded; cargo test contains **zero Rust tests**, so the seven real-binary Python CLI/MCP/context tests carry the behavior evidence. The original five Python tests first reproduced four failures with JSON-only fixtures; the updated seven tests passed.

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
- Before candidate CI, pair the GitGuard engine checkout with the new XML plugin SHA. Its existing `agent-installation.yml` still pins plugin `89e7c8d2`; it must not be mistaken for new XML-candidate evidence.
- Run plugin `tests/run_isolated.py` on Linux x64, macOS arm64 and Windows x64; confirm all 17 Windows-only tests actually run on Windows, including cmd.exe, junction/sharing and Job Objects. Keep non-Windows skips visible.
- Run the companion engine `tests/policy_check.py` against the actual built binary and paired plugin. It includes all eight context profiles, real CLI/MCP and worktree tests.
- The shared GuardEngine `verify_guard_installation.py::test_gitflow_profiles_drift_and_refresh` still seeds JSON and expects JSON drift. That external fixture needs an explicitly coordinated XML update before claiming the old complete installation workflow validates this candidate. It was not modified or reported passing here.
- Validate newly assembled platform packages from those same commits; no formal runtime/default-lock changes or release are included.

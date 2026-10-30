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
- Unchanged Rust engine's embedded Python adapter source loads this XML policy and reports damaged XML unverified. This was source invocation, **not** rebuilt Rust binary acceptance.

## Commands and results

`python3 -m unittest discover -s tests -p 'test_xml*.py' -v`: 41 passed before adding the packaged-fixture test; that additional real package test passed separately. Independent reviewer reproduced the 41-test pass.

`python3 scripts/validate_package.py`: allow, no errors.
`python3 scripts/vendor_skills.py --check`: allow, 90 snapshot files unchanged.
`git diff --check`: passed.

Full standard unittest discovery (all tests, no filtering): **227 test methods run; 198 succeeded, 12 methods failed/errored, 17 skipped**. unittest reports 26 failure records because failed subtests are counted separately, plus 1 error. No failures were hidden or converted into skips.

All remaining failure records originate from non-repository fixtures beneath protected empty `.git` ancestor directories injected by this execution sandbox. GitGuard deliberately reports `repository_unreadable` rather than pretending the directory is unmanaged. The unpacked-package test then accesses absent `git_state` on that unverified result. A separate writable temporary root was attempted; the sandbox injected an empty protected `.git` there too. No metadata was deleted, sandbox bypassed or product guard relaxed. Full-suite green remains blocked on a normal temporary-directory environment.

Failed/errored test methods:

- `test_core.CoreTests.test_no_git_apply_requires_explicit_initialization`
- `test_core.CoreTests.test_no_git_discovery_does_not_initialize_or_write`
- `test_package.PackageTests.test_each_skill_can_run_in_isolation`
- `test_package.PackageTests.test_pack_and_run_from_other_directory`
- `test_project_activation.ProjectActivationTests.test_cd_updates_activation_before_unknown_dynamic_target`
- `test_project_activation.ProjectActivationTests.test_effective_command_target_controls_activation`
- `test_project_activation.ProjectActivationTests.test_git_environment_cannot_activate_unmanaged_directory`
- `test_project_activation.ProjectActivationTests.test_plain_directory_is_silent_for_every_event_without_writes`
- `test_project_activation.ProjectActivationTests.test_state_changes_are_observed_without_cached_activation`
- `test_project_activation.ProjectActivationTests.test_unmanaged_dynamic_commands_do_not_activate_or_execute`
- `test_protocols.ProtocolTests.test_hook_follows_git_C_and_simple_cd_chains`
- `test_protocols.ProtocolTests.test_session_context_and_no_git_choice_persistence`

## Platform gaps

Linux only: Linux-6.18.55-x86_64-with-glibc2.41; Python 3.12.14.

Seventeen original platform skips remain: two Windows locking/junction tests, one actual cmd.exe installer test, and fourteen Windows Job Object/process tests. They are not passes. Current candidate macOS and Windows execution has not run.

## Remaining external actions

1. Run the unchanged complete suite in an environment without synthetic ancestor `.git` metadata.
2. Obtain separate approval for pushing this new local branch and running candidate macOS/Windows CI; original branch authorization is not reused.
3. Validate declared Agent hook protocol on a real approved host; Codex trust/login remains untouched and unverified.
4. Define a separately trusted XML provisioning contract before enabling public CI `check`. Until then it fails unverified.
5. Review existing hook-manager integration separately; never overwrite custom hooks or quietly replace native-runtime snapshots.

No remote protection or universal local merge guarantee is claimed. Native hooks remain bypassable and cannot intercept every fast-forward, no-commit, no-verify, or non-Git-library operation.

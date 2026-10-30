# Implementation and acceptance tasks

The detailed implementation sequence is in [the local plan](../../../docs/superpowers/plans/2026-10-30-xml-native-guard.md). Checkboxes below are acceptance obligations, not claims that final verification has completed.

- [x] Verify safe typed XML round trips for all eight profiles and v2 flattened rules; reject declarations/entities/XInclude, encoding attacks, unknown fields/types, resource excess and unsafe filesystem objects.
- [x] Verify runtime XML-only loading and linked-worktree common policy with invoking-worktree state; missing/corrupt XML must not fall back to JSON.
- [x] Verify explicit profile selection, read-only preview, managed AGENTS preservation, malformed-marker rejection, repeat-init repair and honest partial-write reporting.
- [x] Verify explicit legacy migration, digest/conflict/locked-rule checks, flattened organization rules, original-file preservation and refusal to replace existing XML.
- [x] Verify declared Claude Bash PreToolUse merge allow/deny/ask behavior against local refs; denial must leave refs/index/worktree unchanged.
- [x] Verify native commit-msg/pre-push fixture integration, pending OIDs/ranges, missing objects, mixed invalid refs, real merge state and absence of fabricated source roles.
- [x] Verify explicit hook installation preserves custom hooks/managers and pins the interpreter; report actual host/platform acceptance separately.
- [x] Verify public CI remains unconfigured without trusted XML distribution; pure evaluation-kernel tests must not be presented as remote enforcement.
- [x] Update English/Chinese onboarding, current usage, historical specification notices and compatibility boundaries.
- [x] Run unittest discovery, existing package validators, and affected native fixture tests; independently review security/contracts and repair findings.
- [x] Record exact tested revision, commands, results, skips and unverified platforms; do not infer production readiness or perform unauthorized external operations.

Verification was executed, not universally green: see [local acceptance](../../../docs/xml-native-guard-acceptance.md) for sandbox failures and unexecuted platforms. External acceptance remains pending.

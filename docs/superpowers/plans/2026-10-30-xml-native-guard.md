# XML native GitGuard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Initialize one safe XML policy and guard ordinary Git actions.
**Architecture:** XML storage feeds existing policy/gate APIs; initialization coordinates XML and managed AGENTS guidance; hooks consume shared policy without Git-client wrapper requirements.
**Tech Stack:** Python 3.11+ stdlib, Git, existing test environment.
**Spec:** openspec/changes/xml-native-guard/design.md

## Global Constraints
No pushes/remote CI/releases/new tools/real-repo hook changes. Preserve all eight profiles and existing user files. XML alone is runtime authority. Unknown inputs fail closed. No claim of universal native merge interception.

## Review Focus
- DTD/entity/encoding/oversized/deep XML must reject before expansion.
- Broken markers and existing XML must preserve user bytes.
- Linked worktree uses common policy, own Git state.
- Agent merge before execution changes no refs/index/worktree.
- Missing/unknown push objects or mixed invalid refs never partially pass.

### Task 1: Safe XML store
- [x] RED tests for eight profile round trips, external entities/DTD/XInclude/schema/resource/path attacks.
- [x] Implement scripts/gitflow/xml_policy.py: policy_path(facts), encode(policy), decode(bytes), read_policy(facts), write_policy(facts, policy); lazy shared validation to avoid cycles.
- [x] GREEN targeted tests; independent review before final commit.

### Task 2: Policy and initialization
- [x] RED missing XML/no legacy fallback, init selection/AGENTS preservation/recovery/worktree tests.
- [x] Switch policy.load/write_activation to XML; explicit migrate operation only for legacy JSON, flatten organization snapshot.
- [x] Implement initialization.py for managed block and coordinated apply; CLI interactive profile selection, no noninteractive default.
- [x] Adapt diagnostic and CI semantics to XML authority; preserve existing JSON only as historical migration input.

### Task 3: Hooks
- [x] RED supported native merge PreToolUse accepts valid direction and rejects invalid without executing.
- [x] Update hooks to use gate directly; retain dynamic/ambiguous rejection.
- [x] RED native commit/push range and failure tests; implement bounded OID-based range validation and safe native integration without requiring wrappers.
- [x] Explicit install preserves existing manager/hooks; interpreter and worktree checks.

### Task 4: Integration and delivery
- [x] Synchronize OpenSpec contracts, README main path and compatibility notices.
- [x] Update obsolete JSON-runtime test fixtures to XML without weakening safety assertions; keep migration-specific tests.
- [x] Run full unittest, existing package validators, native fixture acceptance; list platform skips.
- [x] Fresh independent security/contract review, fix findings and rerun affected/full verification.
- [x] Local commit only; report exact SHA and remaining external validation.

Verification was executed, not universally green: see [local acceptance](../../xml-native-guard-acceptance.md) for sandbox failures and unexecuted platforms. External acceptance remains pending.

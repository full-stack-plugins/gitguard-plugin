# XML native governance requirements

## ADDED Requirements

### Requirement: One shared runtime authority

The system SHALL load policy exclusively from `<git-common-dir>/gitflow.xml`. The eight shipped profiles SHALL be initialization templates only. Operational journals SHALL NOT become policy authorities. Checks SHALL evaluate the invoking worktree's Git state.

#### Scenario: Linked worktrees share policy
- GIVEN two registered worktrees with a shared Git common directory
- WHEN either invokes a governance check
- THEN both read the same XML while branch/index/operation observations come from the invoking worktree.

#### Scenario: Missing XML and a valid legacy snapshot
- GIVEN no valid XML and a valid legacy JSON definition or activation
- WHEN a runtime check runs
- THEN it reports missing/unverified policy without importing or using JSON.

#### Scenario: Independent clone
- GIVEN another clone without local XML provisioning
- WHEN governance is requested
- THEN explicit initialization is required rather than assuming metadata was cloned.

### Requirement: Bounded nonredirected XML storage

The system SHALL preserve all validated policy fields using human-readable typed XML, including v2 rule options and nullable fields. It SHALL reject DTDs, entity declarations/external entity handling, XInclude/namespaces, unknown schema/fields/types, duplicates, malformed values and resource excess. Reads SHALL be bounded and verify identity; writes SHALL validate, lock, check identity and use same-directory atomic replacement. Redirected ancestors, symlinks/reparse points, nonregular and multiply linked files SHALL be rejected.

#### Scenario: Declaration hidden by encoding
- GIVEN an XML document containing a DTD or entity declaration, including an alternate supported encoding
- WHEN decoding is attempted
- THEN the document is rejected before expansion or external resolution.

#### Scenario: Unsafe target or concurrent replacement
- GIVEN a redirected/nonregular target or an identity change detected during writing
- WHEN a write is requested
- THEN the unsafe/concurrently changed target is preserved and the operation fails explicitly.

### Requirement: XML-only initialization

Initialization SHALL require explicit profile selection unless interactive selection is available. Preview SHALL write nothing. Apply SHALL select GitFlow and write the sole common-directory XML policy. Init SHALL NOT read, write, create, validate or require AGENTS.md. Existing XML SHALL NOT be silently replaced; repeat init SHALL preserve its bytes and modification time. Init SHALL report automatic enforcement as false.

#### Scenario: No noninteractive profile
- GIVEN an uninitialized repository and noninteractive input
- WHEN init omits `--profile`
- THEN it fails without selecting a default or writing policy.

#### Scenario: Unusable guidance is irrelevant
- GIVEN absent, arbitrary, edited, malformed, oversized, symlinked or nonregular AGENTS.md
- WHEN explicit valid init runs
- THEN XML initializes independently and AGENTS remains unchanged.

### Requirement: Project installer alone owns guidance

The separate Rust project installer SHALL exclusively own its receipt-backed AGENTS block and reference XML without copying roles or rules. Unknown, edited or broken owned content SHALL refuse replacement and preserve existing files. Plugin launcher bootstrap SHALL NOT be represented as project instruction installation. Runtime context SHALL expose reference schema/metadata rather than role/rule copies; explicit policy checks SHALL still evaluate complete XML rules.

#### Scenario: Either operation order
- GIVEN a disposable project and explicit trusted Rust adapter arguments
- WHEN XML init precedes Rust project install, or Rust project install precedes XML init
- THEN each operation preserves the other's independently owned artifact with install alone owning the AGENTS block.

#### Scenario: Launcher bootstrap
- GIVEN the plugin `bin/gitguard` entrypoint
- WHEN `install --bin-dir` runs
- THEN it bootstraps the launcher and does not initialize AGENTS.md.

### Requirement: Explicit flattened legacy migration

Only `policy --operation migrate --apply` SHALL import legacy JSON. Migration SHALL validate digests, candidate/snapshot agreement, pinned organization references and locked rules; preserve originals; flatten resolved rules into XML; and remove runtime organization inheritance. Existing XML SHALL block replacement by migration. Migration SHALL write XML only and SHALL NOT read, write or require AGENTS.md.

#### Scenario: Locked rule weakened by candidate
- GIVEN an organization baseline locks an enabled rule
- WHEN a migration candidate disables it
- THEN migration fails before creating XML and preserves source files.

#### Scenario: JSON changes after migration
- GIVEN valid XML containing flattened rules
- WHEN old candidate or baseline JSON changes or disappears
- THEN runtime enforcement remains based on XML alone.

### Requirement: Declared pre-execution merge checks

The declared Claude Bash PreToolUse path SHALL check supported explicit native merge argv against actual local refs through the shared gate without requiring wrapper sync journals. Violations SHALL deny before execution. Ambiguous, dynamic and unsupported semantics SHALL require review/unverified handling. No undeclared host or universal terminal interception SHALL be claimed.

#### Scenario: Invalid merge direction
- GIVEN a source and current target whose roles forbid the merge
- WHEN a supported explicit merge is inspected
- THEN the response denies before execution and refs, index and worktree remain unchanged.

#### Scenario: Dynamic shell command
- GIVEN a command whose Git operands cannot be uniquely resolved
- WHEN the pre-execution path inspects it
- THEN it asks/reports unverified rather than fabricating a passing identity.

### Requirement: Supplemental native checks and honest boundaries

Native hook installation SHALL be explicit and preserve existing custom hooks/managers. Entrypoints SHALL pin the installing interpreter. Commit/push checks SHALL use actual pending messages, OIDs, refs and bounded ranges; unknown or incomplete inputs SHALL fail closed. Merge exceptions SHALL require provable actual state and SHALL NOT invent source roles. Documentation SHALL explain fast-forward, no-commit, no-verify and third-party-library limits.

#### Scenario: Mixed valid and invalid push refs
- GIVEN a pending multi-ref push containing an invalid or unknown member
- WHEN pre-push evaluates the update
- THEN no partial passing result authorizes the complete push.

#### Scenario: Existing hook manager
- GIVEN custom hooks or another configured hooks path
- WHEN installation is requested
- THEN GitGuard preserves that wiring and reports the integration conflict/status explicitly.

### Requirement: CI trust remains unconfigured

Public CI check SHALL report `ci_policy_unconfigured` until a trusted XML distribution channel is defined. Neither PR-controlled XML nor legacy JSON SHALL authorize that PR. The explicit-policy range evaluation kernel SHALL NOT be represented as remote enforcement or configured required checks.

#### Scenario: PR supplies permissive policy
- GIVEN a PR changes policy files in its workspace
- WHEN the public CI check is invoked without trusted provisioning
- THEN it remains unconfigured rather than approving using those files.

### Requirement: Compatibility and evidence boundaries

Existing branch/sync/release/recovery entrypoints SHALL remain compatibility interfaces against XML. Rust adapter policy loading SHALL delegate to the shared implementation. Frozen skills and older JSON documentation SHALL be identified as compatibility/historical guidance. CLI/MCP/hook replay SHALL NOT be described as actual host acceptance, unobserved binary execution, production readiness or unexecuted platform validation.

#### Scenario: Missing native hooks
- GIVEN valid policy but absent native hook wiring
- WHEN doctor/status is requested
- THEN missing hooks are visible and the result is unverified, without claiming host or server enforcement.

### Initialization discovery boundary
Init and explicit JSON-to-XML migration SHALL inspect repository metadata without running worktree status or project clean filters. Uninspected dirty state SHALL remain unknown. Other operational checks SHALL retain full worktree inspection. Existing AGENTS content, including malformed or nonregular paths, SHALL not be an initialization prerequisite.

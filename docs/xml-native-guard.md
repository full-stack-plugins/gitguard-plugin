# XML policy and native Git usage

This is the current runtime guide. It supersedes conflicting instructions in historical JSON-era documentation under `docs/`, `product-docs/`, and frozen packaged `skills/`. The [approved design](../openspec/changes/xml-native-guard/design.md) and [requirements](../openspec/changes/xml-native-guard/specs/xml-native-guard/spec.md) define this change.

## Initialize explicitly

From the intended repository, inspect then apply:

```bash
python3 /absolute/gitguard-plugin/scripts/gitflow.py discover .
python3 /absolute/gitguard-plugin/scripts/gitflow.py init . --profile github-flow
python3 /absolute/gitguard-plugin/scripts/gitflow.py init . --profile github-flow --apply
python3 /absolute/gitguard-plugin/scripts/gitflow.py policy . --operation describe
python3 /absolute/gitguard-plugin/scripts/gitflow.py hooks .
python3 /absolute/gitguard-plugin/scripts/gitflow.py hooks . --apply
python3 /absolute/gitguard-plugin/scripts/gitflow.py doctor .
python3 /absolute/gitguard-plugin/scripts/gitflow.py status .
python3 /absolute/gitguard-plugin/scripts/gitflow.py audit .
```

Source-checkout equivalent: `python3 scripts/gitflow.py ...`. Append `--json` for structured output. Noninteractive init without a profile fails instead of choosing a default; an interactive terminal can offer profile selection. Creating a Git repository requires `--initialize-git`. `--mode shared|local` is retained for compatibility; both use the single common-directory XML authority.

Templates live in [`profiles/`](../profiles/): centralized, classic-gitflow, git-maintainer, gitlab-environment, gitlab-release, github-flow, microsoft-release, and trunk-based. Choose deliberately; GitGuard does not infer an organization's branching policy from repository history.

Initialization selects the requested GitFlow profile and writes only the common-directory XML policy. It does not read, write, create or validate AGENTS.md, and absent, edited, malformed, oversized, symlinked or nonregular guidance is not an init precondition. Repeat init validates existing XML without rewriting it; another profile cannot silently replace it. Explicit JSON policy migration is likewise XML-only.

## Separate executable responsibilities

Two entrypoints may share the name `gitguard`, but have different installation responsibilities:

| Explicit entrypoint | Responsibility |
| --- | --- |
| `/absolute/gitguard-plugin/bin/gitguard install --bin-dir /absolute/bin` | Bootstrap the plugin launcher; does not write AGENTS.md. |
| `python3 /absolute/gitguard-plugin/scripts/gitflow.py init ...` | Select one of eight GitFlow profiles and write Git-common-directory XML. |
| `/absolute/rust-build/gitguard install --agents codex --project /absolute/project --gitflow-root /absolute/gitguard-plugin --python /absolute/python3` | Rust project installation: own reference-only AGENTS instructions, host configuration and installation receipt. |

Rust installation can use `--home /absolute/isolated-home` for disposable fixtures. Use explicit executable paths rather than assuming a PATH entry selects the intended implementation. Only Rust project installation owns its `GITGUARD_START` / `GITGUARD_END` instruction block and receipt. Unknown, edited or broken owned content is refused and preserved. Instructions refer to XML without copying roles, merge edges or metadata rules. Either order is supported without touching the other operation's artifact.

Runtime context returns the reference schema and policy metadata rather than copied role/rule dictionaries. Explicit CLI/MCP policy checks still use the complete XML policy through the shared gate. Initialization reports `automatic_enforcement: false`; installation establishes configuration, not host execution, hook enforcement or technical quality approval.

## XML authority and format

Locate the authority with `git rev-parse --git-common-dir`; append `gitflow.xml`. Linked worktrees share that policy but checks inspect the invoking worktree's branch, index and operation state. Operational journals remain under the shared `.gitflow/state` anchor with worktree-specific journal paths; they are not a second policy source.

A separate clone has separate Git metadata and must be initialized deliberately. Do not assume a tracked project XML, initialization template, or legacy activation JSON automatically governs another clone. No trusted team/CI XML distribution channel is implemented here.

The serializer emits UTF-8 typed XML. This excerpt shows actual element syntax, not a complete independently valid policy:

```xml
<?xml version='1.0' encoding='utf-8'?>
<policy type="object">
  <schema_version type="string">1.0.0</schema_version>
  <profile type="string">github-flow</profile>
  <revision type="int">1</revision>
  <roles type="object">
    <main type="object">
      <name type="string">main</name>
      <pattern type="null" />
      <required type="bool">true</required>
      <allow_commit type="bool">false</allow_commit>
      <create_from type="list" />
      <merge_into type="list" />
    </main>
  </roles>
</policy>
```

Dictionary fields use named XML elements. Lists contain `<item>` children; strings, integers, booleans and null have explicit types. Full policies also include all required remote, merge, collaboration and message-pattern fields and any additional roles. Role relationships remain readable XML lists. V2 adds typed `rules` and `extends`; migration flattens inherited rules and sets `extends` to null, so runtime never needs an organization JSON file. XML contains no authoritative embedded JSON payload.

The store rejects DTDs, entity declarations and external entity handling, namespaces/XInclude, unknown schema/fields/types, duplicate fields and malformed values. Budgets include 256 KiB total file bytes, 16 nesting levels, 4096 elements, 16 KiB element text and 128 KiB aggregate text. Encoding does not bypass declaration rejection. Files must be bounded single-link ordinary files; symlinks, Windows reparse points, nonregular targets and redirected ancestors are rejected. Reads are bounded and verify file identity. Writes validate first, take a kernel lock, fsync a same-directory temporary, check identities and atomically replace the XML. Directory durability is synced on POSIX. These cooperative filesystem checks do not claim isolation against a malicious local user racing ancestor renames between syscalls.

## Explicit legacy migration

```bash
python3 /absolute/gitguard-plugin/scripts/gitflow.py policy . --operation migrate
python3 /absolute/gitguard-plugin/scripts/gitflow.py policy . --operation migrate --apply
```

Migration accepts reviewed legacy `.gitflow/workflow.json` and/or an activation snapshot discovered by the existing storage layout. It validates snapshot digests and refuses conflicting definitions. Organization references must resolve to their pinned digest and obey locked-rule restrictions before writing. Resolved rules are copied into XML and the runtime inheritance pointer is removed.

Existing XML blocks migration, including attempts to re-import changed JSON. Legacy originals are preserved; operational legacy-state migration may move the old directory into the existing backup layout and preserve its unknown user files. Existing custom hooks and conflicting state stop migration rather than being overwritten. Keep backups for review. Later JSON edits, missing baseline JSON and removed legacy definitions do not alter valid XML policy. A missing or corrupt XML never falls back to those files.

## Integration boundaries

The checked-in [`hooks/hooks.json`](../hooks/hooks.json) declares Claude-compatible SessionStart, UserPromptSubmit, Bash PreToolUse, PostToolUse and Stop events. The pre-execution decision path validates supported explicit native `git merge` argv and actual local source/target refs with the shared gate, without requiring a wrapper sync journal. Direction violations deny before execution; dynamic shell expressions, ambiguous refs and unsupported semantics remain ask/unverified. This is a declared hook protocol and fixture-tested path, not proof that every host invokes it. No Codex hook registration is declared, and Codex login/trust is separate.

`hooks` previews and `hooks --apply` explicitly install supplemental `commit-msg`/`pre-push` hooks. Existing custom hooks or `core.hooksPath` management are not silently replaced. Installed entrypoints pin the installing Python interpreter and copy a runtime; after upgrading, use doctor to inspect outdated wiring before taking action. This work only installs hooks inside disposable test repositories; the commands above are instructions for an explicit user operation.

Native commit checks inspect real pending commit messages and provable merge state. A merge source role is not invented when refs are missing or ambiguous. Push checks use pending refs/OIDs and bounded commit ranges; unknown objects, incomplete history and invalid members of a multi-ref update fail closed. Native hooks cannot universally intercept merges: fast-forward merges do not create a commit message, `--no-commit` can defer a commit, `--no-verify` can bypass applicable hooks, and external Git libraries may bypass Git hooks altogether. A PR-only workflow is not imposed. Server branch protection and host wiring require independent administrator/host verification.

`doctor`, `status`, and `report` expose observed integration state; missing native hooks yield unverified (exit 3), not success. Gate denial uses exit 1; configuration/unverified failures use exit 3. Audit reports governance findings; it does not install protection. Do not label local CLI/MCP/hook protocol replay as actual host acceptance.

## CI and compatibility

Public `check` raises `ci_policy_unconfigured` until separately trusted XML provisioning exists. It cannot approve using PR-controlled XML or JSON, regardless of a passing local gate. [`ci.evaluate_range`](../scripts/gitflow/ci.py) retains a pure policy-argument range evaluator for bounded local/native use and tests; its existence does not configure remote CI or required checks.

Compatibility `branch`, `sync`, `release`, `recovery`, and `policy --operation activate` remain; activation validates current XML and does not import JSON. They are outside the primary normal-Git onboarding path. The Rust adapter continues delegating to the same policy loader; its context returns metadata references while explicit policy checks consume full XML rules. Generic source snapshots remain under unregistered `vendor/git-skills/`; the registered `skills/` contains only the plugin-owned gitguard-init with this current runtime contract.

## Verification and remaining acceptance

```bash
python3 -m unittest discover -s tests
python3 scripts/validate_package.py
```

Use Python 3.11+ and the existing local toolchain. Tests use disposable repositories and local bare remotes. Verification evidence must distinguish parser/storage tests, CLI/MCP/hook replay, native fixture tests and real host installation. No remote CI, actual user-repository hook change, push, release, production-readiness claim or current macOS/Windows acceptance is established by these instructions. Actual Windows native hooks need Git-for-Windows execution; platform coverage should be reported with the exact tested revision when available.

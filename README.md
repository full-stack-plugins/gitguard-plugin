# GitGuard

GitGuard checks branch names, commit permissions, merge direction and configured commit metadata against one local XML policy. Use ordinary Git after explicit initialization and integration review.

[简体中文](README.zh-CN.md) · [Usage and safety](docs/xml-native-guard.md) · [XML contract](openspec/changes/xml-native-guard/specs/xml-native-guard/spec.md)

## Start in an existing repository

Use the plugin Python entrypoint explicitly for policy initialization and native hooks. The Rust project installer is a different executable, even when both commands are named `gitguard`.

```bash
python3 /absolute/gitguard-plugin/scripts/gitflow.py init . --profile github-flow       # preview; writes nothing
python3 /absolute/gitguard-plugin/scripts/gitflow.py init . --profile github-flow --apply
python3 /absolute/gitguard-plugin/scripts/gitflow.py hooks .                           # preview native hook installation
python3 /absolute/gitguard-plugin/scripts/gitflow.py hooks . --apply                   # explicit installation in this repository
python3 /absolute/gitguard-plugin/scripts/gitflow.py doctor .
python3 /absolute/gitguard-plugin/scripts/gitflow.py status .
python3 /absolute/gitguard-plugin/scripts/gitflow.py audit .
git switch -c feature/example
# edit and stage your files
git commit -m "feat: add example"
```

Choose a profile that matches the repository. The eight initialization templates are `centralized`, `classic-gitflow`, `git-maintainer`, `gitlab-environment`, `gitlab-release`, `github-flow`, `microsoft-release`, and `trunk-based`. They are templates, not runtime authorities. Noninteractive initialization requires `--profile`; a missing repository additionally requires `--initialize-git` to create Git metadata.

Initialization selects a profile and writes `<git-common-dir>/gitflow.xml` only. It neither reads nor writes `AGENTS.md`, and guidance contents or file type are not initialization preconditions. Explicit legacy policy migration has the same XML-only responsibility. Linked worktrees share XML and are evaluated against their own Git state. A separate clone needs its own explicit initialization; Git does not transfer this metadata policy when cloning.

## Install host guidance separately

The plugin launcher bootstrap, `/absolute/gitguard-plugin/bin/gitguard install --bin-dir /absolute/bin`, installs the launcher; it does not write AGENTS.md. To install project instructions and host configuration, invoke the separately built Rust executable explicitly:

```bash
/absolute/rust-build/gitguard install --agents codex \
  --project /absolute/project --gitflow-root /absolute/gitguard-plugin \
  --python /absolute/python3
```

Use `--home /absolute/isolated-home` for disposable acceptance fixtures. Rust project installation alone owns its receipt-backed AGENTS block. Instructions reference XML without copying roles or rules; unknown, edited or broken owned entries are refused and preserved. Install and policy init can run in either order because they have separate responsibilities. Rust context exposes a reference schema and policy metadata, while explicit policy checks continue evaluating full rules. Neither installation nor initialization enables automatic enforcement (`automatic_enforcement` remains false).

## What is enforced

[Declared Agent hooks](hooks/hooks.json) use the Claude hook protocol; `PreToolUse` matches `Bash`. An explicit supported native merge is checked before execution against actual local refs. Ambiguous, dynamic or unsupported commands require review (`ask`/unverified). This does not establish interception of every terminal or IDE command. No Codex hook registration or login/trust change is included.

Explicitly installed Git `commit-msg` and `pre-push` hooks add native checks. Existing custom hooks or hook managers are preserved rather than overwritten. `doctor` reports wiring and uncertainty; missing hooks produce an unverified result. Fast-forward merges, `--no-commit`, `--no-verify`, other Git libraries and host integrations have coverage limits. See [the detailed boundaries](docs/xml-native-guard.md#integration-boundaries).

Public CI `check` remains unconfigured until a separately trusted XML distribution channel exists. PR-supplied XML and legacy JSON cannot approve the PR that supplies them. The internal range evaluation kernel is not a remote enforcement guarantee.

## Existing installations

Runtime loads XML only, without JSON fallback. To migrate a reviewed legacy definition or activation snapshot:

```bash
python3 /absolute/gitguard-plugin/scripts/gitflow.py policy . --operation migrate       # preview
python3 /absolute/gitguard-plugin/scripts/gitflow.py policy . --operation migrate --apply
```

Migration preserves legacy files, validates organization references and locked rules, and flattens resolved rules into XML. Existing XML prevents migration from replacing it. `branch`, `sync`, `release`, `recovery` and older activation entrypoints remain compatibility interfaces; new onboarding uses normal Git. The Rust adapter delegates policy loading to the same Python implementation; runtime context exposes metadata references while policy checks consume the complete policy. Packaged `skills/` remain frozen compatibility guidance.

## Development verification

Python 3.11+ standard library is the runtime dependency. Run local checks from the checkout:

```bash
python3 tests/run_isolated.py
python3 scripts/validate_package.py
```

These checks and isolated repository fixtures do not establish actual host installation acceptance, production readiness, or current macOS/Windows validation. No real repository hook installation, remote CI run, push or release is implied by this documentation.

The [XML design](openspec/changes/xml-native-guard/design.md) and [current usage guide](docs/xml-native-guard.md) supersede conflicting JSON-runtime instructions in older `docs/` and `product-docs/` material.

License: [Apache-2.0](LICENSE).

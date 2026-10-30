# GitGuard

GitGuard checks branch names, commit permissions, merge direction and configured commit metadata against one local XML policy. Use ordinary Git after explicit initialization and integration review.

[简体中文](README.zh-CN.md) · [Usage and safety](docs/xml-native-guard.md) · [XML contract](openspec/changes/xml-native-guard/specs/xml-native-guard/spec.md)

## Start in an existing repository

The installed command is `gitguard`. From a source checkout, use `python3 scripts/gitflow.py` with the same arguments.

```bash
gitguard init . --profile github-flow       # preview; writes nothing
gitguard init . --profile github-flow --apply
gitguard hooks .                           # preview native hook installation
gitguard hooks . --apply                   # explicit installation in this repository
gitguard doctor .
gitguard status .
gitguard audit .
git switch -c feature/example
# edit and stage your files, including the generated AGENTS.md guidance
git commit -m "feat: add example"
```

Choose a profile that matches the repository. The eight initialization templates are `centralized`, `classic-gitflow`, `git-maintainer`, `gitlab-environment`, `gitlab-release`, `github-flow`, `microsoft-release`, and `trunk-based`. They are templates, not runtime authorities. Noninteractive initialization requires `--profile`; a missing repository additionally requires `--initialize-git` to create Git metadata.

Initialization writes `<git-common-dir>/gitflow.xml` and one managed block in the repository's `AGENTS.md`. It preserves surrounding guidance. Linked worktrees share XML and are evaluated against their own Git state. A separate clone needs its own explicit initialization; Git does not transfer this metadata policy when cloning.

## What is enforced

[Declared Agent hooks](hooks/hooks.json) use the Claude hook protocol; `PreToolUse` matches `Bash`. An explicit supported native merge is checked before execution against actual local refs. Ambiguous, dynamic or unsupported commands require review (`ask`/unverified). This does not establish interception of every terminal or IDE command. No Codex hook registration or login/trust change is included.

Explicitly installed Git `commit-msg` and `pre-push` hooks add native checks. Existing custom hooks or hook managers are preserved rather than overwritten. `doctor` reports wiring and uncertainty; missing hooks produce an unverified result. Fast-forward merges, `--no-commit`, `--no-verify`, other Git libraries and host integrations have coverage limits. See [the detailed boundaries](docs/xml-native-guard.md#integration-boundaries).

Public CI `check` remains unconfigured until a separately trusted XML distribution channel exists. PR-supplied XML and legacy JSON cannot approve the PR that supplies them. The internal range evaluation kernel is not a remote enforcement guarantee.

## Existing installations

Runtime loads XML only, without JSON fallback. To migrate a reviewed legacy definition or activation snapshot:

```bash
gitguard policy . --operation migrate       # preview
gitguard policy . --operation migrate --apply
```

Migration preserves legacy files, validates organization references and locked rules, and flattens resolved rules into XML. Existing XML prevents migration from replacing it. `branch`, `sync`, `release`, `recovery` and older activation entrypoints remain compatibility interfaces; new onboarding uses normal Git. The Rust adapter delegates policy loading to the same Python implementation; its unchanged Rust source was rebuilt locally and exercised by the companion XML CLI/MCP tests. Packaged `skills/` remain frozen compatibility guidance.

## Development verification

Python 3.11+ standard library is the runtime dependency. Run local checks from the checkout:

```bash
python3 tests/run_isolated.py
python3 scripts/validate_package.py
```

These checks and isolated repository fixtures do not establish actual host installation acceptance, production readiness, or current macOS/Windows validation. No real repository hook installation, remote CI run, push or release is implied by this documentation.

The [XML design](openspec/changes/xml-native-guard/design.md) and [current usage guide](docs/xml-native-guard.md) supersede conflicting JSON-runtime instructions in older `docs/` and `product-docs/` material.

License: [Apache-2.0](LICENSE).

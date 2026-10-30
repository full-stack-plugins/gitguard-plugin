## ADDED Requirements

### Requirement: Namespaced user skill identities
The plugin SHALL expose exactly nine gitguard-* skills with matching directory, SKILL name and host prompt identities.

#### Scenario: Offline package discovery
- **WHEN** a candidate package is unpacked
- **THEN** only gitguard-awesome/workflow/init/branch/audit/commit/sync/release/recovery are discovered as the nine skill entries
- **AND** ordinary Git commands and internal gitflow module names are unchanged

### Requirement: Existing guidance and policy responsibilities
Install SHALL own AGENTS guidance; init SHALL only choose the workflow and initialize gitflow.xml.

#### Scenario: Installation before or after init
- **WHEN** install and init are run in either order in a temporary repository
- **THEN** init preserves AGENTS bytes and current policy remains XML only

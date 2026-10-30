# Skill identity

## ADDED Requirements

### Requirement: Plugin-owned initialization
The plugin SHALL register only gitguard-init and keep generic git-* source outside its registered skills directory.

#### Scenario: initialize policy
- WHEN the authorized user chooses a profile
- THEN the skill invokes existing plugin CLI init with an explicit project and profile, previews before apply, and preserves AGENTS.md

### Requirement: Separate provenance
The lock SHALL record upstream source commit and source file hashes separately from packaged file hashes. Vendoring SHALL preserve owned skills, detect upstream and packaged drift, and keep runtime profiles equal to source profiles.

#### Scenario: regenerate snapshot
- WHEN a clean committed generic source is vendored twice
- THEN owned skill bytes are unchanged and both source and package checks pass

# ADR 0007: Public Rebrand to Hardproof

- Status: Accepted
- Date: 2026-07-11
- Decision owners: Hardproof maintainers

## Context

The project previously operated under the working name "Crucible" with the
distribution identity `crucible-agent`. That name overlapped with existing
commercial uses and had not completed trademark or marketplace clearance.

The project needed a permanent public identity before the v0.1.0 public alpha.

## Decision

The project is permanently rebranded as **Hardproof** with the tagline
"Software has to earn done."

All public and internal surfaces use the new identity:

| Surface | Old | New |
|---------|-----|-----|
| Product name | Crucible | Hardproof |
| Display wordmark | CRUCIBLE | HARDPROOF |
| Repository | asimons81/crucible-agent | asimons81/hardproof |
| Python package | crucible-agent | hardproof |
| Import package | crucible_agent | hardproof |
| Plugin key | crucible | hardproof |
| Slash command | /crucible | /hardproof |
| CLI command | hermes crucible | hermes hardproof |
| State directory | .crucible/ | .hardproof/ |
| Env prefix | CRUCIBLE_ | HARDPROOF_ |
| Tool prefix | crucible_ | hardproof_ |

The rename preserves all behavior. No semantics, policies, or contracts changed.

Old state directories (`.crucible/`) are detected but never automatically
migrated, merged, or deleted. A dedicated `hermes hardproof migrate-state`
command performs explicit migration with backup, integrity verification, and
rollback instructions.

## Consequences

- Every file, import, identifier, test, and document was renamed in a single
  coherent pass.
- Old-name references remain only in migration code, historical changelog
  entries, clean-room documentation, this ADR, and tests proving the old
  names no longer work.
- The public v0.1.0 alpha ships under the Hardproof identity.
- The rename manifests and residual-name audit provide auditable evidence
  of completeness.

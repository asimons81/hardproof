# Configuration and Migration Diagnostics

Use `hermes hardproof config validate` for strict schema validation and `config explain` for a
secret-safe view of the effective profile, selected policy packs, stage graph, immutable constraints,
and configuration fingerprint. Hardproof never rewrites an existing configuration implicitly.

Use `hermes hardproof db status` to inspect the schema ledger and SQLite integrity. Run
`hermes hardproof db migrate --dry-run` before an explicit `db migrate`; dry-run output includes
`mutation_occurred: false`. Newer unknown schemas fail closed. Migrations are forward-only,
transactional, idempotent on rerun, and preserve the existing migration ledger.

`hermes hardproof doctor` combines configuration, database, state-directory, Git, policy-pack,
stage-graph, and Hermes compatibility checks. If both `.crucible/` and `.hardproof/` exist, resolve
the conflict using `migrate-state`; that operation creates `.hardproof.backup`, checks SQLite
integrity before and after copying, and prints rollback guidance. Do not remove state during package
uninstallation. Downgrade safety is not claimed.

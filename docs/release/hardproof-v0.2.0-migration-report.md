# Hardproof v0.2.0 Migration Report

- Fresh database: migrations 001 and 002 apply transactionally.
- Public v0.1.1 rehearsal: migration 001 under v0.1.1, then migration 002 under v0.2.0.
- Preservation: ordered history `[1, 2]`; run/evidence/approval tables remain intact by fixture tests.
- Recovery: failed migration transaction rolls back; reruns are idempotent; future schemas fail.
- Integrity: `PRAGMA integrity_check` returned `ok` after the real clean-environment upgrade.
- Rename migration: `.crucible/` copying is explicit, backed up, integrity checked, and reversible;
  conflicts fail without overwrite.

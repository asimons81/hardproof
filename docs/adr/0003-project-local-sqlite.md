# ADR 0003: Project-Local SQLite State

- Status: Accepted
- Date: 2026-07-11

## Context

Crucible state must survive sessions and process restarts while remaining local to the project, inspectable, transactional, cross-platform, and independent of a hosted service. The protocol needs atomic stage transitions and append-only event ordering without introducing an ORM.

## Decision

Each managed project uses `.crucible/state/crucible.db`. SQLite connections are short-lived and created per repository operation with foreign keys enabled, WAL journaling, and a 5,000 ms busy timeout. Raw connections are never shared across threads.

Schema changes are forward-only packaged SQL migrations. Every migration and its schema-ledger insert execute in one explicit transaction. A database with a newer unknown schema is read-protected from writes. Integrity setup failures produce a diagnostic and never overwrite or automatically repair the original file.

Repository methods map rows into immutable domain records. Events are append-only, and a stage update plus its transition event share one transaction with optimistic concurrency checks.

## Consequences

- State is portable with the project and needs no server process.
- WAL sidecar files are normal live-state artifacts and remain under `.crucible/state/`.
- Backup, corruption recovery, and migration rehearsal remain explicit operational concerns.
- Later schema changes must add a numbered migration and rollback/rehearsal tests; existing migration files are immutable after public release.

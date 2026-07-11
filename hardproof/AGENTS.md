# hardproof/ AGENTS.md — Package Architecture Instructions

This file guides coding agents working inside the `hardproof/` package directory.

## Architecture Boundaries

- `commands/` — human-facing surfaces (CLI, slash, shared). The shared command service is the single source of truth for all command behavior.
- `domain/` — pure data models, enums, stage transitions, and workspace snapshots. Must be deterministic and side-effect-free.
- `hooks/` — Hermes lifecycle hooks (context injection, tool policy, verification, session lifecycle). Each hook registers through the public Hermes hook API.
- `policy/` — rule evaluation, stage graphs, terminal normalization, waivers, and language packs. All policy must be deterministic.
- `services/` — application services (approvals, evidence, reports, risks, runs, tasks, waivers, sessions). Services depend on storage.
- `storage/` — SQLite database, migration engine, and run repository. All state changes go through the repository.
- `tools/` — six hardproof_* tool handlers and JSON schemas. Tools use public Hermes tool registration.
- `skills/` — nine stage skills, each a SKILL.md loaded by the plugin.
- `templates/` — report templates in markdown.
- `migrations/` — SQL migration files, forward-only.

## Deterministic and Secret-Safe Behavior

- All policy evaluation must be deterministic: same inputs always produce same outputs.
- No hidden network behavior. No outbound connections, no remote asset fetching, no telemetry.
- Evidence output is redacted (secrets are replaced with `[REDACTED]`) and size-bounded.
- Policy decisions store argument SHA-256 hashes, not raw values.

## Type Requirements

- `strict` mypy is enforced in CI on the `hardproof` package.
- All public functions and methods must have type annotations.
- Use `from __future__ import annotations` in every module.
- Use `slots=True` on all dataclasses.

## Policy and Authority Invariants

- Immutable rules (terminal, state, evidence, migration, approval authenticity) can never be waived.
- Approvals exist only through human command surfaces (`approve`, `waive`).
- Tool handlers must never create approvals or waivers.
- Risk suggestions are advisory only. They cannot change profile or task risk without explicit human action.

## Migration Rules

- Migrations are forward-only and append-only history.
- Never delete or alter a committed migration.
- Schema downgrade is not supported.
- State migration from `.crucible/` to `.hardproof/` (rename) must create a backup and never silently merge or delete.

## Public API Compatibility

- The six-tool contract (schemas and handler return shapes) is stable.
- Command surface (CLI subcommands and slash-command equivalents) is stable.
- Profile names (quick, standard, critical) are stable.
- Stage names (INTAKE, DISCOVERY, DESIGN, PLAN, IMPLEMENT, REVIEW, VERIFY, DELIVER, LEARN, PAUSED, ABORTED, COMPLETE) are stable.
- Approval gate names (design, plan, completion) are stable.

## Choosing the Correct Layer

| Change type | Layer |
|------------|-------|
| New command or subcommand | `commands/shared.py` (handler) + `commands/cli.py` (argparse) + `commands/slash.py` (dispatch) |
| New domain logic | `domain/` module |
| New policy rule | `policy/` module |
| New tool | `tools/schemas.py` (schema) + `tools/handlers.py` (handler) + `plugin.yaml` (metadata) |
| New storage operation | `storage/repository.py` |
| New migration | `storage/migrations.py` + `migrations/` SQL file |
| New lifecycle hook | `hooks/` module + `plugin.py` registration |
| New service | `services/` module |

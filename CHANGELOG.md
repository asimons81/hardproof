# Changelog

All notable changes to Hardproof are documented here.

## [0.3.1] - 2026-07-12

### Fixed

- **P0-1: Production child handoff contract.** Redesigned the Workcell launch sequence so the tentative attempt identity is generated before the child context is finalized. The child now receives `attempt_id`, `attempt_number`, and `graph_revision_id` in its context, enabling it to produce a valid `result.json` that passes identity validation without post-launch repository introspection. Added a regression test (`test_child_can_write_result_from_received_context_only`) that proves the child can write an accepted result using only information delivered in the launch context.

- **P0-2: Required Workcell transition gate.** Added a deterministic `workcell_required_unresolved` aggregate to transition facts. The IMPLEMENT to REVIEW gate now blocks when required Workcell tasks are not in a terminal successful state. The gate is enforced for Quick, Standard, and Critical profiles. Added unit and end-to-end integration tests proving the gate works for denial and acceptance paths.

- **Enforced configured claim timeout.** `claim_timeout_seconds` from project configuration is now passed through to the SQLite claim expiry window instead of the hardcoded 15-minute default.

- **Enforced active child concurrency bounds.** `maximum_active_children` from project configuration is now enforced before attempting a new launch. `run-next` returns `None` when the configured active-child limit is reached.

- **Added write scope enforcement at result processing.** Every path reported in `changed_paths` and `artifacts_produced` is validated against the task's declared `write_scope` using glob matching. Paths outside the declared scope are rejected with a descriptive error.

- **Added task specification validation hardening.** The `workcells plan --tasks-json` handler now strictly validates: unknown keys, bounded key/title/objective lengths, acceptance criteria bounds (max 32 items, max 512 chars each), dependency constraints (max 32 items), scope path safety (no traversal, no absolute paths), boolean `required` type, bounded priority (-128 to 127), known model tier values, Quick profile task-count limit (max 3), and profile minimum tier enforcement.

- **Added human-authorized retry command.** `workcells retry <task-id|task-key> <reason>` is now available on the CLI and slash surfaces. It requires IMPLEMENT or REVIEW stage and accesses the existing `authorize_workcell_retry` repository method.

- **Added stage scoping to Workcell operations.** `launch_next` and `process_result` now verify the run is in IMPLEMENT stage before proceeding. Cross-run attempt processing is prevented.

- **Documentation synchronized across all files.** README.md, STATUS.md, ROADMAP.md, AGENTS.md, docs/AGENTS.md, and docs/specs/v0.3.0-workcells.md now accurately describe v0.3.0 as released and v0.3.1 as prepared/pending. All stale references to v0.2.0 being current or v0.3.0 being unstarted have been corrected.

### Configuration

- `claim_timeout_seconds` is now enforced at runtime (was previously validated but ignored).
- `maximum_active_children` is now enforced at runtime (was previously validated but ignored).
- `profile_minimum_tiers` is now enforced at graph creation time.
- `model_selectors` is validated at graph creation time.

### Tests

- 8 new tests across unit and integration layers covering P0-1 regression, P0-2 gate enforcement, and scope validation.
- 485 total tests passing (2 skipped: symlink tests on Windows).

### Added

- Workcells dependency-aware task graphs with deterministic validation, cycle detection, and dependency-safe wave planning.
- Transactional SQLite claims with atomic transitions, one-active-attempt enforcement, and fail-closed recovery.
- Bounded child artifact store with path traversal, symlink escape, size, and redaction checks.
- Public-Hermes child adapter using only `dispatch_tool("delegate_task")` with a deterministic fake for tests.
- Immutable attempt state machines with validated transitions and mandatory terminal reasons.
- Authoritative child-result validation: identity match, size bounds, missing-field detection, and acceptance-criteria checking.
- Workcell inspection, retry, recovery, and run-next commands on CLI and slash surfaces.
- Workcells configuration section with tier defaults, per-task overrides, and size-limit validation.
- Schema migration 003 with graph, task, attempt, dependency, and lifecycle event tables.
- 31 new Workcells tests across unit, service, and integration layers.

### Configuration

- `workcells.maximum_attempts` (default: 3) — per-task retry limit
- `workcells.default_model_tier` (required) — provider-neutral tier key
- `workcells.brief_size_limit` (default: 65536) — byte limit for child brief
- `workcells.context_manifest_size_limit` (default: 32768) — byte limit for context manifest
- `workcells.result_size_limit` (default: 65536) — byte limit for child result
- Per-task tiers may override `default_model_tier` in task specs

## [0.2.0] - 2026-07-11

### Added

- Gatehouse policy traces, strict project rules, scoped human waivers, configurable state-failure
  behavior, stable approval keys, and deterministic advisory risk suggestions.
- Bounded monotonic stage-graph configuration with deterministic diagnostics.
- Versioned data-only Python, Node, Rust, and Go policy packs.
- Configuration explanation, database status/dry-run migration, and richer doctor diagnostics.

### Changed

- Released v0.2.0 Gatehouse on GitHub and PyPI with schema migration 002.

## [0.1.1] - 2026-07-11

### Release infrastructure

- **Release signing**: Tags are now cryptographically signed using SSH (Ed25519). The release workflow verifies signatures against `.github/release-signers` before publishing.
- **First PyPI release**: v0.1.1 is the first Hardproof version published to PyPI via Trusted Publishing.

### Changes

- Bump version from 0.1.0 to 0.1.1 (pyproject.toml, plugin.yaml, hardproof/__init__.py)
- Add SSH signing verification to release workflow (`.github/workflows/release.yml`)
- Add `.github/release-signers` with approved public signing key
- Add `docs/security/release-signing.md` with signing policy
- Update `SECURITY.md` with release verification instructions
- Update `CONTRIBUTING.md` with tag-signing requirements

### Application behavior

No application behavior changes. v0.1.1 is identical to v0.1.0 in all runtime code, tests, migrations, skills, tools, and hooks.

### Notes

- v0.1.0 remains available on GitHub as the original public alpha
- PyPI distribution begins at v0.1.1
- The v0.1.0 tag is unsigned by design and will not be retroactively signed

## [0.1.0] - 2026-07-11

Initial public alpha release. See the [v0.1.0 GitHub release](https://github.com/asimons81/hardproof/releases/tag/v0.1.0).

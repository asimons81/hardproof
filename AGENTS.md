# Hardproof Agent Instructions

This file loads as project context when Hermes Agent starts in the Hardproof repository root. Read it before making any changes.

## Project Identity

- **Hardproof** is a persistent, risk-aware engineering protocol for Hermes Agent.
- **Current public release:** v0.3.1 Workcells Hardening (PyPI, GitHub)
- **Current development boundary:** v0.4.0 Challenge Chamber — **not started**.
- **Workcells hardening:** released (v0.3.1).
- **Next planned product release:** v0.4.0 Challenge Chamber — **not started**.
- Hardproof is a standalone Hermes plugin discovered through the `hermes_agent.plugins` entry-point group.
- It uses only public Hermes registration, hook, command, skill, and dispatch APIs.
- The plugin remains opt-in. Hardproof does not modify Hermes core files.

## Read Order

Inspect these files in order before changing code:

1. `AGENTS.md` — this file
2. `README.md` — project overview and quick start
3. `STATUS.md` — current release and maintenance state
4. `ROADMAP.md` — roadmap and version plan
5. `CONTRIBUTING.md` — development workflow
6. `docs/architecture.md` — system architecture
7. `docs/profiles.md` — run profiles (Quick, Standard, Critical)
8. `docs/security-model.md` — security boundary
9. `docs/configuration-and-migrations.md` — config and migration guide
10. `docs/policy-packs.md` — language policy packs
11. Relevant ADRs in `docs/adr/`
12. Relevant tests in `tests/`

Do not assume the README is the entire specification. Read the files relevant to your task.

## Architecture Map

```
hardproof/
├── __init__.py              # Package version and public API
├── plugin.py                # Plugin registration entry point
├── compat.py                # Hermes API compatibility checks
├── config.py                # Configuration loading and defaults
├── constants.py             # Shared constants
├── errors.py                # Error types
├── paths.py                 # Project-local path resolution
├── commands/
│   ├── cli.py               # hermes hardproof CLI adapter
│   ├── slash.py             # /hardproof slash-command adapter
│   └── shared.py            # Shared command implementation (~781 lines)
├── domain/
│   ├── enums.py             # RunStage, RunProfile, ApprovalGate, etc.
│   ├── models.py            # Run, VerificationCheck, SessionBinding, etc.
│   ├── snapshots.py         # Workspace state snapshots
│   └── transitions.py       # Stage transition logic
├── hooks/
│   ├── context.py           # Pre-turn context injection
│   ├── sessions.py          # Session lifecycle hooks
│   ├── tool_policy.py       # Tool-call policy enforcement
│   └── verification.py      # Verification hook
├── migrations/              # SQL migration files
├── policy/
│   ├── packs.py             # Language policy packs (Python, Node, Rust, Go)
│   ├── profiles.py          # Profile definitions
│   ├── stage_graph.py       # Stage graph configuration
│   ├── stage_rules.py       # Stage-aware rules
│   ├── terminal.py          # Terminal normalization
│   ├── tool_rules.py        # Tool-call rules
│   ├── trace.py             # Policy trace model
│   ├── verification_rules.py# Verification-specific rules
│   └── waivers.py           # Waiver logic
├── services/
│   ├── approvals.py         # Human approval service
│   ├── artifacts.py         # Run artifact service
│   ├── authority.py         # Human authority registry
│   ├── decisions.py         # Policy decision persistence
│   ├── evidence.py          # Verification evidence service
│   ├── reports.py           # Report generation
│   ├── risks.py             # Risk classification
│   ├── runs.py              # Run management
│   ├── sessions.py          # Session binding
│   ├── tasks.py             # Task management
│   └── waivers.py           # Waiver service
├── skills/                  # 9 stage skill modules
│   ├── orchestrate/
│   ├── discover/
│   ├── design/
│   ├── plan/
│   ├── implement/
│   ├── review/
│   ├── verify/
│   ├── deliver/
│   └── learn/
├── storage/
│   ├── database.py          # SQLite database wrapper
│   ├── migrations.py        # Migration engine
│   └── repository.py        # Run repository
├── templates/               # Report templates
│   ├── completion.md
│   ├── design.md
│   ├── discovery.md
│   ├── plan.md
│   └── review.md
└── tools/
    ├── handlers.py          # Tool handler implementations
    └── schemas.py           # Exact JSON schemas for 6 tools
```

### Release infrastructure

```
.github/
├── workflows/
│   ├── ci.yml              # Test, lint, build, audit
│   ├── release.yml         # Tagged release publication
│   ├── codeql.yml          # CodeQL analysis
│   └── scorecard.yml       # OpenSSF Scorecard
├── release-signers         # Approved SSH signing keys
├── CODEOWNERS              # Ownership
└── pull_request_template.md
scripts/
├── smoke_install.py        # Clean wheel installation test
└── build_sbom.py           # SBOM generation
```

### Tests

```
tests/
├── unit/                   # Unit tests (primary suite)
├── integration/            # Integration tests
├── contract/               # Contract tests (package data, open source, rename, skills, docs)
└── e2e/                    # End-to-end tests
```

## Public Surfaces

| Surface | Value |
|---------|-------|
| Package name | `hardproof` |
| Plugin key | `hardproof` |
| CLI root | `hermes hardproof` |
| Slash command | `/hardproof` |
| Registered tools | `hardproof_run`, `hardproof_record`, `hardproof_task`, `hardproof_transition`, `hardproof_verify`, `hardproof_report` |
| Profiles | Quick, Standard, Critical |
| Config entry points | `.hardproof/config.yaml`, `hardproof/config.py` defaults |
| State directory | `.hardproof/` |
| Migration commands | `hermes hardproof db status`, `hermes hardproof db migrate`, `hermes hardproof db migrate --dry-run` |
| Diagnostics | `hermes hardproof doctor` |
| State migration (rename) | `hermes hardproof migrate-state` |

### CLI subcommands

`start`, `status`, `approve`, `waive`, `pause`, `resume`, `abort`, `evidence`, `export`, `doctor`, `runs`, `show`, `config` (init/validate/explain), `db` (status/migrate), `complete`, `policy`, `migrate-state`

### Slash-command equivalents

All CLI subcommands work as `/hardproof <subcommand>` in Hermes messaging interfaces.

## Non-Negotiable Invariants

These rules must never be violated:

### Authority
- Approvals are human-created only. Tool handlers cannot create approvals.
- Waivers are human-created only. Tool handlers cannot create waivers.
- Immutable namespaces (terminal, state, evidence, migration, approval authenticity) cannot be waived.
- Risk suggestions are advisory. They cannot silently alter profile or task risk.

### Stage graphs
- Stage graphs remain finite, acyclic, deterministic, bounded, and monotonic in safety.
- VERIFY and DELIVER are always required in non-skip profiles.
- COMPLETE requires fresh successful evidence.

### Evidence
- Stale evidence (recorded against a different workspace Git HEAD) cannot satisfy completion gates.
- Evidence records the Git HEAD at verification time and a tracked-file diff against the working tree.

### Storage
- Migrations are forward-only and preserve history.
- Schema downgrade is not supported.
- State migration from .crucible/ to .hardproof/ creates a backup and preserves old state.

### Tool contract
- The six-tool contract (`hardproof_run`, `hardproof_record`, `hardproof_task`, `hardproof_transition`, `hardproof_verify`, `hardproof_report`) remains stable unless an explicitly approved breaking change is underway.

### Security
- Hardproof coordinates engineering process but is not an OS security sandbox.
- No telemetry, no analytics, no accounts, no hosted dependencies, no remote asset fetching.
- No private Hermes API use. All integration goes through public plugin APIs.
- No Hermes-core modifications. Hardproof is a standalone plugin.
- No secret or raw sensitive output appears in reports. Output is redacted and size-bounded.

### Behavioral
- Hardproof remains opt-in. It does not edit global instructions or install skills into global directories.
- Do not weaken a gate merely to make a test pass.

## Development Workflow

### Setup

```bash
python -m pip install -e ".[dev]"
```

### Validation commands

```bash
python -m pytest                       # Run all tests
python -m ruff check hardproof tests scripts
python -m mypy hardproof               # Strict mypy
python -m build                        # Build wheel and sdist
python -m twine check dist/*.whl dist/*.tar.gz
```

### Coverage

CI enforces:
- Total coverage >= 90% (`--cov-fail-under=90`)
- Critical module aggregate >= 95%

Run coverage locally:
```bash
python -m pytest --cov=hardproof --cov-report=term-missing --cov-fail-under=90
```

To match CI critical module coverage:
```bash
python -m pytest tests/unit/test_domain_transitions.py tests/unit/test_stage_rules.py tests/unit/test_stage_graph.py tests/unit/test_policy_engine.py tests/unit/test_commands.py tests/unit/test_run_service.py tests/unit/test_tool_policy.py tests/unit/test_tool_policy_hook.py tests/unit/test_approval_service.py tests/unit/test_database.py tests/unit/test_evidence_service.py tests/unit/test_terminal_result_parser.py tests/unit/test_snapshots.py tests/unit/test_verification_hook.py --cov=hardproof.policy.stage_rules --cov=hardproof.policy.stage_graph --cov=hardproof.policy.tool_rules --cov=hardproof.services.approvals --cov=hardproof.storage.migrations --cov=hardproof.services.evidence --cov-report=term-missing --cov-fail-under=95
```

## Testing Rules

1. **Reproduce before repairing** — write a failing test that demonstrates the bug before fixing it.
2. **Test allowed and refusal paths** — every permission or gate needs both the happy path and the blocked path.
3. **Test security boundaries** — waivers cannot bypass immutable rules, tools cannot create approvals, etc.
4. **Add migration tests for persisted-state changes** — test fresh databases, upgrades, rollback, idempotence.
5. **Use temporary project roots** — use `tmp_path` fixtures, never write to the real filesystem.
6. **Test Windows path behavior** where relevant (`.exe` pack detection, path separators).
7. **Avoid brittle count snapshots** — do not assert exact test counts, model enumerations, or module file lists.
8. **Avoid change-detector tests** — test behavior contracts, not frozen values.
9. **Preserve real integration coverage** — use real SQLite, real temp directories, real Git commands where practical.
10. **Run focused tests first** — `python -m pytest tests/unit/test_my_module.py -q` before the full suite.

## Documentation Truth Rules

1. Current status documents (`STATUS.md`, `README.md`, `docs/codex/STATUS.md`) describe current public reality.
2. Historical release reports remain historical. Do not rewrite old evidence to make it look current.
3. Do not claim future roadmap work is shipped.
4. Examples must be executable and verified against actual CLI/tool/slash-command implementations.
5. Local paths, private transcripts, and environment dumps must never be committed.
6. Every command shown in docs must exist in the actual parser. Do not invent aliases or syntax.
7. Internal links must resolve. External links are preferred over internal ones for authoritative references.

## Release Rules

1. Release tags are cryptographically signed using SSH (Ed25519).
2. Approved signers are listed in `.github/release-signers`.
3. Public tags are immutable — never delete, recreate, or force-push a published tag.
4. PyPI uses Trusted Publishing (OIDC). No manual uploads. No static PyPI token.
5. Version must be consistent across `pyproject.toml`, `plugin.yaml`, and `hardproof/__init__.py`.
6. Release branches must go through PR review. No direct pushes to `main` for release changes.
7. Release PRs must pass all CI gates before merge.

## Task Boundaries

- **Current development task:** v0.4.0 Challenge Chamber — **not started**.
- **Next planned product release:** v0.4.0 Challenge Chamber — **not started**.
- Do not begin v0.4.0 implementation during the v0.3.1 release program.

## Completion Report

When finishing a task, report:

1. Files changed
2. Behavior changed or unchanged (explicit)
3. Tests run and results
4. Documentation validation performed
5. Migrations affected
6. Unresolved findings with severity (P0/P1/P2/P3)
7. Exact branch and commit

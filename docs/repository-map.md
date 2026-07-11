# Repository Map

## Root Files

| File | Purpose |
|------|---------|
| `AGENTS.md` | Coding agent instructions (Hermes context file) |
| `README.md` | Project overview, install, quick start |
| `STATUS.md` | Current release and maintenance state |
| `ROADMAP.md` | Release roadmap |
| `CONTRIBUTING.md` | Contribution guidelines |
| `CHANGELOG.md` | Release changelog |
| `SECURITY.md` | Security policy |
| `SUPPORT.md` | Support information |
| `GOVERNANCE.md` | Project governance |
| `CODE_OF_CONDUCT.md` | Code of conduct |
| `INSPIRATION.md` | Clean-room inspiration documentation |
| `NOTICE` | License notice |
| `LICENSE` | Apache-2.0 license text |
| `pyproject.toml` | Package metadata, build config, dev dependencies, tool config |
| `plugin.yaml` | Hermes plugin metadata |

## Source (`hardproof/`)

```
hardproof/
├── __init__.py              # Package version
├── plugin.py                # Hermes plugin registration
├── compat.py                # Hermes API compatibility
├── config.py                # Configuration loading
├── constants.py             # Shared constants
├── errors.py                # Error types
├── paths.py                 # Project-local paths
├── commands/                # CLI and slash command surfaces
│   ├── cli.py               # hermes hardproof argparse adapter
│   ├── slash.py             # /hardproof slash-command adapter
│   └── shared.py            # Shared command implementation
├── domain/                  # Domain models and logic
│   ├── enums.py             # Enums (RunStage, RunProfile, etc.)
│   ├── models.py            # Domain models (Run, VerificationCheck, etc.)
│   ├── snapshots.py         # Workspace state snapshot
│   └── transitions.py       # Stage transition logic
├── hooks/                   # Hermes lifecycle hooks
│   ├── context.py           # Pre-turn context injection
│   ├── sessions.py          # Session lifecycle
│   ├── tool_policy.py       # Tool-call policy enforcement
│   └── verification.py      # Verification hook
├── migrations/              # SQL migration files
├── policy/                  # Policy engine
│   ├── packs.py             # Language policy packs
│   ├── profiles.py          # Profile definitions
│   ├── stage_graph.py       # Stage graph configuration
│   ├── stage_rules.py       # Stage transition rules
│   ├── terminal.py          # Terminal normalization
│   ├── tool_rules.py        # Tool-call rules
│   ├── trace.py             # Policy trace model
│   ├── verification_rules.py# Verification rules
│   └── waivers.py           # Waiver logic
├── services/                # Application services
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
├── skills/                  # 9 stage skills
│   ├── orchestrate/         # SKILL.md
│   ├── discover/            # SKILL.md
│   ├── design/              # SKILL.md
│   ├── plan/                # SKILL.md
│   ├── implement/           # SKILL.md
│   ├── review/              # SKILL.md
│   ├── verify/              # SKILL.md
│   ├── deliver/             # SKILL.md
│   └── learn/               # SKILL.md
├── storage/                 # Persistence
│   ├── database.py          # SQLite database wrapper
│   ├── migrations.py        # Migration engine
│   └── repository.py        # Run repository
├── templates/               # Report templates
│   ├── completion.md
│   ├── design.md
│   ├── discovery.md
│   ├── plan.md
│   └── review.md
└── tools/                   # Six registered tools
    ├── handlers.py          # Tool handler implementations
    └── schemas.py           # JSON tool schemas
```

## Tests (`tests/`)

```
tests/
├── unit/                   # Unit tests (fast, isolated)
├── integration/            # Integration tests (real DB, Git)
├── contract/               # Contract tests (package data, rename, docs, skills)
└── e2e/                    # End-to-end tests
```

## Scripts (`scripts/`)

| File | Purpose |
|------|---------|
| `scripts/smoke_install.py` | Clean wheel installation smoke test |
| `scripts/build_sbom.py` | SBOM (CycloneDX) generation |

## GitHub Configuration (`.github/`)

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | CI pipeline (tests, lint, build, audit) |
| `.github/workflows/release.yml` | Release publication workflow |
| `.github/workflows/codeql.yml` | CodeQL security analysis |
| `.github/workflows/scorecard.yml` | OpenSSF Scorecard |
| `.github/release-signers` | Approved SSH signing public keys |
| `.github/CODEOWNERS` | Repository ownership |
| `.github/pull_request_template.md` | PR template |
| `.github/ISSUE_TEMPLATE/bug.yml` | Bug report template |
| `.github/ISSUE_TEMPLATE/feature.yml` | Feature request template |

## Docs (`docs/`)

See [docs/README.md](README.md) for the full documentation index.

## Agent Instruction Files

| File | Audience |
|------|----------|
| `AGENTS.md` | Coding agents working on the whole project |
| `hardproof/AGENTS.md` | Agents editing package source |
| `tests/AGENTS.md` | Agents writing or modifying tests |
| `docs/AGENTS.md` | Agents editing documentation |

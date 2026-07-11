# HARDPROOF

> Software has to earn done.

[![CI](https://github.com/asimons81/hardproof/actions/workflows/ci.yml/badge.svg)](https://github.com/asimons81/hardproof/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/hardproof)](https://pypi.org/project/hardproof/)

> **Alpha software.** v0.2.0 Gatehouse is the current signed public alpha on PyPI. v0.3.0 Workcells development has not begun. Commands, schemas, and contracts may change before v1.0.0.

Hardproof gives coding agents a persistent, risk-aware engineering process that turns ambiguous software requests into reviewed, verified results while preserving the evidence behind every completion claim.

> A persistent, risk-aware engineering protocol for Hermes Agent.

## Current Release

| Release | Version | Status |
|---------|---------|--------|
| Public alpha | v0.2.0 Gatehouse | Released on GitHub and PyPI |
| Previous | v0.1.1 Core Heat | Released on GitHub and PyPI |
| Previous | v0.1.0 Core Heat | Released on GitHub |
| Future | v0.3.0 Workcells | Not started |

## Install

From PyPI:

```bash
pip install hardproof
hermes plugins enable hardproof
```

From GitHub:

```bash
hermes plugins install asimons81/hardproof --enable
```

## Enable

Enable the plugin in Hermes:

```bash
hermes plugins enable hardproof
```

Verify discovery:

```bash
hermes hardproof doctor
```

## Quick Start

Both the CLI and slash-command surfaces work identically:

```bash
# Terminal
hermes hardproof start standard "Build API-key rotation with rollback support"
hermes hardproof status
hermes hardproof doctor

# In Hermes chat
/hardproof start standard "Build API-key rotation with rollback support"
/hardproof status
```

Hardproof stores state under `.hardproof/`, adds that directory to the repository-local Git exclude file, and injects compact stage context into bound Hermes sessions.

## How Hardproof Changes an Agent Workflow

1. **INT AKE** — clarify the request before any code is written
2. **DISCOVERY** — inspect the repository, constraints, and unknowns
3. **DESIGN** — shape a reversible solution (requires human approval)
4. **PLAN** — turn the design into dependency-aware tasks (requires human approval)
5. **IMPLEMENT** — execute approved tasks with focused tests
6. **REVIEW** — challenge the implementation and risks
7. **VERIFY** — run checks and evaluate fresh workspace-bound evidence
8. **DELIVER** — prepare an evidence-backed completion handoff
9. **LEARN** — capture lessons or explicitly skip

Every stage has defined gates. No run completes without fresh successful evidence.

## Profiles

| Profile | Use Case | Key Requirements |
|---------|----------|-----------------|
| **Quick** | Typo fixes, doc updates, one-line changes | Recorded skips, at least one fresh verification check |
| **Standard** | Feature work, refactors, multi-file changes | Discovery, design and plan, human design and plan approval, tracked implementation, review, fresh verification, delivery, learning decision |
| **Critical** | Auth changes, data migrations, production config | Destructive-action approvals, at least two checks, rollback and risk material, fail-closed mutation policy, human completion approval |

No profile permits completion without fresh successful evidence.

## Gatehouse v0.2.0 Features

Gatehouse adds strict project allow/deny/approval rules, ordered policy explanations, human-only
scoped waivers, advisory risk suggestions, bounded monotonic stage graphs, configuration and
migration diagnostics, and versioned Python/Node/Rust/Go policy packs. See
[configuration and migrations](docs/configuration-and-migrations.md) and
[policy packs](docs/policy-packs.md).

## Common Commands

```bash
hermes hardproof start quick|standard|critical "request"
hermes hardproof status
hermes hardproof doctor
hermes hardproof approve design|plan|completion [reason]
hermes hardproof waive <reason>
hermes hardproof pause [reason]
hermes hardproof resume [run-id]
hermes hardproof abort <reason>
hermes hardproof evidence
hermes hardproof export [path]
hermes hardproof config init|validate|explain
hermes hardproof db status|migrate [--dry-run]
hermes hardproof migrate-state
hermes hardproof runs
hermes hardproof show <run-id>
hermes hardproof policy <args>
```

All commands also work as `/hardproof <subcommand>` in Hermes chat.

## Point Hermes Agent at This Repository

Hermes Agent automatically reads `AGENTS.md` when started in the repository. To work on Hardproof itself:

1. Clone or open the repo
2. Start Hermes from the repository root
3. Confirm `AGENTS.md` is loaded (Hermes prints a context-file banner on startup)
4. Follow the instructions in [docs/hermes-agent-guide.md](docs/hermes-agent-guide.md)

## Architecture

Hardproof is a standalone Python package discovered through the `hermes_agent.plugins` entry-point group. It uses only the public Hermes registration, hook, command, skill, and dispatch APIs.

1. **Plugin layer** — registers slash commands, CLI commands, six tools, lifecycle hooks, and nine stage skills
2. **Domain layer** — run profiles, stages, transitions, approval gates, and immutable event models
3. **Policy layer** — stage-aware mutation rules, tool policies, and human-required approval escalation
4. **Storage layer** — project-local SQLite database with forward-only migrations plus human-readable artifacts under `.hardproof/runs/<run-id>/`
5. **Verification layer** — workspace-bound evidence with Git HEAD capture, binary diff freshness checks, and redacted output recording

See [architecture](docs/architecture.md), [profiles](docs/profiles.md), and [compatibility](docs/compatibility.md).

## Verification Evidence

Hardproof requires fresh, workspace-bound evidence before any run can complete. Verification checks capture:

- Git HEAD commit hash at the time of verification
- Binary diff against the working tree to detect uncommitted changes
- Redacted, size-bounded output from each configured check
- Strict exit-code evaluation (only explicit zero passes)

Stale evidence — recorded against a different workspace state — is flagged and cannot satisfy completion gates.

## Security Boundary

Hardproof coordinates engineering process; it is not a security sandbox. Policy hooks do not replace OS permissions, protected branches, sandboxing, isolation, or human code review.

Hardproof includes these protections:
- Force pushes and destructive Git operations are blocked
- Recognized destructive actions are blocked or require human approval
- Source mutation is stage-aware (locked in later stages)
- Human-only approval gates prevent model self-approval
- Policy decisions are recorded with cryptographic hashes of arguments and configuration

See [SECURITY.md](SECURITY.md) and the [security model](docs/security-model.md).

## Privacy

Hardproof has **no telemetry, no analytics, no accounts, no hosted dependencies, no remote asset fetching, and no automatic update checks.** Normal local operation makes no intentional network request. Verification output is redacted and size-bounded. Policy events store argument keys and hashes rather than raw values. Nothing phones home.

## Known Limitations

- Policy hooks coordinate process but are not a security sandbox or complete shell parser
- Managed runs require a Git worktree for workspace-bound freshness evidence
- Local compatibility evidence covers Hermes Agent 0.18.2 on native Windows; macOS and Linux are CI-enforced
- Downgrade from a migrated v0.2.0 database is not supported

## Documentation Index

| Document | Audience |
|----------|----------|
| [docs/README.md](docs/README.md) | Full documentation index |
| [docs/hermes-agent-guide.md](docs/hermes-agent-guide.md) | Hermes Agent operators |
| [docs/architecture.md](docs/architecture.md) | Architecture overview |
| [docs/profiles.md](docs/profiles.md) | Run profiles |
| [docs/protocol.md](docs/protocol.md) | Protocol specification |
| [docs/security-model.md](docs/security-model.md) | Security model |
| [docs/configuration-and-migrations.md](docs/configuration-and-migrations.md) | Config and migrations |
| [docs/policy-packs.md](docs/policy-packs.md) | Language policy packs |
| [docs/command-reference.md](docs/command-reference.md) | All commands and tools |
| [docs/repository-map.md](docs/repository-map.md) | Repository layout |

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Coding agents should read [AGENTS.md](AGENTS.md) first. Design changes use ADRs; breaking protocol changes require a public RFC issue. Contributions use the Developer Certificate of Origin rather than a CLA.

## Roadmap

| Version | Codename | Focus |
|---------|----------|-------|
| v0.1.1 | Core Heat | Standalone plugin, durable stages, SQLite state, approvals, skills, fresh evidence, reports |
| v0.2.0 | Gatehouse | Explainable configurable policy, scoped waivers, risk suggestions, language packs |
| v0.3.0 | Workcells | Dependency-aware task waves, resumable subagent implementers |
| v0.4.0 | Challenge Chamber | Independent specialized reviewers, severity, fix/re-review loops |
| v0.5.0 | Isolation | Branches, worktrees, baseline proof, rollback, backend adapters |

Full roadmap: [ROADMAP.md](ROADMAP.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Affiliation

Hardproof is independent open-source software. It is not affiliated with, endorsed by, or sponsored by Hermes Agent, Nous Research, Atlassian, or any other organization.

---

**Topics:** `hermes-agent` `coding-agents` `agentic-coding` `software-engineering` `verification` `developer-tools` `open-source` `python`

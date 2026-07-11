# HARDPROOF

[![CI](https://github.com/asimons81/hardproof/actions/workflows/ci.yml/badge.svg)](https://github.com/asimons81/hardproof/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> **Software has to earn done.**

Hardproof gives coding agents a persistent, risk-aware engineering process that turns ambiguous software requests into reviewed, verified results while preserving the evidence behind every completion claim.

> **Alpha software: v0.1.0 is a public alpha. Current development is v0.2.0 Gatehouse. Commands, schemas, and contracts may change before v1.0.0.**

---

A persistent, risk-aware engineering protocol for Hermes Agent. **Software has to earn done.**

**Current release:** v0.1.0 "Core Heat" (public alpha)
**In development:** v0.2.0 "Gatehouse"

---

## Install and enable

### From GitHub (recommended)

```bash
hermes plugins install asimons81/hardproof --enable
```

### From PyPI

> **Not yet published.** PyPI distribution is planned for a future release. Install from GitHub for now.

### Enable an already-installed plugin

```bash
hermes plugins enable hardproof
```

Plugins remain opt-in under Hermes configuration. Hardproof does not edit global instructions or install skills into the user's global skill directory.

## First run

Start in a Git repository with at least one commit:

```text
/hardproof start standard "Build API-key rotation with rollback support"
/hardproof status
```

The equivalent terminal surface is:

```bash
hermes hardproof start standard "Build API-key rotation with rollback support"
hermes hardproof status
```

Hardproof stores state under `.hardproof/`, adds that directory to the repository-local Git exclude file when necessary, and injects compact stage context into bound Hermes sessions.

See the [first-run walkthrough](docs/examples/first-run.md) for a guided example.

## Profiles

Hardproof ships three profiles, each calibrated to the risk and coordination needs of a task.

- **Quick** -- Supports low-risk localized work with recorded skips and at least one fresh verification check. Best for small bug fixes, formatting changes, or one-line corrections where full ceremony would be wasteful.
- **Standard** -- Requires discovery, design and plan artifacts, human design and plan approvals, tracked implementation, review, fresh verification, delivery, and a learning decision. The default for most engineering work.
- **Critical** -- Adds destructive-action approvals, at least two independent verification checks, rollback and risk material, fail-closed mutation policy, and human completion approval. Use for production infrastructure, security-sensitive changes, or data migrations.

No profile permits completion without fresh successful evidence.

For full profile definitions, see [protocol profiles](docs/profiles.md).

## Architecture

Hardproof is a standalone Python package discovered through the `hermes_agent.plugins` entry-point group. It uses only the public Hermes registration, hook, command, skill, and dispatch APIs. Five layers compose the system:

1. **Adapters** -- Register public Hermes commands, tools, hooks, and namespaced skills.
2. **Application services** -- Manage runs, artifacts, approvals, decisions, tasks, sessions, evidence, and reports.
3. **Deterministic policy** -- Evaluate stage transitions, mutation rules, profiles, and freshness requirements.
4. **Immutable domain records** -- Define persisted protocol values.
5. **Project-local SQLite** -- Provide migrations and transactional ledgers.

Project-local SQLite stores runs, sessions, events, artifacts, approvals, decisions, tasks, configured checks, and evidence. Human-readable artifacts and redacted command output live beside the database under `.hardproof/runs/<run-id>/`.

The compatibility boundary feature-detects public Hermes methods. No service reaches through private Hermes attributes. Human commands and model tools share services, but only human-facing command sources can create protected approvals.

See [architecture](docs/architecture.md), [protocol profiles](docs/profiles.md), and [compatibility](docs/compatibility.md). Design decisions are recorded in [ADRs](docs/adr/).

## Verification evidence

Every completion claim must be backed by fresh evidence. Hardproof captures Git HEAD, exact binary diff bytes, and ignored-aware untracked content before and after configured verification commands. Reports derive from durable state without mutating it.

When a run completes, the evidence ledger shows:
- The exact workspace state at verification time
- Which checks ran and what they produced
- Redacted command output for each verification step

This evidence is stored alongside the run under `.hardproof/runs/<run-id>/` and is readable without tooling -- just open the artifacts.

## Security boundary

Hardproof coordinates engineering process; it is not a security sandbox. Policy hooks do not replace OS permissions, protected branches, sandboxing, isolation, or human code review.

- Force pushes are blocked during managed runs.
- Recognized destructive actions are blocked or approval-gated depending on the active profile.
- Source mutation is stage-aware: the implement stage permits writes; other stages gate or block them.
- Project-local configuration and plugins execute with the user's local authority.

See [SECURITY.md](SECURITY.md) and the [security model](docs/security-model.md).

## Privacy

Hardproof has **no telemetry, no analytics, no account system, no hosted dependency, no remote asset fetch, and no automatic update check.** Normal local operation makes no intentional network request.

Verification output is redacted and size-bounded. Policy events store argument keys and hashes rather than raw values. Nothing phones home.

## Known limitations in v0.1.0

- Policy hooks coordinate process but are not a security sandbox or complete shell parser.
- Managed runs require a Git worktree for workspace-bound freshness evidence.
- Local Hermes compatibility evidence currently covers Hermes Agent 0.18.2 on native Windows; other supported operating systems are enforced by CI and require a remote green run before publication.
- The working product name remains subject to trademark and marketplace clearance.

## Roadmap

Hardproof ships by evidence gates rather than dates. Every release produces its own specification, migration and compatibility evidence, security summary, package artifacts, checksums, SBOM, and release report before the next release advances.

| Version | Codename | Focus |
|---------|----------|-------|
| **v0.1.0** | Core Heat | Standalone plugin, durable stages and profiles, local SQLite state, approvals, skills, context, mutation policy, fresh evidence, reports, open-source foundation |
| **v0.2.0** | Gatehouse | Explainable configurable policy, scoped waivers, risk suggestions, migration diagnostics, language policy packs |
| v0.3.0 | Workcells | Dependency-aware task waves, resumable fresh implementer subagents |
| v0.4.0 | Challenge Chamber | Independent specialized reviewers, severity, fix/re-review loops, review evidence packages |
| v0.5.0 | Isolation | Branches, worktrees, baseline proof, rollback, cleanup, backend adapters |
| v0.6.0 | Tempering | Human-approved, provenance-linked learning proposals |
| v0.7.0 | Control Room | Cross-surface continuity, timeline, notifications, optional local dashboard |
| v0.8.0 | Protocol SDK | Frozen documented policy, validator, evidence, report, and extension interfaces |
| v0.9.0 | Hardening | Rehearse all migrations, recovery, concurrency, performance, security, Windows, gateway, and compatibility scenarios |
| **v1.0.0** | Proven | Frozen stable public contracts; validated Standard and Critical workflows across multiple repositories, operating systems, and execution backends |

See the full [ROADMAP.md](ROADMAP.md) for details on gating criteria and release process.

### Current development status

**v0.2.0 Gatehouse** is under active development. The next implementation target is **Task 8** (explainable policy evaluation). v0.1.0 Core Heat is the current public alpha -- it is stable enough for evaluation and feedback, but not yet at production-hardened contracts.

## Contributing

Hardproof welcomes issues, documentation, tests, policy analysis, compatibility reports, and code contributions. Start with:

- [CONTRIBUTING.md](CONTRIBUTING.md) -- Development setup, testing, and pull request process
- [GOVERNANCE.md](GOVERNANCE.md) -- Project roles and decision-making
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) -- Community standards

Design changes use ADRs. Breaking protocol changes require a public RFC issue. Contributions use the Developer Certificate of Origin rather than a CLA.

## Inspiration

Hardproof acknowledges conceptual inspiration from the broad idea that coding agents benefit from an explicit, inspectable process, while maintaining a strict clean-room boundary. All behavior, terminology, schemas, prose, tests, and implementation are derived independently from this project's public requirements and the documented public Hermes Agent APIs.

See [INSPIRATION.md](INSPIRATION.md) for the full clean-room statement.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Affiliation

Hardproof is independent and is not affiliated with Hermes Agent or Nous Research.

## Topics

`hermes-agent` `coding-agents` `agentic-coding` `software-engineering` `verification` `developer-tools` `open-source` `python`

# HARDPROOF

> Software has to earn done.

[![CI](https://github.com/asimons81/hardproof/actions/workflows/ci.yml/badge.svg)](https://github.com/asimons81/hardproof/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> **Alpha software.** v0.1.0 is a public alpha. Latest development is v0.2.0 Gatehouse. Commands, schemas, and contracts may change before v1.0.0. Install from GitHub; PyPI publication is pending.

Hardproof gives coding agents a persistent, risk-aware engineering process that turns ambiguous software requests into reviewed, verified results while preserving the evidence behind every completion claim.

> A persistent, risk-aware engineering protocol for Hermes Agent.

## Current Status

| Release | Version | Status |
|---------|---------|--------|
| Public alpha | v0.1.0 Core Heat | Released |
| Active development | v0.2.0 Gatehouse | Task 8 (stage-graph configuration) next |

## Install and enable

From GitHub (only option until PyPI publication):

```bash
hermes plugins install asimons81/hardproof --enable
```

From PyPI (not yet published -- this will work once the package is uploaded):

```bash
pip install hardproof
hermes plugins enable hardproof
```

Plugins remain opt-in under Hermes configuration. Hardproof does not edit global instructions or install skills into the user's global skill directory.

## First run

Start in a Git repository with at least one commit:

```text
/hardproof start standard Build API-key rotation with rollback support
/hardproof status
```

The equivalent terminal surface is:

```bash
hermes hardproof start standard "Build API-key rotation with rollback support"
hermes hardproof status
```

Hardproof stores state under `.hardproof/`, adds that directory to the repository-local Git exclude file when necessary, and injects compact stage context into bound Hermes sessions.

## Profiles

**Quick** supports low-risk localized work with recorded skips and at least one fresh verification check. Use for typo fixes, doc updates, or one-line changes.

**Standard** requires discovery, design and plan artifacts, human design and plan approvals, tracked implementation, review, fresh verification, delivery, and a learning decision. Use for feature work, refactors, or multi-file changes.

**Critical** adds destructive-action approvals, at least two checks, rollback and risk material, fail-closed mutation policy, and human completion approval. Use for auth changes, data migrations, or production configuration.

No profile permits completion without fresh successful evidence.

## Architecture

Hardproof is a standalone Python package discovered through the `hermes_agent.plugins` entry-point group. It uses only the public Hermes registration, hook, command, skill, and dispatch APIs.

1. **Plugin layer** -- registers slash commands, CLI commands, six tools, lifecycle hooks, and nine namespaced skills
2. **Domain layer** -- run profiles, stages, transitions, approval gates, and immutable event models
3. **Policy layer** -- stage-aware mutation rules, tool policies, and human-required approval escalation
4. **Storage layer** -- project-local SQLite database with forward-only migrations plus human-readable artifacts under `.hardproof/runs/<run-id>/`
5. **Verification layer** -- workspace-bound evidence with Git HEAD capture, binary diff freshness checks, and redacted output recording

See [architecture](docs/architecture.md), [protocol profiles](docs/profiles.md), and [compatibility](docs/compatibility.md).

## Verification Evidence

Hardproof requires fresh, workspace-bound evidence before any run can complete. Verification checks run through Hermes in the current working directory, capturing:

- Git HEAD commit hash at the time of verification
- Binary diff against the working tree to detect uncommitted changes
- Redacted, size-bounded output from each configured check
- Strict exit-code evaluation (only explicit zero passes)

Evidence is recorded in the run ledger and included in every completion report. Stale evidence -- evidence recorded against a different workspace state -- is flagged and cannot satisfy completion gates.

## Security Boundary

Hardproof coordinates engineering process; it is not a security sandbox. Policy hooks do not replace OS permissions, protected branches, sandboxing, isolation, or human code review.

Protections included:
- Force pushes and destructive Git operations are blocked
- Recognized destructive actions are blocked or require human approval
- Source mutation is stage-aware (locked in later stages)
- Human-only approval gates prevent model self-approval
- Policy decisions are recorded with cryptographic hashes of arguments and configuration

See [SECURITY.md](SECURITY.md) and the [security model](docs/security-model.md).

## Privacy

Hardproof has **no telemetry, no analytics, no accounts, no hosted dependencies, no remote asset fetching, and no automatic update checks.** Normal local operation makes no intentional network request. Verification output is redacted and size-bounded. Policy events store argument keys and hashes rather than raw values. Nothing phones home.

## Known Limitations in v0.1.0

- Policy hooks coordinate process but are not a security sandbox or complete shell parser
- Managed runs require a Git worktree for workspace-bound freshness evidence
- Local compatibility evidence covers Hermes Agent 0.18.2 on native Windows; other OS support is CI-enforced
- Gatehouse policy features (configurable rules, waivers, risk suggestions) ship in v0.2.0

## Roadmap

| Version | Codename | Focus |
|---------|----------|-------|
| v0.1.0 | Core Heat | Standalone plugin, durable stages, SQLite state, approvals, skills, fresh evidence, reports |
| v0.2.0 | Gatehouse | Explainable configurable policy, scoped waivers, risk suggestions, language packs |
| v0.3.0 | Workcells | Dependency-aware task waves, resumable subagent implementers |
| v0.4.0 | Challenge Chamber | Independent specialized reviewers, severity, fix/re-review loops |
| v0.5.0 | Isolation | Branches, worktrees, baseline proof, rollback, backend adapters |
| v0.6.0 | Tempering | Human-approved provenance-linked learning proposals |
| v0.7.0 | Control Room | Cross-surface continuity, timeline, notifications, local dashboard |
| v0.8.0 | Protocol SDK | Frozen documented policy, validator, evidence, report interfaces |
| v0.9.0 | Hardening | Migration rehearsals, recovery, concurrency, performance, security scenarios |
| v1.0.0 | Proven | Stable public contracts, multi-repo validation across OS and backend targets |

See [ROADMAP.md](ROADMAP.md). A release advances only after its tests, migrations, security review, compatibility evidence, documentation, and package artifacts pass.

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Design changes use ADRs; breaking protocol changes require a public RFC issue. Contributions use the Developer Certificate of Origin rather than a CLA.

## Inspiration

Hardproof acknowledges conceptual inspiration while maintaining a strict clean-room boundary. See [INSPIRATION.md](INSPIRATION.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Affiliation

Hardproof is independent open-source software. It is not affiliated with, endorsed by, or sponsored by Hermes Agent, Nous Research, Atlassian, or any other organization.

---

**Topics:** `hermes-agent` `coding-agents` `agentic-coding` `software-engineering` `verification` `developer-tools` `open-source` `python`

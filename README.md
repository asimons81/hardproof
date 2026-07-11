# Crucible Agent

[![CI](https://github.com/asimons81/crucible-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/asimons81/crucible-agent/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> Alpha software: v0.1.0 is under active development. The command, schema, and extension contracts may change before v1.0.0 through documented migrations and release notes.

Crucible is a local-first engineering protocol for Hermes Agent. It turns rough software requests into durable discovery, approved design and planning, tracked implementation, independent review, and fresh verification evidence tied to the final Git workspace state.

## Install and enable

From GitHub:

```bash
hermes plugins install asimons81/crucible-agent --enable
```

From a Python package:

```bash
pip install crucible-agent
hermes plugins enable crucible
```

Plugins remain opt-in under Hermes configuration. Crucible does not edit global instructions or install skills into the user's global skill directory.

## First run

Start in a Git repository with at least one commit:

```text
/crucible start standard Build API-key rotation with rollback support
/crucible status
```

The equivalent terminal surface is:

```bash
hermes crucible start standard "Build API-key rotation with rollback support"
hermes crucible status
```

Crucible stores state under `.crucible/`, adds that directory to the repository-local Git exclude file when necessary, and injects compact stage context into bound Hermes sessions.

## Profiles

- Quick supports low-risk localized work with recorded skips and at least one fresh verification check.
- Standard requires discovery, design and plan artifacts, human design and plan approvals, tracked implementation, review, fresh verification, delivery, and a learning decision.
- Critical adds destructive-action approvals, at least two checks, rollback and risk material, fail-closed mutation policy, and human completion approval.

No profile permits completion without fresh successful evidence.

## Architecture

Crucible is a standalone Python package discovered through the `hermes_agent.plugins` entry-point group. It uses only the public Hermes registration, hook, command, skill, and dispatch APIs. Project-local SQLite stores runs, sessions, events, artifacts, approvals, decisions, tasks, configured checks, and evidence. Human-readable artifacts and redacted command output live beside the database under `.crucible/runs/<run-id>/`.

See [architecture](docs/architecture.md), [protocol profiles](docs/profiles.md), and [compatibility](docs/compatibility.md).

## Security boundary

Crucible coordinates engineering process; it is not a security sandbox. Policy hooks do not replace OS permissions, protected branches, sandboxing, isolation, or human code review. Force pushes are blocked, recognized destructive actions are blocked or approval-gated, and source mutation is stage-aware. Project-local configuration and plugins execute with the user's local authority.

See [SECURITY.md](SECURITY.md) and the [security model](docs/security-model.md).

## Privacy

Crucible has no telemetry, analytics, account, hosted dependency, remote asset fetch, or automatic update check. Normal local operation makes no intentional network request. Verification output is redacted and size-bounded; policy events store argument keys and hashes rather than raw values.

## Roadmap

The gated release train runs from Core Heat v0.1.0 through Proven v1.0.0. See [ROADMAP.md](ROADMAP.md). A release advances only after its tests, migrations, security review, compatibility evidence, documentation, and package artifacts pass.

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Design changes use ADRs; breaking protocol changes require a public RFC issue. Contributions use the Developer Certificate of Origin rather than a CLA.

## Inspiration

Crucible acknowledges conceptual inspiration while maintaining a strict clean-room boundary. See [INSPIRATION.md](INSPIRATION.md). Crucible is independent and is not affiliated with Atlassian.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

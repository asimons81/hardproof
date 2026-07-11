# Security Policy

## Supported versions

Until v1.0.0, security fixes target the newest published minor release. Maintainers may provide a migration rather than backport a fix when pre-1.0 protocol behavior changes.

## Reporting a vulnerability

Use GitHub's private security advisory flow for `asimons81/crucible-agent`. Do not open a public issue for a vulnerability that could expose secrets, bypass approvals, corrupt state, execute unintended commands, or weaken evidence integrity.

Include affected versions, environment, reproduction steps, impact, and any suggested mitigation. Remove real credentials and private data. Maintainers will acknowledge the report, assess severity, coordinate remediation, and credit reporters who consent.

## Security posture

Crucible is process control, not a security sandbox. It uses project-local state, no telemetry, no hosted dependency, explicit human approval surfaces, bounded redacted output, path containment, forward-only migrations, and workspace-bound evidence. See `docs/security-model.md` for trust boundaries and limitations.

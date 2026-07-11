# Hardproof v0.1.0 Release Candidate

## Release Identity

| Field | Value |
|-------|-------|
| Product | Hardproof |
| Version | 0.1.0 |
| Codename | Core Heat |
| Tagline | Software has to earn done. |
| License | Apache-2.0 |
| Python | >= 3.11 |
| Status | Public Alpha -- unpublished |

## Included Features

- Standalone Hermes plugin with slash command (/hardproof), CLI (hermes hardproof),
  six tools (hardproof_run, hardproof_record, hardproof_task, hardproof_transition,
  hardproof_verify, hardproof_report), hooks, and namespaced skills
- Quick, Standard, and Critical run profiles with stage-gated workflows
- Project-local SQLite state with forward-only migrations
- Stage-aware mutation policy with Hermes approval escalation
- Git workspace snapshots and redacted verification output
- Freshness enforcement for verification evidence
- Deterministic Markdown and JSON completion reports
- Full Standard workflow support with restart recovery
- Human-only protected approvals (design, plan, completion)
- Clean-room implementation boundary

## Known Limitations

- Policy hooks coordinate process but are not a security sandbox
- Managed runs require a Git worktree for workspace-bound freshness
- Local Hermes compatibility evidence covers Hermes Agent 0.18.2 on Windows
- PyPI publication is pending; install from GitHub only
- No Gatehouse policy features (v0.2.0)
- No subagent orchestration (v0.3.0)

## Development Status

The v0.2.0 Gatehouse development line adds explainable configurable policy,
scoped waivers, risk suggestions, migration diagnostics, and language policy
packs. Task 8 (bounded monotonic stage-graph configuration) is the next
Gatehouse item.

## Verification Evidence

- 217 tests passing on Windows (Python 3.11)
- Ruff: all checks passed
- mypy --strict: no issues found in 44 source files
- Wheel build: succeeds
- Sdist build: succeeds
- Package import: `import hardproof` works
- Entry-point discovery: hardproof plugin registered

# Hardproof v0.1.0 Security Review

## Scope

Public alpha v0.1.0 release. Source code, build artifacts, and installed package.

## Methodology

- Full repository secret scan (deterministic pattern matching)
- Package artifact inspection
- Dependency audit (pip-audit)
- Privacy posture review
- Configuration security analysis

## Findings

### P0 (Blockers): None

### P1 (High): None

### P2 (Medium): None

### P3 (Low)

1. **Policy hooks are not a security sandbox.** The stage-aware mutation policy
   coordinates engineering process but does not replace OS permissions, protected
   branches, or sandboxing. This is documented in the security model and README.

2. **Verification commands run with user authority.** The verification subsystem
   executes commands through Hermes with the user's local permissions. Malicious
   verification check configurations could execute arbitrary code. This is a
   documented design property, not a vulnerability.

3. **No dependency pinning in optional dev dependencies.** Dev dependencies use
   minimum version constraints (>=) rather than pinned versions. This is standard
   for library packages and does not affect end users who install from wheel.

### Informational

- No telemetry, analytics, or network requests in normal operation
- No remote asset fetching
- No automatic update checks
- Verification output is redacted and size-bounded
- Policy events store argument hashes rather than raw values
- Project-local SQLite database with forward-only migrations
- Human-only approval gates prevent model self-approval
- Force pushes and destructive git operations are blocked

## Secret Scan

Deterministic pattern search across all tracked files and Git history:

- API key patterns: 0 findings
- Token patterns: 0 findings
- Password patterns: 0 findings
- Private URLs: 0 findings
- Personal file paths: 0 findings (beyond expected project paths)
- Email addresses: Only public maintainer email (asimons81@gmail.com)
- .env files: None committed
- Test secrets: None found (tests use temporary paths)

## Dependency Audit

pip-audit result: No known vulnerabilities in runtime dependency (PyYAML).

## Privacy Posture

- No telemetry collection
- No analytics integration
- No remote asset loading
- No automatic network requests during normal operation
- No user tracking or identification
- Local-only state storage in .hardproof/ directory

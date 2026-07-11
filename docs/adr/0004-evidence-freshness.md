# ADR 0004: Workspace-Bound Verification Evidence

- Status: Accepted
- Date: 2026-07-11

## Context

Command output alone cannot prove that a successful check applies to the workspace later presented as complete. Evidence must distinguish tracked edits, untracked files, concurrent workspace changes, ambiguous terminal results, and Hardproof's own local state.

## Decision

Each verification record stores three Git-derived values captured immediately around command execution: `HEAD`, the SHA-256 of exact binary diff bytes, and the SHA-256 of the sorted ignored-aware untracked path/blob ledger. A check can pass only when Hermes returns an explicit integer zero exit code and the before/after snapshots match.

Missing exit status, malformed results, timeouts, or concurrent workspace changes never pass. Freshness is reevaluated against the current snapshot before delivery or completion. Evidence output is redacted, size-bounded by configuration, hashed, and stored under the run directory; events contain only a bounded redacted preview.

Hardproof adds `.hardproof/` to the repository-local `.git/info/exclude` during run start when the project has not already ignored it. This preserves the exact `git ls-files --others --exclude-standard -z` algorithm without allowing Hardproof's own database and evidence files to invalidate otherwise unchanged source evidence. No tracked `.gitignore` file is modified implicitly.

## Consequences

- Any tracked or relevant untracked change after verification makes passing evidence stale.
- Repositories need a valid `HEAD` before verification can run.
- Ignored files do not affect evidence identity, consistent with Git's project policy.
- A check that modifies the workspace while running is indeterminate even with exit code zero.
- Verification commands must come from durable run configuration.

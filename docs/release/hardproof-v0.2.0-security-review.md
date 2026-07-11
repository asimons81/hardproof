# Hardproof v0.2.0 Gatehouse Security Review

Status: Complete for the local release candidate

## Result

No unresolved P0 or P1 finding remains. Review covered immutable-rule and protected-namespace
bypass, wrapper/chained command normalization, waiver forgery and scope intersection, approval-key
stability, redaction, malicious YAML/regex/glob/path input, graph/config size limits, forward-only
transactional SQLite migration, fail-open constraints, Windows paths, and local-only pack detection.

## Controls verified

- Model-callable tools cannot create, extend, revoke, accept, or override human authority records.
- Immutable terminal, state, evidence, migration, and approval-authenticity rules are unwaivable.
- Command input, segments, tokens, regexes, rules, graph nodes/edges, JSON, traces, and stored output
  are bounded. YAML uses `safe_load`; packs execute no project code and perform no network access.
- Chains and common POSIX, PowerShell, `cmd`, `env`, and shell wrappers are normalized before the
  highest-risk segment is selected. Windows `.exe` pack forms are covered.
- Stage graphs permit only supported forward stages, one deterministic successor, VERIFY, DELIVER,
  and immutable completion. Critical runs cannot use skip overlays or fail open.
- Migration history is append-only, transactions roll back on failure, future schemas are rejected,
  integrity is checked, and legacy state copying creates a backup with rollback guidance.

## Residual findings

- P2: policy parsing is deliberately bounded and conservative, not a full shell or OS sandbox.
- P3: symlink/junction semantics ultimately depend on OS permissions and resolved-path behavior.
- P3: Linux/macOS platform confirmation awaits independent remote CI; Windows is verified locally.

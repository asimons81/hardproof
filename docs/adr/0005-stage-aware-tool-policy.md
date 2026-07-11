# ADR 0005: Stage-Aware Tool Policy

- Status: Accepted
- Date: 2026-07-11

## Context

Standard and Critical runs must preserve intent-before-implementation and prevent silent edits after verification. Hermes provides public `pre_tool_call` block and approval directives, but tool names and terminal syntax can evolve.

## Decision

Crucible separates deterministic classification in `policy/tool_rules.py` from the Hermes adapter in `hooks/tool_policy.py`. Known mutating tool names are feature-configurable. Artifact-directory writes remain allowed in every active stage; project source writes are allowed only during IMPLEMENT.

Immutable force-push rules block in every profile. Recognized destructive commands block or use Hermes's public human-approval escalation, with stable `crucible:` rule keys. Deployment is unavailable before DELIVER. Standard and Critical mutations fail closed when active state cannot load.

Audit events store rule identifiers and hashed argument summaries, never raw arguments or tool output.

## Consequences

- Policy decisions are unit-testable without Hermes runtime state.
- Classification is process control, not a complete shell parser or sandbox.
- New tool aliases and command forms require configuration or tested classifier updates.
- Moving back to IMPLEMENT is the explicit path for post-verification source edits.

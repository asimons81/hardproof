# Architecture

Hardproof is a standalone Hermes plugin with five layers.

1. Adapters register public Hermes commands, tools, hooks, and namespaced skills.
2. Application services manage runs, artifacts, approvals, decisions, tasks, sessions, evidence, and reports.
3. Deterministic policy evaluates stage transitions, mutation rules, profiles, and freshness requirements.
4. Immutable domain records define persisted protocol values.
5. A project-local SQLite repository provides migrations and transactional ledgers.

The compatibility boundary feature-detects public Hermes methods. No service reaches through private Hermes attributes. Human commands and model tools share services, but only human-facing command sources can create protected approvals.

Verification captures Git HEAD, exact binary diff bytes, and ignored-aware untracked content before and after configured commands. Reports derive from durable state without mutating it.

See ADRs under `docs/adr/` for clean-room, plugin, storage, evidence, and tool-policy decisions.

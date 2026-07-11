# ADR 0006: Ordered Policy Traces and Immutable Rule Ownership

Status: Accepted

Date: 2026-07-11

## Context

Gatehouse must explain every policy outcome while adding project rules, waivers, packs, and configurable failure behavior. If adapters evaluate separate rule sets or configuration can replace core rules, explanations become incomplete and immutable safety can silently weaken. Time-dependent waiver evaluation also becomes nondeterministic if policy code reads the clock internally.

## Decision

Crucible will retain one policy evaluator. It returns an immutable ordered tuple of trace entries and one final stable rule key. Rule precedence is state availability, immutable terminal safety, project deny, project approval, stage mutation, project allow, policy pack, then default. The final trace entry must match the decision's final rule key.

Crucible owns the `terminal.immutable.*` namespace. Configuration and waivers may refer to immutable keys for explanation but can never define, replace, or waive them. Existing v0.1.0 rule keys are frozen as a compatibility set.

Evaluation receives the effective time from its caller whenever expiry matters. The same normalized inputs, configuration, durable state, and supplied time therefore produce the same result and trace.

## Consequences

- Adapters consume and persist the same explanation rather than reconstructing one.
- New rules require a stable key and trace behavior test.
- Trace schemas can evolve additively, but existing keys cannot be silently repurposed.
- Callers own clock acquisition; tests can prove expiry boundaries without patching global time.
- The initial v0.2 contract permits a single matched trace entry for v0.1 behavior; Task 4 expands it to complete ordered evaluation traces.

# Hermes Child-Session API Research for Workcells v0.3.0

**Date:** 2026-07-11  
**Hermes Agent inspected:** `0.18.2` (`2026.7.7.2`, upstream `4281151a`)  
**Decision:** Compatible with a conservative, fail-closed Workcells adapter.

## Public interfaces inspected

The installed public plugin interface is `hermes_cli.plugins.PluginContext`.
Its public methods include `register_tool`, `register_hook`, `register_skill`,
`register_command`, `register_cli_command`, and `dispatch_tool`.
`dispatch_tool` is the documented public plugin interface for dispatching
registered built-in tools such as `delegate_task`; Hardproof can use it without
accessing a parent agent or any private Hermes attribute.

`delegate_task` accepts explicit goal and context fields, supports
configuration-owned delegation model routing, and launches fresh background
subagents with isolated conversation, terminal, and tool contexts. It returns
a launch handle immediately and delivers child output to the live parent as a
new conversation message when the child finishes.

## Capability assessment

| Workcells capability | Public API status | Workcells behavior |
| --- | --- | --- |
| Launch a fresh child with explicit instructions | `dispatch_tool("delegate_task", args)` | Supported |
| Select a model or configured model alias | Hermes delegation configuration | Supported, configuration-owned |
| Obtain a launch handle | `delegate_task` result | Record durably when supplied |
| Observe known-child status | Plugin context | Unavailable; reconcile marks uncertainty durably |
| Wait on a known child | Plugin context | Unavailable; the parent does not poll |
| Cancel a known child | Plugin context | Unavailable; report limitation and require human remediation |
| Retrieve a structured result for a known child | Plugin context | Unavailable; validated result file is the durable handoff |
| Reconnect after parent interruption | Plugin context | Unavailable; never relaunch automatically |
| Reconcile interrupted state | Local ledger + public limitations | Idempotent, fail-closed reconciliation |
| Durable child-process persistence | Public delegation contract | Unavailable; preserve the attempt ledger instead |
| Gateway/non-interactive launch | Requires Hermes parent agent | Diagnose and block safely when unavailable |

## Constraints and fallback

The public `delegate_task` description states that background delegations are
not durable: if the parent session closes or the process exits before
completion, child work is discarded, and stopping the parent cancels running
children. It also says not to wait or poll.

Workcells therefore treats a missing or unobservable child as *uncertain*.
It preserves the attempt, blocks dependents, and requires explicit recovery,
retry, or human escalation. It never infers success, failure, cancellation, or
liveness from missing public status. This is the specified fallback for
unavailable cancellation and reconciliation.

The implementation contains internal subagent registries and lifecycle
machinery, but using those would require framework internals or private state.
That is prohibited. The adapter will use only public dispatch and an internal,
durable ledger; tests use a deterministic fake adapter and make no paid model
calls.

## Compatibility assumptions

Hardproof requires `PluginContext.dispatch_tool` and the built-in public
`delegate_task` tool. Launch is supported only where Hermes provides a parent
agent context. Gateway and non-interactive invocation without that context
must return a stable blocked diagnostic rather than attempting a private
fallback. The versioned child-result file remains untrusted until the parent
validates it against the active attempt.

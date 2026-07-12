# Hermes Child-Session API Research for Workcells v0.3.0

**Date:** 2026-07-11  
**Hermes Agent inspected:** `0.18.2` (`2026.7.7.2`, upstream `4281151a`)  
**Decision:** **NO-GO: REQUIRED PUBLIC HERMES CHILD-SESSION API IS UNAVAILABLE**

## Public interfaces inspected

The installed public plugin interface is `hermes_cli.plugins.PluginContext`.
Its public methods include `register_tool`, `register_hook`, `register_skill`,
`register_command`, `register_cli_command`, and `dispatch_tool`. The latter is
documented as the public plugin interface for dispatching registered built-in
tools such as `delegate_task`; Hardproof can use it without accessing a parent
agent or any private Hermes attribute.

`delegate_task` accepts an explicit goal/context and supports configured
delegation model routing. It launches fresh background subagents with isolated
conversation, terminal, and tool contexts. Its public description says that it
returns a handle immediately and returns child output to the parent as a new
conversation message when the child finishes.

## Capability assessment

| Workcells capability | Public API status | Result |
| --- | --- | --- |
| Launch a fresh child with explicit instructions | `dispatch_tool("delegate_task", args)` | Available |
| Select a model or configured model alias | Hermes delegation configuration | Available, configuration-owned |
| Obtain a launch handle | `delegate_task` result | Available for the live parent session only |
| Observe known-child status | Plugin context | **Unavailable** |
| Wait on a known child | Plugin context | **Unavailable** |
| Cancel a known child | Plugin context | **Unavailable** |
| Retrieve a structured result for a known child | Plugin context | **Unavailable** |
| Reconnect to a known child after parent interruption | Plugin context | **Unavailable** |
| Reconcile interrupted parent/child state | Plugin context | **Unavailable** |
| Durable child-session persistence | Public delegation contract | **Unavailable** |
| Gateway/non-interactive durable operation | Public delegation contract | **Unavailable** |

## Binding incompatibility

The public `delegate_task` description explicitly states that background
delegations are not durable: if the parent session is closed or the process
exits before completion, the child work is discarded, and stopping the parent
cancels every running child. It also says not to wait or poll. That directly
conflicts with Workcells' required durable lifecycle ledger, known-child
status/wait/cancel operations, reconnect/reconcile recovery, and resumable
orchestration.

The implementation contains internal subagent registries and lifecycle
machinery, but using those would require importing framework internals or
reaching through private state. That is prohibited by Hardproof's compatibility
and security boundaries, and is not a fallback.

## Fallback behavior

No safe compatibility fallback exists for the binding release promise. A
plugin may record a local launch intent and accept an untrusted result file,
but it cannot truthfully claim that the child was launched, remains active,
was cancelled, or can be reconciled after interruption. A local process
adapter would likewise not be a Hermes child-session implementation and is
outside the specified public-API boundary.

## Required Hermes capability to unblock

Hardproof v0.3.0 requires a documented public child-session service usable
from `PluginContext` (or an equivalent public plugin API) with launch,
durable child identity, status, wait, cancellation, structured-result
retrieval, and reconnect/reconciliation operations that work in gateway and
non-interactive operation.

Until that API exists, Workcells must not be implemented or released as
specified.

# ADR 0002: Standalone Hermes Plugin Compatibility Boundary

- Status: Accepted
- Date: 2026-07-10

## Context

Crucible must work as a standalone plugin across supported Hermes releases without patching Hermes Agent or depending on private implementation state. The initial environment provides Hermes Agent 0.18.2 on native Windows.

Inspection of `hermes_cli.plugins.PluginContext` and the public hook documentation confirmed all required registration and dispatch capabilities. It also revealed a naming detail that the roadmap's qualified skill list does not express at the call boundary: `register_skill` rejects names containing a colon and adds the plugin namespace itself.

## Decision

All Hermes interaction passes through `crucible_agent.compat`. Registration feature-detects the six required public context methods and fails with a structured compatibility report if any are absent. Optional lifecycle capabilities are reported separately and may degrade without weakening required gates.

Crucible passes bare names such as `orchestrate` to `register_skill`. Hermes then exposes the required public name `crucible:orchestrate`. This is an adapter-level interpretation, not a change to the specified user-facing skill names.

Crucible will not inspect `ctx._cli_ref`, `ctx._manager`, or other private attributes. Hook callbacks accept additive keyword arguments. The compatibility script may inspect the public `PluginContext` type without starting an agent or mutating user configuration.

## Evidence

- Installed distribution: Hermes Agent 0.18.2.
- Required methods: `register_tool`, `register_hook`, `register_skill`, `register_command`, `register_cli_command`, `dispatch_tool`.
- Required hook names are present in the installed `VALID_HOOKS` contract.
- WSL was unavailable in the initial runtime; cross-platform claims remain gated on CI and later compatibility evidence.

## Consequences

- Version-specific adaptation stays out of domain and policy services.
- A missing required capability prevents partial, misleading registration.
- Optional integrations can be diagnosed without pretending they are required core support.
- Compatibility tests use both fake contexts and the installed public Hermes type.

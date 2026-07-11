# Security Model

Hardproof enforces engineering-process policy; it is not a security sandbox. It does not replace operating-system permissions, repository protection, isolated execution, Hermes approvals, or human review.

## Stage-aware mutation

Known file-writing and execution tools are configurable. Before IMPLEMENT, direct project mutation is blocked while writes inside the active run artifact directory remain allowed. IMPLEMENT permits project edits. VERIFY, DELIVER, and LEARN block unrelated source changes until the run returns to IMPLEMENT.

Terminal commands receive additional deterministic classification. Force pushes are always blocked. Destructive operations are blocked or escalated to Hermes human approval according to profile. Deployment is blocked before DELIVER. These rules are conservative guidance over recognizable command forms, not a shell parser or containment boundary.

## Failure behavior

When active Standard or Critical policy state cannot be loaded, known mutation tools fail closed. Quick runs may fail open on state errors as documented by profile policy. No active run leaves Hermes behavior unchanged.

## Audit privacy

Blocks and approval requests record exact rule keys, tool names, argument-key names, and a SHA-256 digest of canonical arguments. Raw arguments, command output, prompts, credentials, cookies, and secret values are not stored in policy events. Post-tool observations record only lifecycle metadata.

## Trust boundary

Project-local configuration and plugins execute with the user's local authority. Hardproof does not make untrusted code safe. Use worktrees, containers, remote backends, OS controls, and protected branches appropriate to the risk.

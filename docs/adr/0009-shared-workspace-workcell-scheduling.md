# ADR 0009: Shared-Workspace Workcell Scheduling

- Status: Accepted
- Date: 2026-07-11

Workcells provides context isolation, not filesystem isolation. The default is
one mutating child at a time. Optional parallelism requires explicit
configuration, known non-overlapping write scopes, a clean expected workspace,
and a bounded concurrency limit. Unknown or overlapping scopes serialize.
Worktree and branch isolation remain out of scope until v0.5.0.

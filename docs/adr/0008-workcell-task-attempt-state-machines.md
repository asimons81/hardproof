# ADR 0008: Workcell Task and Attempt State Machines

- Status: Accepted
- Date: 2026-07-11

Tasks and attempts are separate durable state machines. Tasks move through
`PENDING`, `READY`, `STARTING`, `RUNNING`, `SUCCEEDED`, `BLOCKED`, `FAILED`,
`INTERRUPTED`, `CANCELLED`, and `ESCALATED`. Attempts are immutable after a
terminal outcome; retry creates a new attempt. Every transition is validated,
attributed, timestamped, and appended to the lifecycle ledger. This prevents a
child self-report from becoming authoritative task success.

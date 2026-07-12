# ADR 0010: Workcell Child-Result Validation

- Status: Accepted
- Date: 2026-07-11

Children write a versioned, bounded result document under the run artifact
tree. The parent validates contract version, run/task/attempt/child identity,
paths, size, redaction, and claimed artifacts before deciding a task
transition. Missing, malformed, mismatched, oversized, or stale documents fail
closed. A child result is untrusted input and never verification evidence.

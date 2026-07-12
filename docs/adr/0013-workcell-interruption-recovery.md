# ADR 0013: Workcell Interruption Recovery and Duplicate Prevention

- Status: Accepted
- Date: 2026-07-11

Hermes public delegation does not expose durable status, cancellation, or
reconnection. On restart Workcells preserves the recorded child identity,
marks unobservable work `INTERRUPTED`/recovery-required, blocks dependents,
and requires explicit retry or human escalation. It never infers liveness or
success and never launches a replacement automatically.

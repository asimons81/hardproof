# ADR 0011: Provider-Neutral Workcell Model Tiers

- Status: Accepted
- Date: 2026-07-11

Workcells stores deterministic `economy`, `standard`, and `strong` tiers, not
provider or credential names. Project configuration maps each tier to a Hermes
selector. Profile minimums and retry escalation are checked by Hardproof;
missing mappings block launch with remediation. Children cannot select or alter
their own tier.

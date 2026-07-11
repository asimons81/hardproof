---
name: review
description: Challenge a Crucible implementation during REVIEW against its approved contract, code quality, tests, and risk boundaries.
---

# Challenge the Result

## Purpose
Apply judgment independent from implementation and make blocking findings durable.

## When to use
Use for the REVIEW stage selected by the active run context.

## Inputs
Read the request, approved design and plan, task acceptance notes, complete diff, tests, migrations, documentation, and risk records.

## Procedure
1. Compare observable behavior with the approved contract.
2. Inspect correctness, failure paths, security boundaries, compatibility, maintainability, and test strength.
3. Classify findings by impact and cite concrete files or evidence.
4. Send blocking fixes back to IMPLEMENT and require re-review.
5. Record the review and outcome with `crucible_record`.

## Required records
Standard and Critical runs require a review artifact. Record an approved review outcome only after blocking findings are resolved; a human waiver must use the human command surface.

## Exit criteria
Every blocking finding is fixed or validly waived, review provenance is clear, and the final diff—not an earlier snapshot—was examined.

## Failure modes
Do not review from summaries alone, approve your own unsupported assertions, or bury uncertainty. Return to IMPLEMENT when the code changes.

## Verification
Reinspect fixes and tests, record the final outcome, then call `crucible_transition` for VERIFY.

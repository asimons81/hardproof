---
name: design
description: Shape the smallest reversible Hardproof design from discovery evidence during DESIGN, including contracts, failures, and risks.
---

# Shape the Design

## Purpose
Convert verified discovery into a coherent solution whose consequences can be reviewed before product code changes.

## When to use
Use for the DESIGN stage selected by the active run context.

## Inputs
Use the approved request boundary, discovery artifact, current interfaces, profile requirements, and recorded risks.

## Procedure
1. State the intended behavior and excluded scope.
2. Define public contracts, data ownership, trust boundaries, failure behavior, and rollback implications.
3. Compare viable alternatives and choose the smallest reversible option.
4. Record consequential choices with `hardproof_record` as decisions.
5. Write the design artifact with `hardproof_record`.

## Required records
Standard and Critical runs require a design artifact and a separate human design approval. Model tools cannot create that approval.

## Exit criteria
The design is testable, compatible with inspected APIs, explicit about risks, and ready for human review.

## Failure modes
Return to DISCOVERY when essential facts are missing. Pause if a safe boundary cannot be designed. Do not weaken gates to fit an attractive approach.

## Verification
Cross-check every interface claim and unresolved risk, then ask the human to use `/hardproof approve design`. After approval exists, call `hardproof_transition` for PLAN.

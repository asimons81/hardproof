---
name: orchestrate
description: Coordinate an active Hardproof run across discovery, design, planning, implementation, review, verification, delivery, and learning.
---

# Orchestrate Hardproof

## Purpose
Turn a rough software request into an inspectable result whose completion claim is backed by current evidence.

## When to use
Use when starting, resuming, or coordinating the full active Hardproof protocol rather than performing one stage in isolation.

## Inputs
Begin with `hardproof_run` status, the injected run context, profile, blockers, durable records, current workspace, and required stage skill.

## Procedure
1. Load the stage-specific `hardproof:*` skill named by run context.
2. Keep state in Hardproof records rather than relying on conversation history.
3. Match ceremony to Quick, Standard, or Critical policy without weakening verification.
4. Use `hardproof_record` and `hardproof_task` for durable work products.
5. Request every stage change through `hardproof_transition`; the service, not prose, decides whether gates pass.
6. Use human commands for protected approvals and waivers.

## Required records
Maintain the artifacts, decisions, tasks, review, evidence, risks, approvals, completion report, and learning decision required by the selected profile.

## Exit criteria
The run reaches COMPLETE only after every enforced gate passes against current durable state.

## Failure modes
Pause on missing authority or unsafe boundaries. Return to the appropriate earlier stage when facts, design, code, review, or evidence change.

## Verification
Inspect status and evidence with `hardproof_report`. Treat missing, failed, indeterminate, or stale evidence as incomplete.

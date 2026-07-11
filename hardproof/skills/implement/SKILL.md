---
name: implement
description: Execute approved Hardproof tasks during IMPLEMENT with focused tests, durable task updates, and scope-controlled code changes.
---

# Implement the Plan

## Purpose
Produce the approved behavior in buildable increments while preserving an inspectable task ledger.

## When to use
Use for the IMPLEMENT stage selected by the active run context.

## Inputs
Use approved design and plan records, ready tasks, project guidance, current code, tests, and profile-specific policy.

## Procedure
1. Select a dependency-ready task with `hardproof_task`.
2. Add or identify a failing behavioral test where practical.
3. Make the smallest complete code and documentation change for that task.
4. Run focused checks and inspect the diff.
5. Update the task with acceptance notes through `hardproof_task`.
6. Record consequential deviations with `hardproof_record`; return to DESIGN or PLAN when approval assumptions no longer hold.

## Required records
Keep task status, acceptance evidence, changed scope, and new decisions durable. At least one completed task or recorded change is required before review.

## Exit criteria
Planned implementation tasks are complete or explicitly blocked, the repository remains buildable, and the resulting diff is ready for independent challenge.

## Failure modes
Stop on unsafe mutation, approval gaps, destructive actions, or design drift. Never mark a task complete without acceptance notes.

## Verification
Run task-focused checks, review the actual diff, and call `hardproof_transition` for REVIEW. Full verification evidence belongs to VERIFY.

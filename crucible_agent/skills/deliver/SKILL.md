---
name: deliver
description: Prepare an inspectable Crucible delivery during DELIVER with final scope, evidence, risks, rollback, and reproducible reporting.
---

# Deliver with Evidence

## Purpose
Turn reviewed, verified work into a precise handoff without overstating what was proven.

## When to use
Use for the DELIVER stage selected by the active run context.

## Inputs
Use the final request, stage history, artifacts, decisions, tasks, diff, review outcome, fresh evidence, waivers, risks, and publication constraints.

## Procedure
1. Confirm evidence still matches the workspace.
2. Summarize behavior and changed files in user terms.
3. State tests, platforms, compatibility evidence, limitations, and unresolved risks exactly.
4. Include rollback instructions, especially for Critical work.
5. Generate the completion draft with `crucible_report` and record it through `crucible_record` when required.

## Required records
Every run requires a completion artifact. Critical runs also require explicit rollback, unresolved-risk material, and later human completion approval.

## Exit criteria
The report is deterministic, secret-safe, project-relative, and supported by fresh evidence.

## Failure modes
Return to VERIFY when evidence is stale or missing. Do not claim publication, platform support, or clean installation without direct evidence.

## Verification
Reopen the generated report and linked evidence, then call `crucible_transition` for LEARN.

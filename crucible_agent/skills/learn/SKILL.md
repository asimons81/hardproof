---
name: learn
description: Close a Crucible run during LEARN by capturing safe provenance-linked lessons or recording an explicit reason to skip them.
---

# Learn from the Run

## Purpose
Decide deliberately whether completed work contains reusable project knowledge without silently changing user instructions or skills.

## When to use
Use for the LEARN stage selected by the active run context.

## Inputs
Read decisions, corrections, review findings, evidence, remaining risks, and the completion report.

## Procedure
1. Identify lessons that are specific, reusable, and supported by the run.
2. Exclude secrets, private output, transient failures, and guesses.
3. Record a learning artifact with `crucible_record`, including source-run provenance and intended scope.
4. If nothing qualifies, record an explicit skip reason rather than inventing a lesson.
5. Do not create or edit global knowledge automatically.

## Required records
Standard and Critical require a learning artifact or explicit skip reason. Quick may skip with a recorded reason when its profile path requires one.

## Exit criteria
The learning decision is durable, privacy-safe, and linked to evidence. Critical also has a human completion approval.

## Failure modes
Do not persist credentials, raw private content, unsupported generalizations, or duplicate guidance. Leave proposals reviewable.

## Verification
Confirm provenance and redaction, then call `crucible_transition` for COMPLETE. Never declare completion only in prose.

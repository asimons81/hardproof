---
name: verify
description: Prove a Crucible implementation during VERIFY by running configured checks and evaluating fresh workspace-bound evidence.
---

# Prove the Workspace State

## Purpose
Tie completion claims to explicit successful checks executed against the current Git workspace snapshot.

## When to use
Use for the VERIFY stage selected by the active run context.

## Inputs
Use configured verification checks, profile requirements, current review outcome, Git state, and existing evidence records.

## Procedure
1. Inspect which required checks are configured and missing.
2. Invoke `crucible_verify`; do not substitute an unrecorded terminal run.
3. Treat timeouts, malformed results, unknown exit status, or workspace changes during execution as non-passing.
4. Inspect stored redacted output and address failures in IMPLEMENT.
5. Rerun checks after every code change that makes evidence stale.

## Required records
Quick and Standard require at least one fresh passing check; Critical requires at least two. Evidence must include an explicit zero exit code and matching workspace identity.

## Exit criteria
All profile-required evidence is fresh, passing, and attributable to the final workspace state.

## Failure modes
Never infer success from reassuring output, stale evidence, a missing exit code, or a prior commit. Return to IMPLEMENT for fixes and REVIEW when the diff changes materially.

## Verification
Use `crucible_report` to inspect evidence freshness, then call `crucible_transition` for DELIVER.

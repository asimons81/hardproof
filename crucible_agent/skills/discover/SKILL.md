---
name: discover
description: Inspect a Crucible run's request, repository, constraints, and unknowns during DISCOVERY before proposing a design.
---

# Discover the Work

## Purpose
Establish what is true in the current workspace and what the request actually requires.

## When to use
Use for the DISCOVERY stage selected by the active run context.

## Inputs
Read the request, profile, repository state, applicable project guidance, prior run records, and inspected public interfaces.

## Procedure
1. Inspect relevant code, tests, configuration, history, and documentation.
2. Separate observed facts from assumptions.
3. Identify user-visible outcomes, compatibility constraints, security boundaries, and unresolved questions.
4. Keep scope tied to the request; do not choose an implementation yet.
5. Record the findings with `crucible_record` as a discovery artifact.

## Required records
Record inspected evidence, constraints, scope boundaries, and open questions. Standard and Critical profiles require a discovery artifact.

## Exit criteria
Discovery is ready when the design can be evaluated against explicit facts and no blocking question is hidden.

## Failure modes
Pause when required evidence is unavailable. Do not invent current behavior, private Hermes APIs, approvals, or external facts.

## Verification
Recheck cited paths and commands against the current workspace, then call `crucible_transition` for DESIGN. Never claim the stage changed in prose.

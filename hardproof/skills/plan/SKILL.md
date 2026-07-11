---
name: plan
description: Turn an approved Hardproof design into dependency-aware, independently testable tasks during PLAN without editing product code.
---

# Plan the Implementation

## Purpose
Create an executable task sequence that preserves the approved design and makes progress inspectable.

## When to use
Use for the PLAN stage selected by the active run context.

## Inputs
Read the design, design approval, repository conventions, affected files, tests, migrations, documentation, and risk profile.

## Procedure
1. Decompose work into coherent tasks with observable outcomes.
2. Name dependencies, likely files, risk, and acceptance checks.
3. Include documentation and migration work with the behavior they describe.
4. Add each task through `hardproof_task`.
5. Record the complete plan through `hardproof_record`.

## Required records
Standard and Critical runs require a plan artifact, durable task records, and a separate human plan approval.

## Exit criteria
Every required outcome maps to a task, dependencies are acyclic, and each task can be verified without relying on confidence.

## Failure modes
Return to DESIGN if planning exposes a contract flaw. Do not create vague tasks, omit release work, or grant approval through a model tool.

## Verification
Check task coverage and dependency order, then ask the human to use `/hardproof approve plan`. After approval exists, call `hardproof_transition` for IMPLEMENT.

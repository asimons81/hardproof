# ADR 0001: Clean-Room Implementation and Working-Name Boundary

- Status: Accepted
- Date: 2026-07-10
- Decision owners: Crucible maintainers

## Context

Crucible coordinates a staged software-engineering process for Hermes Agent. Other agent workflow projects explore related ideas, so the repository needs a durable originality boundary. The working name also overlaps with existing commercial uses and has not completed trademark or marketplace clearance.

The project needs a permissive open-source license suitable for independent contributors and downstream commercial use while preserving a meaningful patent grant.

## Decision

Crucible will be designed and implemented as a clean-room project from its own specification and current, documented public Hermes Agent APIs.

Superpowers is credited only as conceptual inspiration. Contributors must not copy or adapt its source code, skill prose, prompts, test fixtures, diagrams, templates, repository layout, or documentation wording. Reviewers will treat suspicious namespace, phrasing, or structural reuse as a release blocker until independently resolved.

"Crucible" remains a working name until trademark and marketplace clearance is complete. Public materials will use the distinct identifiers `crucible-agent`, `crucible_agent`, and `crucible`, will avoid Atlassian trade dress and terminology, and will state that no Atlassian affiliation is implied.

The project is licensed under Apache License 2.0. Its permissive terms support broad adoption, and its explicit patent license and termination provisions provide clearer patent protection for contributors and users than a permissive license without a patent grant.

## Consequences

- Every feature and document must have an independently traceable origin in Crucible requirements or public Hermes contracts.
- Contract tests reject prohibited upstream namespaces in package and skill paths.
- Brand clearance remains an external publication gate, not a reason to stop technical development.
- Source distributions must include the Apache-2.0 license and this notice.
- Any future change to the license or brand boundary requires a public ADR and legal review.

"""Stable v0.1.0 profile semantics."""

from __future__ import annotations

from dataclasses import dataclass

from crucible_agent.domain.enums import ApprovalGate, ArtifactKind, RunProfile


@dataclass(frozen=True, slots=True)
class ProfilePolicy:
    profile: RunProfile
    required_artifacts: frozenset[ArtifactKind]
    required_approvals: frozenset[ApprovalGate]
    minimum_verification_checks: int
    requires_review: bool
    requires_learning_decision: bool
    fail_closed_on_state_error: bool


PROFILE_POLICIES: dict[RunProfile, ProfilePolicy] = {
    RunProfile.QUICK: ProfilePolicy(
        RunProfile.QUICK,
        frozenset({ArtifactKind.COMPLETION}),
        frozenset(),
        1,
        False,
        False,
        False,
    ),
    RunProfile.STANDARD: ProfilePolicy(
        RunProfile.STANDARD,
        frozenset({
            ArtifactKind.DISCOVERY, ArtifactKind.DESIGN, ArtifactKind.PLAN,
            ArtifactKind.REVIEW, ArtifactKind.COMPLETION,
        }),
        frozenset({ApprovalGate.DESIGN, ApprovalGate.PLAN}),
        1,
        True,
        True,
        True,
    ),
    RunProfile.CRITICAL: ProfilePolicy(
        RunProfile.CRITICAL,
        frozenset({
            ArtifactKind.DISCOVERY, ArtifactKind.DESIGN, ArtifactKind.PLAN,
            ArtifactKind.REVIEW, ArtifactKind.COMPLETION, ArtifactKind.RISK,
        }),
        frozenset({ApprovalGate.DESIGN, ApprovalGate.PLAN, ApprovalGate.COMPLETION}),
        2,
        True,
        True,
        True,
    ),
}


def policy_for(profile: RunProfile) -> ProfilePolicy:
    return PROFILE_POLICIES[RunProfile(profile)]

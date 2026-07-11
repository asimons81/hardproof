"""Verification gate helpers shared by transitions and pre-completion checks."""

from __future__ import annotations

from crucible_agent.domain.enums import EvidenceStatus, RunProfile
from crucible_agent.domain.models import Evidence
from crucible_agent.policy.profiles import policy_for


def passing_check_names(evidence: tuple[Evidence, ...]) -> frozenset[str]:
    """Return checks whose latest recorded result is fresh and passing."""
    latest: dict[str, Evidence] = {}
    for item in sorted(evidence, key=lambda record: (record.completed_at, record.id)):
        latest[item.check_name] = item
    return frozenset(
        name for name, item in latest.items()
        if item.status is EvidenceStatus.PASSED and item.exit_code == 0
    )


def verification_blocker(profile: RunProfile, evidence: tuple[Evidence, ...]) -> str | None:
    required = policy_for(profile).minimum_verification_checks
    found = len(passing_check_names(evidence))
    if found < required:
        return f"{required} fresh passing verification check{'s' if required != 1 else ''} required; found {found}"
    return None

"""Human-authority approval creation boundary."""

from __future__ import annotations

from hardproof.domain.enums import ApprovalGate
from hardproof.domain.models import Approval, new_id, utc_now
from hardproof.policy.stage_rules import HUMAN_APPROVAL_SOURCES, NON_HUMAN_ACTORS
from hardproof.storage.repository import RunRepository


class ApprovalService:
    def __init__(self, repository: RunRepository) -> None:
        self.repository = repository

    def create_human(
        self,
        run_id: str,
        gate: ApprovalGate,
        *,
        actor: str,
        source: str,
        reason: str | None = None,
    ) -> Approval:
        if source.lower() not in HUMAN_APPROVAL_SOURCES or actor.lower() in NON_HUMAN_ACTORS:
            raise PermissionError("approval requires an attributable human-facing command source")
        if gate is ApprovalGate.WAIVER and not (reason or "").strip():
            raise ValueError("waiver approval requires a reason")
        approval = Approval(new_id("approval"), run_id, gate, actor, source, reason, utc_now())
        self.repository.add_approval(approval)
        self.repository.append_event(
            run_id,
            "approval_created",
            {"approval_id": approval.id, "actor": actor, "gate": gate.value, "source": source},
        )
        return approval

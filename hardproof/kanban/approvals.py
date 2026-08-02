"""TP-06: Human approval gates for kanban tasks."""
from hardproof.domain.enums import ApprovalGate
from hardproof.services.approvals import ApprovalService
from hardproof.storage.repository import RunRepository

class KanbanApprovalGate:
    def __init__(self, repo: RunRepository):
        self.service = ApprovalService(repo)

    def require_design_approval(self, task_id: str, actor: str, source: str, reason: str | None = None) -> None:
        self.service.create_human(task_id, ApprovalGate.DESIGN, actor=actor, source=source, reason=reason)

    def require_plan_approval(self, task_id: str, actor: str, source: str, reason: str | None = None) -> None:
        self.service.create_human(task_id, ApprovalGate.PLAN, actor=actor, source=source, reason=reason)

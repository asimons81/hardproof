"""Stable-key decision ledger with supersession audit events."""

from __future__ import annotations

from hardproof.domain.models import Decision, new_id, utc_now
from hardproof.storage.repository import RunRepository


class DecisionService:
    def __init__(self, repository: RunRepository) -> None:
        self.repository = repository

    def record(
        self,
        run_id: str,
        key: str,
        question: str,
        choice: str,
        rationale: str,
        status: str,
    ) -> Decision:
        prior = next((item for item in self.repository.list_decisions(run_id) if item.key == key), None)
        decision = Decision(
            new_id("decision"), run_id, key, question, choice, rationale, status, utc_now()
        )
        self.repository.upsert_decision(decision)
        if prior is not None:
            self.repository.append_event(
                run_id,
                "decision_superseded",
                {"key": key, "previous_id": prior.id, "replacement_id": decision.id},
            )
        else:
            self.repository.append_event(
                run_id, "decision_recorded", {"decision_id": decision.id, "key": key}
            )
        return decision

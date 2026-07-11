"""Run lifecycle service that persists only policy-approved transitions."""

from __future__ import annotations

from hardproof.domain.enums import RunProfile, RunStage
from hardproof.domain.models import Run, TransitionResult
from hardproof.domain.transitions import FORWARD_STAGE
from hardproof.errors import TransitionError
from hardproof.policy.stage_rules import TransitionFacts, evaluate_transition
from hardproof.storage.repository import RunRepository
from hardproof.policy.stage_graph import StageGraph, compile_stage_graph
from typing import Any


class RunService:
    def __init__(
        self, repository: RunRepository, stage_graph: StageGraph | None = None,
        *, stage_graph_config: dict[str, Any] | None = None,
    ) -> None:
        self.repository = repository
        self.stage_graph = stage_graph
        self.stage_graph_config = stage_graph_config

    def try_transition(
        self,
        run_id: str,
        target: RunStage,
        facts: TransitionFacts,
        *,
        reason: str,
        skip_reason: str | None = None,
    ) -> TransitionResult:
        run = self.repository.get_run(run_id)
        graph = self.stage_graph
        if self.stage_graph_config is not None:
            graph = compile_stage_graph(self.stage_graph_config, profile=run.profile)
        result = evaluate_transition(run, target, facts, skip_reason=skip_reason, stage_graph=graph)
        if not result.allowed:
            return result
        audit_events: tuple[tuple[str, dict[str, object]], ...] = ()
        if run.profile is RunProfile.QUICK and target is not FORWARD_STAGE.get(run.stage):
            audit_events = ((
                "stages_skipped",
                {"from_stage": run.stage.value, "to_stage": target.value, "reason": skip_reason},
            ),)
        self.repository.transition_run(
            run_id, target, reason=reason, audit_events=audit_events
        )
        return result

    def transition(
        self,
        run_id: str,
        target: RunStage,
        facts: TransitionFacts,
        *,
        reason: str,
        skip_reason: str | None = None,
    ) -> Run:
        result = self.try_transition(
            run_id, target, facts, reason=reason, skip_reason=skip_reason
        )
        if not result.allowed:
            raise TransitionError("; ".join(result.blockers))
        return self.repository.get_run(run_id)

    def pause(self, run_id: str, *, reason: str) -> Run:
        return self.transition(run_id, RunStage.PAUSED, TransitionFacts(), reason=reason)

    def resume(self, run_id: str, *, reason: str) -> Run:
        run = self.repository.get_run(run_id)
        if run.stage is not RunStage.PAUSED:
            raise TransitionError("only a paused run can resume")
        prior_stage: RunStage | None = None
        for event in reversed(self.repository.list_events(run_id)):
            if event.event_type == "stage_transitioned" and event.payload.get("to_stage") == "PAUSED":
                prior_stage = RunStage(str(event.payload["from_stage"]))
                break
        if prior_stage is None or prior_stage in {RunStage.PAUSED, RunStage.ABORTED, RunStage.COMPLETE}:
            raise TransitionError("paused run has no valid durable resume stage")
        return self.repository.transition_run(run_id, prior_stage, reason=reason)

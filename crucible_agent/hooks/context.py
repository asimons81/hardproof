"""Compact deterministic pre-turn context for active Crucible runs."""

from __future__ import annotations

from typing import Any, Callable

from crucible_agent.commands.shared import CommandService
from crucible_agent.constants import MAX_CONTEXT_CHARACTERS
from crucible_agent.domain.enums import RunStage
from crucible_agent.domain.transitions import FORWARD_STAGE
from crucible_agent.policy.stage_rules import evaluate_transition
from crucible_agent.services.sessions import SessionService


STAGE_SKILLS = {
    RunStage.INTAKE: "orchestrate",
    RunStage.DISCOVERY: "discover",
    RunStage.DESIGN: "design",
    RunStage.PLAN: "plan",
    RunStage.IMPLEMENT: "implement",
    RunStage.REVIEW: "review",
    RunStage.VERIFY: "verify",
    RunStage.DELIVER: "deliver",
    RunStage.LEARN: "learn",
    RunStage.PAUSED: "orchestrate",
}


class ContextHook:
    def __init__(self, sessions: SessionService, commands: CommandService) -> None:
        self.sessions = sessions
        self.commands = commands
        self.cache: dict[str, str] = {}

    def clear(self, session_id: str | None = None) -> None:
        if session_id is None:
            self.cache.clear()
        else:
            self.cache.pop(session_id, None)

    def __call__(self, **kwargs: Any) -> dict[str, str] | None:
        session_id = str(kwargs.get("session_id") or "")
        if not session_id:
            return None
        run = self.sessions.resolve(session_id, str(kwargs.get("platform") or "") or None)
        if run is None:
            self.clear(session_id)
            return None
        self.cache[session_id] = run.id
        blockers: tuple[str, ...]
        if run.stage is RunStage.PAUSED:
            next_action = "Resume the paused run"
            blockers = ("Run is paused",)
        else:
            target = FORWARD_STAGE.get(run.stage)
            if target is None:
                return None
            result = evaluate_transition(
                run, target, self.commands.transition_facts(run.id)
            )
            blockers = result.blockers
            next_action = (
                f"Resolve: {blockers[0]}" if blockers
                else f"Call crucible_transition for {target.value}"
            )
        skill = STAGE_SKILLS[run.stage]
        blocked = "; ".join(blockers) if blockers else "None from durable gate state"
        text = "\n".join((
            "CRUCIBLE RUN ACTIVE",
            f"Run: {run.id}",
            f"Profile: {run.profile.value}",
            f"Stage: {run.stage.value}",
            f"Required next action: {next_action}",
            f"Blocked actions: {blocked}",
            f"Open blockers: {blocked}",
            f'Required skill: skill_view("crucible:{skill}")',
        ))
        return {"context": text[:MAX_CONTEXT_CHARACTERS]}


HookBundle = tuple[ContextHook, "SessionHooks"]


def register_context_hooks(ctx: Any, bundle_factory: Callable[[], HookBundle]) -> None:
    bundle: HookBundle | None = None

    def get() -> HookBundle:
        nonlocal bundle
        if bundle is None:
            bundle = bundle_factory()
        return bundle

    ctx.register_hook("pre_llm_call", lambda **kwargs: get()[0](**kwargs))
    ctx.register_hook("on_session_start", lambda **kwargs: get()[1].on_session_start(**kwargs))
    ctx.register_hook("on_session_finalize", lambda **kwargs: get()[1].on_session_finalize(**kwargs))
    ctx.register_hook("on_session_reset", lambda **kwargs: get()[1].on_session_reset(**kwargs))


from crucible_agent.hooks.sessions import SessionHooks  # noqa: E402  # break annotation cycle

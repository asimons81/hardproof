"""Hermes pre/post tool hooks backed by deterministic Hardproof policy."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from hardproof.commands.shared import CommandService
from hardproof.config import config_fingerprint, load_config
from hardproof.domain.enums import RunProfile
from hardproof.domain.models import PolicyDecisionRecord, new_id, utc_now
from hardproof.policy.tool_rules import ToolPolicyContext, evaluate_tool_call
from hardproof.services.sessions import SessionService
from hardproof.services.waivers import WaiverService


class ToolPolicyHook:
    def __init__(self, sessions: SessionService, commands: CommandService) -> None:
        self.sessions = sessions
        self.commands = commands
        self.last_profiles: dict[str, RunProfile] = {}
        self.last_failure_modes: dict[str, str] = {}

    @staticmethod
    def _audit_summary(args: Any) -> dict[str, Any]:
        safe = args if isinstance(args, dict) else {}
        canonical = json.dumps(safe, sort_keys=True, separators=(",", ":"), default=str)
        return {
            "argument_keys": sorted(str(key) for key in safe),
            "arguments_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        }

    def _resolve(self, session_id: str, platform: str | None) -> ToolPolicyContext | None:
        run = self.sessions.resolve(session_id, platform)
        if run is None:
            return None
        self.last_profiles[session_id] = run.profile
        config = load_config(self.commands.paths.config)
        effective_time = utc_now()
        waiver_service = WaiverService(self.commands.repository)
        waiver_service.expire_due(effective_time)
        self.last_failure_modes[session_id] = config.policy.state_failure_mode
        return ToolPolicyContext(
            run,
            self.commands.context.project_root,
            self.commands.paths.run_directory(run.id),
            frozenset(config.mutating_tools),
            policy=config.policy,
            config_sha256=config_fingerprint(config),
            waivers=self.commands.repository.list_applicable_waivers(run.id),
            effective_time=effective_time,
        )

    def pre_tool_call(self, **kwargs: Any) -> dict[str, str] | None:
        session_id = str(kwargs.get("session_id") or "")
        tool_name = str(kwargs.get("tool_name") or "")
        raw_args = kwargs.get("args")
        args: dict[str, Any] = raw_args if isinstance(raw_args, dict) else {}
        try:
            context = self._resolve(session_id, str(kwargs.get("platform") or "") or None)
            decision = evaluate_tool_call(tool_name, args, context)
        except Exception:
            decision = evaluate_tool_call(
                tool_name, args, None, state_error=True,
                profile_hint=self.last_profiles.get(session_id, RunProfile.STANDARD),
                failure_mode=self.last_failure_modes.get(session_id, "profile"),
            )
            context = None
        run_id = context.run.id if context is not None else None
        persistence_failed = False
        if context is not None:
            audit = self._audit_summary(args)
            try:
                self.commands.repository.add_policy_decision(
                    PolicyDecisionRecord(
                        new_id("policy"), context.run.id, tool_name, decision.action,
                        decision.rule_key, decision.reason, decision.trace,
                        str(audit["arguments_sha256"]), context.config_sha256,
                        decision.waiver_id, None, utc_now(),
                    )
                )
            except Exception:
                persistence_failed = True
        if (
            persistence_failed
            and context is not None
            and decision.action == "allow"
            and tool_name in context.mutating_tools
            and context.run.profile in {RunProfile.STANDARD, RunProfile.CRITICAL}
        ):
            decision = evaluate_tool_call(
                tool_name, args, None, state_error=True,
                profile_hint=context.run.profile, failure_mode="closed",
            )
        if decision.action == "allow":
            return None
        if run_id and decision.action != "allow":
            try:
                self.commands.repository.append_event(
                    run_id,
                    "tool_policy_decision",
                    {
                        "action": decision.action,
                        "rule_key": decision.rule_key,
                        "tool_name": tool_name,
                        **self._audit_summary(args),
                    },
                )
            except Exception:
                pass
        if decision.action == "approval":
            return {
                "action": "approve",
                "message": decision.reason,
                "rule_key": f"hardproof:{decision.rule_key}",
            }
        return {"action": "block", "message": f"{decision.reason} Rule: {decision.rule_key}."}

    def post_tool_call(self, **kwargs: Any) -> None:
        session_id = str(kwargs.get("session_id") or "")
        try:
            context = self._resolve(session_id, str(kwargs.get("platform") or "") or None)
        except Exception:
            return
        if context is None:
            return
        raw_args = kwargs.get("args")
        args: dict[str, Any] = raw_args if isinstance(raw_args, dict) else {}
        duration = kwargs.get("duration_ms")
        self.commands.repository.append_event(
            context.run.id,
            "tool_observed",
            {
                "tool_name": str(kwargs.get("tool_name") or ""),
                "status": str(kwargs.get("status") or "unknown"),
                "duration_ms": float(duration) if isinstance(duration, (int, float)) else None,
                **self._audit_summary(args),
            },
        )


def register_tool_policy_hooks(ctx: Any, hook_factory: Callable[[], ToolPolicyHook]) -> None:
    hook: ToolPolicyHook | None = None

    def get() -> ToolPolicyHook:
        nonlocal hook
        if hook is None:
            hook = hook_factory()
        return hook

    ctx.register_hook("pre_tool_call", lambda **kwargs: get().pre_tool_call(**kwargs))
    ctx.register_hook("post_tool_call", lambda **kwargs: get().post_tool_call(**kwargs))

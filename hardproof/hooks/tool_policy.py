"""Hermes pre/post tool hooks backed by deterministic Hardproof policy."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from hardproof.commands.shared import CommandService
from hardproof.config import load_config
from hardproof.domain.enums import RunProfile
from hardproof.policy.tool_rules import ToolPolicyContext, evaluate_tool_call
from hardproof.services.sessions import SessionService


class ToolPolicyHook:
    def __init__(self, sessions: SessionService, commands: CommandService) -> None:
        self.sessions = sessions
        self.commands = commands
        self.last_profiles: dict[str, RunProfile] = {}

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
        return ToolPolicyContext(
            run,
            self.commands.context.project_root,
            self.commands.paths.run_directory(run.id),
            frozenset(config.mutating_tools),
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
            )
            context = None
        if decision.action == "allow":
            return None
        run_id = context.run.id if context is not None else None
        if run_id:
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

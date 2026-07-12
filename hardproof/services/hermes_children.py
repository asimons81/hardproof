"""Public-Hermes child session adapter for Workcells."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol


class ChildLaunchError(RuntimeError):
    """Public Hermes delegation could not create a child session."""


@dataclass(frozen=True, slots=True)
class ChildLaunch:
    handle: str
    child_session_id: str | None
    model_tier: str
    raw: dict[str, object]


class ChildSessionAdapter(Protocol):
    def launch(self, brief: str, context: str, model_tier: str) -> ChildLaunch: ...


class HermesChildAdapter:
    """Use only the documented PluginContext dispatch surface."""

    def __init__(self, context: Any) -> None:
        self.context = context

    def launch(self, brief: str, context: str, model_tier: str) -> ChildLaunch:
        if not brief.strip() or not context.strip() or not model_tier.strip():
            raise ValueError("Workcell child launch requires brief, context, and model tier")
        try:
            raw = self.context.dispatch_tool(
                "delegate_task", {"goal": brief, "context": context, "role": "leaf"}
            )
        except Exception as exc:
            raise ChildLaunchError("public Hermes child launch failed") from exc
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError as exc:
            raise ChildLaunchError("public Hermes child launch returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ChildLaunchError("public Hermes child launch returned invalid data")
        if isinstance(payload.get("error"), str):
            raise ChildLaunchError(f"public Hermes child launch refused: {payload['error']}")
        result = payload
        if isinstance(payload.get("results"), list) and payload["results"]:
            candidate = payload["results"][0]
            if isinstance(candidate, dict):
                result = candidate
        handle = result.get("handle") or result.get("task_id") or result.get("id")
        if not isinstance(handle, str) or not handle.strip():
            raise ChildLaunchError("public Hermes child launch did not return a handle")
        child = result.get("child_session_id")
        return ChildLaunch(
            handle, child if isinstance(child, str) and child.strip() else None,
            model_tier, {str(key): value for key, value in result.items()},
        )


class FakeHermesChildAdapter:
    """Deterministic child adapter for all automated Workcells tests."""

    def __init__(self) -> None:
        self.launches: tuple[tuple[str, str, str], ...] = ()

    def launch(self, brief: str, context: str, model_tier: str) -> ChildLaunch:
        if not brief.strip() or not context.strip() or not model_tier.strip():
            raise ValueError("Workcell child launch requires brief, context, and model tier")
        self.launches += ((brief, context, model_tier),)
        number = len(self.launches)
        handle = f"fake-handle-{number}"
        child = f"fake-child-{number}"
        return ChildLaunch(handle, child, model_tier, {"handle": handle, "child_session_id": child})

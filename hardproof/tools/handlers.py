"""Bounded JSON tool handlers with injected run services."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

from hardproof.commands.shared import CommandService
from hardproof.domain.enums import ArtifactKind, RiskLevel, RunStage, TaskStatus
from hardproof.domain.models import utc_now
from hardproof.services.artifacts import ArtifactService
from hardproof.services.decisions import DecisionService
from hardproof.services.tasks import TaskService
from hardproof.services.risks import RiskService
from hardproof.tools.schemas import TOOL_SCHEMAS


logger = logging.getLogger(__name__)
ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]
_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|authorization|cookie)\s*[:=]\s*\S+")


def _not_configured(name: str) -> dict[str, Any]:
    return {"ok": False, "error": f"{name} service is not configured in this build stage"}


@dataclass(frozen=True, slots=True)
class HandlerDependencies:
    command_service: CommandService
    verify: ToolHandler = lambda args: _not_configured("verification")
    report: ToolHandler = lambda args: _not_configured("report")
    maximum_response_characters: int = 8_000
    spill: Callable[[str], str] | None = None


def _bounded(
    payload: dict[str, Any], maximum: int, spill: Callable[[str], str] | None = None
) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    if len(serialized) <= maximum:
        return serialized
    preview_size = max(0, maximum - 120)
    bounded: dict[str, Any] = {
        "ok": bool(payload.get("ok", False)),
        "truncated": True,
        "preview": serialized[:preview_size],
    }
    if spill is not None:
        bounded["output_path"] = spill(serialized)
    result = json.dumps(bounded, sort_keys=True, separators=(",", ":"))
    while len(result) > maximum and bounded["preview"]:
        bounded["preview"] = bounded["preview"][:-32]
        result = json.dumps(bounded, sort_keys=True, separators=(",", ":"))
    return result


def _error(exc: Exception) -> dict[str, Any]:
    logger.info("Hardproof tool request failed: %s", type(exc).__name__)
    message = _SECRET.sub(lambda match: match.group(1) + "=[REDACTED]", str(exc))
    return {"ok": False, "error": message or type(exc).__name__}


def _task_payload(task: Any) -> dict[str, Any]:
    return {
        "key": task.task_key,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "risk": task.risk.value,
        "dependencies": list(task.dependencies),
        "acceptance": list(task.acceptance),
        "files": list(task.files),
        "acceptance_notes": task.acceptance_notes,
    }


def create_handlers(dependencies: HandlerDependencies) -> dict[str, Callable[..., str]]:
    service = dependencies.command_service

    def wrap(operation: ToolHandler) -> Callable[..., str]:
        def handler(args: dict[str, Any], **kwargs: Any) -> str:
            del kwargs
            try:
                payload = operation(args if isinstance(args, dict) else {})
            except Exception as exc:
                payload = _error(exc)
            return _bounded(payload, dependencies.maximum_response_characters, dependencies.spill)
        return handler

    def run(args: dict[str, Any]) -> dict[str, Any]:
        action = args.get("action")
        if action == "start":
            result = service.execute(["start", args.get("profile", "standard"), args.get("request", "")])
        elif action == "status":
            result = service.execute(["status"])
        elif action == "pause":
            result = service.execute(["pause", args.get("reason", "model requested pause")])
        elif action == "resume":
            argv = ["resume"] + ([args["run_id"]] if args.get("run_id") else [])
            result = service.execute(argv)
        elif action == "abort":
            result = service.execute(["abort", args.get("reason", "model requested abort")])
        elif action == "workcells_status":
            result = service.execute(["workcells", "status"])
            return {"ok": result.ok, "workcells": json.loads(result.text)}
        elif action == "workcells_reconcile":
            attempt_id = str(args.get("attempt_id", ""))
            if not attempt_id:
                raise ValueError("workcells_reconcile requires attempt_id")
            result = service.execute(["workcells", "reconcile", attempt_id])
            return {"ok": result.ok, "message": result.text}
        else:
            raise ValueError(f"unknown hardproof_run action: {action}")
        current = service.repository.get_run(result.run_id or service.active_run_id())
        return {
            "ok": result.ok, "run_id": current.id, "profile": current.profile.value,
            "stage": current.stage.value, "status": current.status.value, "message": result.text,
        }

    def record(args: dict[str, Any]) -> dict[str, Any]:
        kind = str(args.get("kind", ""))
        if kind in {"approval", "waiver"}:
            return {"ok": False, "error": "Human approvals and waivers require /hardproof approve or /hardproof waive."}
        run_id = service.active_run_id()
        content = str(args.get("content", ""))
        raw_metadata = args.get("metadata")
        metadata: dict[str, Any] = raw_metadata if isinstance(raw_metadata, dict) else {}
        if kind == "decision":
            decision = DecisionService(service.repository).record(
                run_id,
                str(metadata.get("key") or args.get("title") or "decision"),
                str(metadata.get("question") or args.get("title") or "Decision"),
                str(metadata.get("choice") or content),
                str(metadata.get("rationale") or content),
                str(metadata.get("status") or "accepted"),
            )
            return {"ok": True, "kind": "decision", "key": decision.key, "status": decision.status}
        kind_map = {
            "artifact": ArtifactKind.OTHER, "discovery": ArtifactKind.DISCOVERY,
            "design": ArtifactKind.DESIGN, "plan": ArtifactKind.PLAN,
            "review": ArtifactKind.REVIEW, "learning": ArtifactKind.LEARNING,
            "risk": ArtifactKind.RISK,
        }
        if kind not in kind_map:
            if "approv" in kind.lower() or "waiv" in kind.lower():
                return {"ok": False, "error": "Human approvals and waivers require /hardproof approve or /hardproof waive."}
            raise ValueError(f"unknown hardproof_record kind: {kind}")
        artifact_kind = kind_map[kind]
        path = str(args.get("path") or f"{artifact_kind.value}.md")
        run_directory = service.paths.run_directory(run_id)
        artifact = ArtifactService(service.repository, run_directory).write(
            run_id, artifact_kind, path, content
        )
        if artifact_kind is ArtifactKind.REVIEW and str(metadata.get("outcome", "")).lower() == "approved":
            service.repository.append_event(run_id, "review_approved", {"path": artifact.path})
        if artifact_kind is ArtifactKind.LEARNING and str(metadata.get("skipped", "")).lower() == "true":
            service.repository.append_event(run_id, "learning_skipped", {"reason": content[:500]})
        return {"ok": True, "kind": artifact.kind.value, "path": artifact.path, "sha256": artifact.sha256}

    def task(args: dict[str, Any]) -> dict[str, Any]:
        action = args.get("action")
        run_id = service.active_run_id()
        tasks = TaskService(service.repository)
        if action == "create":
            item = tasks.create(
                run_id, str(args.get("key", "")), str(args.get("title", "")),
                str(args.get("description", "")), RiskLevel(args.get("risk", "medium")),
                dependencies=tuple(args.get("dependencies") or ()),
                acceptance=tuple(args.get("acceptance") or ()), files=tuple(args.get("files") or ()),
            )
            suggestion = RiskService(service.repository).suggest(
                run_id,
                text=f"{item.title}\n{item.description}",
                files=item.files,
                task_id=item.id,
                now=utc_now(),
            )
            return {
                "ok": True,
                "task": _task_payload(item),
                "risk_suggestion": {
                    "id": suggestion.id,
                    "suggested_risk": suggestion.suggested_risk.value,
                    "reasons": list(suggestion.reasons),
                    "decision_required": True,
                    "selected_task_risk_unchanged": item.risk.value,
                },
            }
        if action == "update":
            status = TaskStatus(args["status"]) if args.get("status") else None
            item = tasks.update(
                run_id, str(args.get("key", "")), status=status,
                dependencies=tuple(args["dependencies"]) if "dependencies" in args else None,
                acceptance_notes=args.get("acceptance_notes"),
            )
            return {"ok": True, "task": _task_payload(item)}
        all_tasks = service.repository.list_tasks(run_id)
        if action == "list":
            return {"ok": True, "tasks": [_task_payload(item) for item in all_tasks]}
        if action == "get":
            found = next((candidate for candidate in all_tasks if candidate.task_key == args.get("key")), None)
            if found is None:
                raise LookupError(f"task not found: {args.get('key')}")
            return {"ok": True, "task": _task_payload(found)}
        if action == "workcell_graph":
            result = service.execute(["task", "graph"])
            return {"ok": result.ok, "graph": json.loads(result.text)}
        if action == "workcell_attempts":
            task_id = str(args.get("task_id") or args.get("key") or "")
            if not task_id:
                raise ValueError("workcell_attempts requires task_id")
            result = service.execute(["task", "attempts", task_id])
            return {"ok": result.ok, "attempts": json.loads(result.text)}
        raise ValueError(f"unknown hardproof_task action: {action}")

    def transition(args: dict[str, Any]) -> dict[str, Any]:
        run_id = service.active_run_id()
        run = service.run_service.transition(
            run_id, RunStage(str(args.get("target_stage"))), service.transition_facts(run_id),
            reason=str(args.get("reason", "")), skip_reason=args.get("skip_reason"),
        )
        return {"ok": True, "run_id": run.id, "stage": run.stage.value, "status": run.status.value}

    return {
        "hardproof_run": wrap(run),
        "hardproof_record": wrap(record),
        "hardproof_task": wrap(task),
        "hardproof_transition": wrap(transition),
        "hardproof_verify": wrap(dependencies.verify),
        "hardproof_report": wrap(dependencies.report),
    }


def register_tools(ctx: Any, dependency_factory: Callable[[], HandlerDependencies]) -> None:
    for name, schema in TOOL_SCHEMAS.items():
        def handler(args: dict[str, Any], _name: str = name, **kwargs: Any) -> str:
            return create_handlers(dependency_factory())[_name](args, **kwargs)

        ctx.register_tool(
            name=name,
            toolset="hardproof",
            schema=schema,
            handler=handler,
            description=str(schema["description"]),
            emoji="🔥",
        )

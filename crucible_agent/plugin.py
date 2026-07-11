"""Hermes plugin registration entry point."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from crucible_agent.commands.cli import register_cli
from crucible_agent.commands.shared import CommandContext, CommandService
from crucible_agent.commands.slash import register_slash
from crucible_agent.compat import require_compatible
from crucible_agent.config import load_config
from crucible_agent.hooks.context import ContextHook, register_context_hooks
from crucible_agent.hooks.sessions import SessionHooks
from crucible_agent.hooks.tool_policy import ToolPolicyHook, register_tool_policy_hooks
from crucible_agent.hooks.verification import VerificationHook, register_verification_hook
from crucible_agent.services.evidence import EvidenceService, HermesCommandRunner
from crucible_agent.services.sessions import SessionService
from crucible_agent.services.reports import ReportService
from crucible_agent.services.risks import classify_risk
from crucible_agent.tools.handlers import HandlerDependencies, register_tools


SKILL_NAMES = (
    "orchestrate", "discover", "design", "plan", "implement",
    "review", "verify", "deliver", "learn",
)

SKILL_DESCRIPTIONS = {
    "orchestrate": "Coordinate an active Crucible run across all durable engineering stages.",
    "discover": "Inspect request, repository, constraints, and unknowns during DISCOVERY.",
    "design": "Shape a reversible solution from discovery evidence during DESIGN.",
    "plan": "Turn an approved design into dependency-aware tasks during PLAN.",
    "implement": "Execute approved tasks with focused tests during IMPLEMENT.",
    "review": "Challenge implementation, tests, and risks during REVIEW.",
    "verify": "Run checks and evaluate fresh workspace-bound evidence during VERIFY.",
    "deliver": "Prepare an evidence-backed completion handoff during DELIVER.",
    "learn": "Capture safe provenance-linked lessons or an explicit skip during LEARN.",
}


def register_skills(ctx: Any) -> None:
    root = Path(__file__).parent / "skills"
    for name in SKILL_NAMES:
        ctx.register_skill(name, root / name / "SKILL.md", SKILL_DESCRIPTIONS[name])


def register(ctx: Any) -> None:
    """Register Crucible with Hermes.

    Registration is populated task-by-task as the public compatibility,
    command, tool, hook, and skill surfaces are implemented.
    """
    require_compatible(ctx)
    register_slash(
        ctx,
        lambda: CommandService(CommandContext(
            Path.cwd(), actor="interactive-user", source="slash", hermes_context=ctx
        )),
    )
    register_cli(
        ctx,
        lambda: CommandService(CommandContext(
            Path.cwd(), actor="interactive-user", source="cli", hermes_context=ctx
        )),
    )
    def tool_dependencies() -> HandlerDependencies:
        command_service = CommandService(CommandContext(
            Path.cwd(), actor="model", source="tool", hermes_context=ctx
        ))
        def verify(args: dict[str, Any]) -> dict[str, Any]:
            config = load_config(command_service.paths.config)
            run_id = command_service.active_run_id()
            evidence_service = EvidenceService(
                command_service.repository,
                command_service.context.project_root,
                command_service.paths.run_directory(run_id),
                HermesCommandRunner(ctx),
                maximum_stored_output_size=config.maximum_stored_output_size,
            )
            records = evidence_service.verify(
                run_id,
                checks=tuple(args.get("checks") or ()) or None,
                all_required=bool(args.get("all_required", True)),
                timeout_override=args.get("timeout_override"),
            )
            return {
                "ok": all(item.status.value == "passed" for item in records),
                "evidence": [
                    {
                        "check": item.check_name, "exit_code": item.exit_code,
                        "output_path": item.output_path, "status": item.status.value,
                    }
                    for item in records
                ],
            }

        def report(args: dict[str, Any]) -> dict[str, Any]:
            action = str(args.get("action", "status"))
            if action == "risk_suggest":
                assessment = classify_risk(
                    text=str(args.get("text", "")),
                    files=tuple(str(item) for item in (args.get("files") or ())),
                    command=str(args["command"]) if args.get("command") else None,
                )
                return {
                    "ok": True, "action": action,
                    "suggested_risk": assessment.level.value,
                    "reasons": list(assessment.reasons),
                    "advisory": True,
                }
            if action == "policy_explain":
                raw_arguments = args.get("arguments")
                arguments = raw_arguments if isinstance(raw_arguments, dict) else {}
                sequence = args.get("event_sequence")
                explanation = command_service.explain_policy(
                    event_sequence=int(sequence) if sequence is not None else None,
                    tool_name=str(args["tool_name"]) if args.get("tool_name") else None,
                    args=arguments,
                )
                return {"ok": True, "action": action, "explanation": explanation}
            if action in {"export", "completion"}:
                run_id = command_service.active_run_id()
                paths = ReportService(
                    command_service.repository,
                    command_service.context.project_root,
                    command_service.paths.run_directory(run_id),
                ).export(
                    run_id,
                    destination=args.get("path"),
                    format=str(args.get("format") or "both"),
                )
                return {
                    "ok": True, "action": action, "run_id": run_id,
                    "paths": {key: str(path) for key, path in paths.items()},
                }
            result = command_service.execute([action])
            return {"ok": result.ok, "action": action, "message": result.text, "run_id": result.run_id}

        def spill(content: str) -> str:
            run_id = command_service.active_run_id()
            logs = command_service.paths.run_directory(run_id) / "logs"
            logs.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            destination = logs / f"tool-response-{digest}.json"
            temporary = destination.with_suffix(".tmp")
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, destination)
            return destination.relative_to(command_service.context.project_root).as_posix()

        return HandlerDependencies(
            command_service=command_service, verify=verify, report=report, spill=spill
        )

    register_tools(ctx, tool_dependencies)
    register_skills(ctx)

    def context_bundle() -> tuple[ContextHook, SessionHooks]:
        command_service = CommandService(CommandContext(
            Path.cwd(), actor="model", source="hook", hermes_context=ctx
        ))
        sessions = SessionService(command_service.repository, command_service.paths)
        context_hook = ContextHook(sessions, command_service)
        return context_hook, SessionHooks(sessions, context_hook)

    register_context_hooks(ctx, context_bundle)

    def policy_hook() -> ToolPolicyHook:
        command_service = CommandService(CommandContext(
            Path.cwd(), actor="model", source="hook", hermes_context=ctx
        ))
        return ToolPolicyHook(
            SessionService(command_service.repository, command_service.paths), command_service
        )

    register_tool_policy_hooks(ctx, policy_hook)

    def verification_hook() -> VerificationHook:
        command_service = CommandService(CommandContext(
            Path.cwd(), actor="model", source="hook", hermes_context=ctx
        ))
        config = load_config(command_service.paths.config)
        evidence = EvidenceService(
            command_service.repository,
            command_service.context.project_root,
            command_service.paths.runs / "__hook_unbound__",
            HermesCommandRunner(ctx),
            maximum_stored_output_size=config.maximum_stored_output_size,
        )
        return VerificationHook(
            SessionService(command_service.repository, command_service.paths),
            command_service,
            evidence,
        )

    register_verification_hook(ctx, verification_hook)

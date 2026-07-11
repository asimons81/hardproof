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

        def report(args: dict[str, Any]) -> dict[str, Any]:
            action = str(args.get("action", "status"))
            command = "export" if action in {"export", "completion"} else action
            argv = [command] + ([str(args["path"])] if args.get("path") and command == "export" else [])
            result = command_service.execute(argv)
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

        return HandlerDependencies(command_service=command_service, report=report, spill=spill)

    register_tools(ctx, tool_dependencies)
    register_skills(ctx)

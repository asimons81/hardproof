"""Hermes plugin registration entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crucible_agent.commands.cli import register_cli
from crucible_agent.commands.shared import CommandContext, CommandService
from crucible_agent.commands.slash import register_slash
from crucible_agent.compat import require_compatible


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

"""Hermes `/crucible` adapter."""

from __future__ import annotations

import shlex
from collections.abc import Awaitable
from typing import Any, Callable

from crucible_agent.commands.shared import CommandService


def make_slash_handler(
    service_factory: Callable[[], CommandService],
) -> Callable[[str], Awaitable[str]]:
    async def handler(raw_args: str) -> str:
        try:
            argv = shlex.split(raw_args, posix=True)
            result = service_factory().execute(argv)
            return result.text
        except Exception as exc:
            return f"Crucible error: {exc}"[:499]

    return handler


def register_slash(ctx: Any, service_factory: Callable[[], CommandService]) -> None:
    ctx.register_command(
        "crucible",
        make_slash_handler(service_factory),
        description="Manage a persistent Crucible engineering run",
        args_hint="<subcommand> [arguments]",
    )

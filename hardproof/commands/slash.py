"""Hermes `/hardproof` adapter."""

from __future__ import annotations

import shlex
from collections.abc import Awaitable
from typing import Any, Callable

from hardproof.commands.shared import CommandService


def make_slash_handler(
    service_factory: Callable[[], CommandService],
) -> Callable[[str], Awaitable[str]]:
    async def handler(raw_args: str) -> str:
        try:
            argv = shlex.split(raw_args, posix=True)
            result = service_factory().execute(argv)
            return result.text
        except Exception as exc:
            return f"Hardproof error: {exc}"[:499]

    return handler


def register_slash(ctx: Any, service_factory: Callable[[], CommandService]) -> None:
    ctx.register_command(
        "hardproof",
        make_slash_handler(service_factory),
        description="Manage a persistent Hardproof engineering run",
        args_hint="<subcommand> [arguments]",
    )

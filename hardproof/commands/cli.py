"""`hermes hardproof` argparse adapter."""

from __future__ import annotations

import argparse
from typing import Any, Callable

from hardproof.commands.shared import CommandService


def _configure(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="hardproof_command", required=True)
    start = sub.add_parser("start")
    start.add_argument("profile", choices=("quick", "standard", "critical"))
    start.add_argument("request", nargs="+")
    sub.add_parser("status")
    approve = sub.add_parser("approve")
    approve.add_argument("gate", choices=("design", "plan", "completion"))
    approve.add_argument("reason", nargs="*")
    waive = sub.add_parser("waive")
    waive.add_argument("gate")
    waive.add_argument("reason", nargs="+")
    pause = sub.add_parser("pause")
    pause.add_argument("reason", nargs="*")
    resume = sub.add_parser("resume")
    resume.add_argument("run_id", nargs="?")
    abort = sub.add_parser("abort")
    abort.add_argument("reason", nargs="+")
    sub.add_parser("evidence")
    export = sub.add_parser("export")
    export.add_argument("path", nargs="?")
    sub.add_parser("doctor")
    sub.add_parser("runs")
    show = sub.add_parser("show")
    show.add_argument("run_id")
    config = sub.add_parser("config").add_subparsers(dest="config_command", required=True)
    config.add_parser("init")
    config.add_parser("validate")
    db = sub.add_parser("db").add_subparsers(dest="db_command", required=True)
    db.add_parser("migrate")
    policy = sub.add_parser("policy")
    policy.add_argument("policy_args", nargs=argparse.REMAINDER)
    sub.add_parser("complete")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes hardproof")
    _configure(parser)
    return parser


def _to_argv(args: argparse.Namespace) -> list[str]:
    command = args.hardproof_command
    if command == "start":
        return [command, args.profile, *args.request]
    if command == "approve":
        return [command, args.gate, *args.reason]
    if command == "waive":
        return [command, args.gate, *args.reason]
    if command in {"pause", "abort"}:
        return [command, *args.reason]
    if command == "resume":
        return [command, *([args.run_id] if args.run_id else [])]
    if command == "export":
        return [command, *([args.path] if args.path else [])]
    if command == "show":
        return [command, args.run_id]
    if command == "config":
        return [command, args.config_command]
    if command == "db":
        return [command, args.db_command]
    if command == "policy":
        return [command, *args.policy_args]
    return [command]


def run_cli(
    args: argparse.Namespace,
    *,
    service_factory: Callable[[], CommandService],
) -> str:
    try:
        return service_factory().execute(_to_argv(args)).text
    except Exception as exc:
        return f"Hardproof error: {exc}"[:499]


def register_cli(ctx: Any, service_factory: Callable[[], CommandService]) -> None:
    def handler(args: argparse.Namespace) -> str:
        return run_cli(args, service_factory=service_factory)

    ctx.register_cli_command(
        "hardproof",
        "Manage persistent Hardproof engineering runs",
        _configure,
        handler,
        description="Start, inspect, approve, pause, verify, and export Hardproof runs",
    )

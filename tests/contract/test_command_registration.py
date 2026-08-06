from pathlib import Path

from hardproof.commands.cli import build_parser, register_cli
from hardproof.commands.shared import CommandContext, CommandService
from hardproof.commands.slash import register_slash
from hardproof.plugin import register

import pytest


def _service_factory(root: Path):
    if not (root / ".git").exists():
        import subprocess

        subprocess.run(["git", "init", "-q", str(root)], check=True)
    context = CommandContext(root, actor="test-user", source="cli", session_id="session-1")
    return lambda: CommandService(context)


class FakeContext:
    def __init__(self) -> None:
        self.slash: tuple | None = None
        self.cli: tuple | None = None

    def register_command(self, *args: object, **kwargs: object) -> None:
        self.slash = (args, kwargs)

    def register_cli_command(self, *args: object, **kwargs: object) -> None:
        self.cli = (args, kwargs)

    def register_tool(self, *args: object, **kwargs: object) -> None: ...
    def register_hook(self, *args: object, **kwargs: object) -> None: ...
    def register_skill(self, *args: object, **kwargs: object) -> None: ...
    def dispatch_tool(self, *args: object, **kwargs: object) -> str: return "{}"

    @property
    def profile_name(self) -> str:
        return "default"


def test_registers_one_hardproof_slash_and_cli_command() -> None:
    context = FakeContext()
    register_slash(context, lambda: None)  # type: ignore[arg-type]
    register_cli(context, lambda: None)  # type: ignore[arg-type]
    assert context.slash is not None and context.slash[0][0] == "hardproof"
    assert context.cli is not None and context.cli[0][0] == "hardproof"


def test_plugin_entrypoint_wires_both_human_command_surfaces() -> None:
    context = FakeContext()
    register(context)
    assert context.slash is not None
    assert context.cli is not None


def test_cli_handler_prints_report_and_returns_int_exit_code(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """P2-1 regression: the `hermes hardproof` handler must print to stdout and
    return an int so Hermes dispatch does not swallow the output."""
    context = FakeContext()
    register_cli(context, _service_factory(tmp_path))
    assert context.cli is not None
    handler = context.cli[0][3]
    assert callable(handler)
    args = build_parser().parse_args(["runs"])
    rc = handler(args)
    captured = capsys.readouterr()
    assert isinstance(rc, int)
    assert rc == 0
    assert "No Hardproof runs found" in captured.out


def test_cli_handler_returns_nonzero_on_hardproof_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """P2-1 regression: errors must surface on stderr with a non-zero exit code."""
    context = FakeContext()
    register_cli(context, _service_factory(tmp_path))
    assert context.cli is not None
    handler = context.cli[0][3]
    assert callable(handler)
    # `abort` without an active run raises an error through the shared service.
    args = build_parser().parse_args(["abort", "no-active-run"])
    rc = handler(args)
    captured = capsys.readouterr()
    assert isinstance(rc, int)
    assert rc != 0
    assert "Hardproof error" in captured.err

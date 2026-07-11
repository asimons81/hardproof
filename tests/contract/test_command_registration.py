from hardproof.commands.cli import register_cli
from hardproof.commands.slash import register_slash
from hardproof.plugin import register


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

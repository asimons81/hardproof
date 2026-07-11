from hardproof.tools.handlers import HandlerDependencies, register_tools


class FakeContext:
    def __init__(self) -> None:
        self.tools: list[dict] = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)


def test_all_six_tools_register_under_hardproof_toolset() -> None:
    context = FakeContext()
    register_tools(context, lambda: HandlerDependencies(None))  # type: ignore[arg-type]
    assert len(context.tools) == 6
    assert {item["name"] for item in context.tools} == {
        "hardproof_run", "hardproof_record", "hardproof_task",
        "hardproof_transition", "hardproof_verify", "hardproof_report",
    }
    assert {item["toolset"] for item in context.tools} == {"hardproof"}

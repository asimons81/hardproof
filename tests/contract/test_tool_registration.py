from crucible_agent.tools.handlers import HandlerDependencies, register_tools


class FakeContext:
    def __init__(self) -> None:
        self.tools: list[dict] = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)


def test_all_six_tools_register_under_crucible_toolset() -> None:
    context = FakeContext()
    register_tools(context, lambda: HandlerDependencies(None))  # type: ignore[arg-type]
    assert len(context.tools) == 6
    assert {item["name"] for item in context.tools} == {
        "crucible_run", "crucible_record", "crucible_task",
        "crucible_transition", "crucible_verify", "crucible_report",
    }
    assert {item["toolset"] for item in context.tools} == {"crucible"}

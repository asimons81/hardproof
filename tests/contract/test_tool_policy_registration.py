from crucible_agent.hooks.tool_policy import register_tool_policy_hooks


class FakeContext:
    def __init__(self) -> None:
        self.hooks = []

    def register_hook(self, name, callback):
        self.hooks.append(name)


def test_registers_pre_and_post_tool_hooks() -> None:
    context = FakeContext()
    register_tool_policy_hooks(context, lambda: None)  # type: ignore[arg-type]
    assert context.hooks == ["pre_tool_call", "post_tool_call"]

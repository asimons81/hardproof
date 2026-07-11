from hardproof.hooks.context import register_context_hooks


class FakeContext:
    def __init__(self) -> None:
        self.hooks: list[str] = []

    def register_hook(self, name, callback):
        self.hooks.append(name)


def test_task_11_registers_context_and_session_hooks() -> None:
    context = FakeContext()
    register_context_hooks(context, lambda: None)  # type: ignore[arg-type]
    assert context.hooks == [
        "pre_llm_call", "on_session_start", "on_session_finalize", "on_session_reset"
    ]

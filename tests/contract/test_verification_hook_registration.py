from hardproof.hooks.verification import register_verification_hook


class Context:
    def __init__(self):
        self.hooks = []

    def register_hook(self, name, callback):
        self.hooks.append(name)


def test_registers_pre_verify_hook() -> None:
    context = Context()
    register_verification_hook(context, lambda: None)  # type: ignore[arg-type]
    assert context.hooks == ["pre_verify"]

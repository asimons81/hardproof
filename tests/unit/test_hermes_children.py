from __future__ import annotations

import json

from hardproof.services.hermes_children import FakeHermesChildAdapter, HermesChildAdapter


class Context:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def dispatch_tool(self, name: str, args: dict[str, object]) -> str:
        self.calls.append((name, args))
        return json.dumps({"results": [{"handle": "handle-1", "child_session_id": "child-1"}]})


def test_public_adapter_launches_fresh_leaf_with_explicit_brief_and_context() -> None:
    context = Context()
    result = HermesChildAdapter(context).launch("Implement task", "Read brief.md", "standard")
    assert result.child_session_id == "child-1"
    assert result.handle == "handle-1"
    assert context.calls == [("delegate_task", {"goal": "Implement task", "context": "Read brief.md", "role": "leaf"})]


def test_fake_adapter_is_deterministic_and_does_not_call_models() -> None:
    adapter = FakeHermesChildAdapter()
    first = adapter.launch("Implement task", "brief", "standard")
    second = adapter.launch("Implement task", "brief", "standard")
    assert first.child_session_id == "fake-child-1"
    assert second.child_session_id == "fake-child-2"
    assert adapter.launches == (("Implement task", "brief", "standard"),) * 2

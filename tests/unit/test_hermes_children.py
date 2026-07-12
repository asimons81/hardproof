from __future__ import annotations

import json

import pytest

from hardproof.services.hermes_children import ChildLaunchError, FakeHermesChildAdapter, HermesChildAdapter


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


def test_public_adapter_requires_non_empty_inputs() -> None:
    context = Context()
    adapter = HermesChildAdapter(context)
    with pytest.raises(ValueError, match="brief, context, and model tier"):
        adapter.launch("", "context", "standard")
    with pytest.raises(ValueError, match="brief, context, and model tier"):
        adapter.launch("brief", "", "standard")
    with pytest.raises(ValueError, match="brief, context, and model tier"):
        adapter.launch("brief", "context", "")


def test_public_adapter_raises_on_dispatch_failure() -> None:
    class BrokenContext:
        def dispatch_tool(self, name: str, args: dict[str, object]) -> str:
            raise RuntimeError("network failure")
    adapter = HermesChildAdapter(BrokenContext())
    with pytest.raises(ChildLaunchError, match="child launch failed"):
        adapter.launch("Implement", "context", "standard")


def test_public_adapter_raises_on_invalid_response() -> None:
    class BadResponseContext:
        def dispatch_tool(self, name: str, args: dict[str, object]) -> str:
            return "not even json"
    adapter = HermesChildAdapter(BadResponseContext())
    with pytest.raises(ChildLaunchError, match="invalid JSON"):
        adapter.launch("Implement", "context", "standard")


def test_public_adapter_raises_on_missing_handle() -> None:
    class NoHandleContext:
        def dispatch_tool(self, name: str, args: dict[str, object]) -> str:
            return json.dumps({"results": [{}]})
    adapter = HermesChildAdapter(NoHandleContext())
    with pytest.raises(ChildLaunchError, match="did not return a handle"):
        adapter.launch("Implement", "context", "standard")


def test_public_adapter_raises_on_refusal() -> None:
    class RefusalContext:
        def dispatch_tool(self, name: str, args: dict[str, object]) -> str:
            return json.dumps({"error": "rate limited"})
    adapter = HermesChildAdapter(RefusalContext())
    with pytest.raises(ChildLaunchError, match="refused"):
        adapter.launch("Implement", "context", "standard")

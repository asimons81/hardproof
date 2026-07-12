from __future__ import annotations

import json

import pytest

from hardproof.compat import CompatibilityError, inspect_context, require_compatible
from importlib import metadata


class CompleteContext:
    profile_name = "default"

    def register_tool(self, *args: object, **kwargs: object) -> None: ...
    def register_hook(self, *args: object, **kwargs: object) -> None: ...
    def register_skill(self, *args: object, **kwargs: object) -> None: ...
    def register_command(self, *args: object, **kwargs: object) -> None: ...
    def register_cli_command(self, *args: object, **kwargs: object) -> None: ...
    def dispatch_tool(self, *args: object, **kwargs: object) -> str: return "{}"


def test_complete_context_reports_required_capabilities() -> None:
    report = inspect_context(CompleteContext(), distribution_version="0.18.2")
    assert report.compatible is True
    assert report.hermes_version == "0.18.2"
    assert report.missing_required == ()
    payload = json.loads(report.to_json())
    assert all(payload["required"].values())
    assert payload["profile_name"] == "default"


def test_missing_required_capability_refuses_registration() -> None:
    context = CompleteContext()
    context.dispatch_tool = None  # type: ignore[method-assign]  # type: ignore[assignment]
    report = inspect_context(context)
    assert report.compatible is False
    assert report.missing_required == ("dispatch_tool",)
    with pytest.raises(CompatibilityError, match="dispatch_tool"):
        require_compatible(context)


def test_private_cli_reference_is_never_inspected() -> None:
    class GuardedContext(CompleteContext):
        def __getattribute__(self, name: str) -> object:
            if name == "_cli_ref":
                raise AssertionError("private Hermes state was inspected")
            return super().__getattribute__(name)

    assert inspect_context(GuardedContext()).compatible


def test_optional_lifecycle_capabilities_are_separate() -> None:
    report = inspect_context(CompleteContext())
    assert report.optional == {
        "kanban_lifecycle_hooks": False,
        "subagent_lifecycle_hooks": False,
    }


def test_installed_version_returns_none_when_package_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Covers compat.py lines 53-54: PackageNotFoundError path."""
    def fake_version(name: str) -> str:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "version", fake_version)
    report = inspect_context(CompleteContext())
    assert report.hermes_version is None

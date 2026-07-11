"""Public Hermes compatibility boundary.

This module uses capability detection only. It deliberately avoids Hermes
private attributes and keeps version drift out of Crucible's domain services.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from importlib import metadata
from typing import Any


REQUIRED_CAPABILITIES = (
    "register_tool",
    "register_hook",
    "register_skill",
    "register_command",
    "register_cli_command",
    "dispatch_tool",
)

OPTIONAL_CAPABILITIES = (
    "subagent_lifecycle_hooks",
    "kanban_lifecycle_hooks",
)


class CompatibilityError(RuntimeError):
    """Raised when Hermes lacks a required public plugin capability."""


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    """Serializable result of inspecting a Hermes plugin context."""

    compatible: bool
    hermes_version: str | None
    profile_name: str
    required: dict[str, bool]
    optional: dict[str, bool]
    missing_required: tuple[str, ...]

    def to_json(self) -> str:
        """Return deterministic JSON suitable for doctor output."""
        return json.dumps(asdict(self), sort_keys=True)


def _installed_version() -> str | None:
    try:
        return metadata.version("hermes-agent")
    except metadata.PackageNotFoundError:
        return None


def inspect_context(
    ctx: Any,
    *,
    distribution_version: str | None = None,
) -> CompatibilityReport:
    """Inspect only Crucible's documented public Hermes surface."""
    required = {
        name: callable(getattr(ctx, name, None)) for name in REQUIRED_CAPABILITIES
    }
    # Hermes 0.18.x exposes these as hook names rather than context methods.
    # Task 2 reports them conservatively; later releases feature-detect the
    # lifecycle events during registration without relying on private state.
    optional = {name: False for name in OPTIONAL_CAPABILITIES}
    missing = tuple(name for name, present in required.items() if not present)
    profile = getattr(ctx, "profile_name", "default")
    return CompatibilityReport(
        compatible=not missing,
        hermes_version=distribution_version or _installed_version(),
        profile_name=profile if isinstance(profile, str) else "default",
        required=required,
        optional=optional,
        missing_required=missing,
    )


def require_compatible(ctx: Any) -> CompatibilityReport:
    """Return a report or refuse unsafe partial plugin registration."""
    report = inspect_context(ctx)
    if not report.compatible:
        missing = ", ".join(report.missing_required)
        raise CompatibilityError(f"Hermes is missing required public capabilities: {missing}")
    return report

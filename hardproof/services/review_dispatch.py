"""Specialized reviewer dispatch for Challenge Chamber (CC-06)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .hermes_children import ChildLaunch, HermesChildAdapter


@dataclass(frozen=True, slots=True)
class ReviewerSpec:
    name: str
    brief: str
    model_tier: str


class ReviewerDispatch:
    """Launch specialized reviewers via public delegate_task."""

    REVIEWER_SPECS = [
        ReviewerSpec("security", "Security audit: vulns, secrets, authz, deps", "stack.coding.large"),
        ReviewerSpec("architecture", "Arch review: modularity, coupling, boundaries", "stack.coding.large"),
        ReviewerSpec("tests", "Test coverage, edge cases, determinism", "stack.coding.medium"),
    ]

    def __init__(self, context: Any) -> None:
        self.adapter = HermesChildAdapter(context)

    def launch_reviewers(self, context: str) -> list[ChildLaunch]:
        launches: list[ChildLaunch] = []
        for spec in self.REVIEWER_SPECS:
            launch = self.adapter.launch(spec.brief, context, spec.model_tier)
            launches.append(launch)
        return launches

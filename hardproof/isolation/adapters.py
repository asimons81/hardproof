"""Backend adapter protocol for v0.5.0 Isolation (Docker, SSH)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BackendLaunch:
    handle: str
    backend: str
    raw: dict[str, object]


class BackendAdapter(Protocol):
    def launch(self, brief: str, context: str, model_tier: str) -> BackendLaunch: ...

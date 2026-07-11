"""Human-authorized waiver lifecycle over the durable repository."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from hardproof.domain.enums import RunProfile, RunStage
from hardproof.domain.models import Waiver, new_id
from hardproof.policy.waivers import WaiverScope, is_protected_rule, match_waiver
from hardproof.services.authority import require_human
from hardproof.services.evidence import redact_output
from hardproof.storage.repository import RunRepository


_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class WaiverService:
    def __init__(self, repository: RunRepository) -> None:
        self.repository = repository

    def create_human(
        self,
        *,
        run_id: str | None,
        name: str,
        rule_key: str,
        rationale: str,
        actor: str,
        source: str,
        created_at: str,
        expires_at: str,
        tool_name: str | None = None,
        command_sha256: str | None = None,
        path_scope: str | None = None,
        profile: RunProfile | None = None,
        stage: RunStage | None = None,
    ) -> Waiver:
        require_human(actor, source, "policy waiver mutation")
        if not _NAME.fullmatch(name):
            raise ValueError("waiver name must use lowercase letters, numbers, and hyphens")
        if is_protected_rule(rule_key):
            raise ValueError(f"protected policy rule cannot be waived: {rule_key}")
        if path_scope is not None:
            normalized = PurePosixPath(path_scope.replace("\\", "/"))
            if normalized.is_absolute() or ".." in normalized.parts:
                raise ValueError("waiver path scope must be project-relative without traversal")
        waiver = Waiver(
            new_id("waiver"), run_id, name, rule_key, tool_name, command_sha256,
            path_scope, profile, stage, redact_output(rationale), actor, source,
            created_at, expires_at,
        )
        self.repository.add_waiver(waiver)
        return waiver

    def get(self, name: str) -> Waiver:
        return self.repository.get_waiver(name)

    def list(self, run_id: str | None = None) -> tuple[Waiver, ...]:
        return self.repository.list_waivers(run_id)

    def list_applicable(self, run_id: str) -> tuple[Waiver, ...]:
        return self.repository.list_applicable_waivers(run_id)

    def revoke_human(
        self, name: str, *, actor: str, source: str, reason: str, now: str
    ) -> Waiver:
        require_human(actor, source, "policy waiver mutation")
        if not reason.strip():
            raise ValueError("waiver revocation requires a reason")
        return self.repository.revoke_waiver(
            name, actor, source, redact_output(reason), now
        )

    def expire_due(self, now: str) -> tuple[str, ...]:
        return self.repository.expire_due_waivers(now)


__all__ = ["WaiverScope", "WaiverService", "match_waiver"]

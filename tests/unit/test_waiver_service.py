from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hardproof.commands.shared import CommandContext, CommandService
from hardproof.domain.enums import RunProfile, RunStage
from hardproof.services.waivers import WaiverService, WaiverScope, match_waiver


NOW = "2026-07-11T20:00:00.000Z"
LATER = "2026-07-12T20:00:00Z"
AFTER = "2026-07-13T20:00:00Z"


def commands_at(tmp_path: Path, *, actor: str = "person", source: str = "cli") -> CommandService:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    commands = CommandService(CommandContext(tmp_path, actor=actor, source=source))
    commands.execute(["start", "standard", "waiver test"])
    return commands


def test_human_can_create_and_revoke_durable_scoped_waiver(tmp_path: Path) -> None:
    commands = commands_at(tmp_path)
    service = WaiverService(commands.repository)
    waiver = service.create_human(
        run_id=commands.active_run_id(), name="generated-write",
        rule_key="stage.before_implement.source_mutation", rationale="reviewed generator",
        actor="person", source="cli", created_at=NOW, expires_at=LATER,
        tool_name="write_file", path_scope="generated/**",
        profile=RunProfile.STANDARD, stage=RunStage.DESIGN,
    )
    scope = WaiverScope(
        waiver.rule_key, "write_file", None, "generated/client.py",
        RunProfile.STANDARD, RunStage.DESIGN, waiver.run_id, NOW,
    )
    assert match_waiver((waiver,), scope) == waiver
    assert match_waiver((waiver,), WaiverScope(
        waiver.rule_key, "write_file", None, "src/client.py",
        RunProfile.STANDARD, RunStage.DESIGN, waiver.run_id, NOW,
    )) is None

    revoked = service.revoke_human("generated-write", actor="person", source="cli", reason="done", now=NOW)
    assert revoked.revoked_at == NOW
    assert match_waiver((revoked,), scope) is None
    events = commands.repository.list_waiver_events(waiver.id)
    assert [item.event_type for item in events] == ["created", "revoked"]
    reopened = WaiverService(commands.repository).get("generated-write")
    assert reopened == revoked


def test_expiry_boundary_is_caller_supplied_and_audited_once(tmp_path: Path) -> None:
    commands = commands_at(tmp_path)
    service = WaiverService(commands.repository)
    waiver = service.create_human(
        run_id=None, name="temporary", rule_key="project.temporary", rationale="one day",
        actor="person", source="slash", created_at=NOW, expires_at=LATER,
    )
    before = WaiverScope(waiver.rule_key, None, None, None, RunProfile.QUICK, RunStage.INTAKE, "run-x", NOW)
    at_expiry = WaiverScope(waiver.rule_key, None, None, None, RunProfile.QUICK, RunStage.INTAKE, "run-x", LATER)
    assert match_waiver((waiver,), before) == waiver
    assert match_waiver((waiver,), at_expiry) is None
    assert service.expire_due(AFTER) == (waiver.id,)
    assert service.expire_due(AFTER) == ()
    assert [item.event_type for item in commands.repository.list_waiver_events(waiver.id)] == [
        "created", "expired",
    ]


@pytest.mark.parametrize("actor,source", [("model", "cli"), ("person", "tool"), ("agent", "gateway")])
def test_nonhuman_authority_cannot_mutate_waivers(
    tmp_path: Path, actor: str, source: str
) -> None:
    commands = commands_at(tmp_path, actor=actor, source=source)
    service = WaiverService(commands.repository)
    with pytest.raises(PermissionError, match="human"):
        service.create_human(
            run_id=commands.active_run_id(), name="denied", rule_key="project.denied",
            rationale="no", actor=actor, source=source, created_at=NOW, expires_at=LATER,
        )


@pytest.mark.parametrize(
    "rule_key",
    [
        "terminal.immutable.force_push", "state.unavailable.fail_closed",
        "evidence.freshness", "verification.required", "migration.schema",
        "approval.authenticity.human",
    ],
)
def test_protected_rule_namespaces_cannot_be_waived(tmp_path: Path, rule_key: str) -> None:
    commands = commands_at(tmp_path)
    with pytest.raises(ValueError, match="protected"):
        WaiverService(commands.repository).create_human(
            run_id=commands.active_run_id(), name="protected", rule_key=rule_key,
            rationale="unsafe", actor="person", source="cli", created_at=NOW, expires_at=LATER,
        )


def test_lifecycle_rationales_are_redacted_before_storage(tmp_path: Path) -> None:
    commands = commands_at(tmp_path)
    service = WaiverService(commands.repository)
    waiver = service.create_human(
        run_id=commands.active_run_id(), name="redacted", rule_key="project.redacted",
        rationale="token=never-store-this", actor="person", source="cli",
        created_at=NOW, expires_at=LATER,
    )
    assert "never-store-this" not in waiver.rationale
    revoked = service.revoke_human(
        waiver.name, actor="person", source="cli",
        reason="password=also-never-store", now=NOW,
    )
    assert "also-never-store" not in str(revoked.to_dict())
    assert "never-store" not in str(commands.repository.list_waiver_events(waiver.id))

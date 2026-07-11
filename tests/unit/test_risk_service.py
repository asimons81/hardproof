from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from crucible_agent.commands.shared import CommandContext, CommandService
from crucible_agent.domain.enums import RiskLevel
from crucible_agent.services.risks import RiskService, classify_risk


NOW = "2026-07-11T22:00:00Z"


@pytest.mark.parametrize(
    ("text", "files", "command", "expected", "reason"),
    [
        ("Add OAuth authorization", (), None, RiskLevel.CRITICAL, "signal:authentication"),
        ("Rotate API secrets", (), None, RiskLevel.CRITICAL, "signal:secrets"),
        ("Change invoice billing", (), None, RiskLevel.CRITICAL, "signal:billing"),
        ("Fix race in worker", (), None, RiskLevel.CRITICAL, "signal:concurrency"),
        ("Update schema", ("migrations/003.sql",), None, RiskLevel.CRITICAL, "path:migration"),
        ("Ship release", (), "kubectl apply -f app.yaml", RiskLevel.CRITICAL, "terminal:deployment"),
        ("Change public API", ("src/api.py",), None, RiskLevel.HIGH, "signal:public-api"),
        ("Refactor helpers", ("src/a.py", "src/b.py"), None, RiskLevel.MEDIUM, "scope:multiple-files"),
        ("Fix typo", ("docs/readme.md",), None, RiskLevel.LOW, "scope:documentation-only"),
    ],
)
def test_risk_classification_is_deterministic_and_explainable(
    text: str,
    files: tuple[str, ...],
    command: str | None,
    expected: RiskLevel,
    reason: str,
) -> None:
    first = classify_risk(text=text, files=files, command=command)
    second = classify_risk(text=text, files=files, command=command)
    assert first == second
    assert first.level is expected
    assert reason in first.reasons


def service_at(tmp_path: Path, *, actor: str = "person", source: str = "cli") -> tuple[CommandService, RiskService]:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    commands = CommandService(CommandContext(tmp_path, actor=actor, source=source))
    commands.execute(["start", "standard", "risk test"])
    return commands, RiskService(commands.repository)


def test_suggestion_and_human_override_are_durable_and_attributed(tmp_path: Path) -> None:
    commands, service = service_at(tmp_path)
    suggestion = service.suggest(
        commands.active_run_id(), text="Update migration", files=("migrations/003.sql",), now=NOW
    )
    assert suggestion.suggested_risk is RiskLevel.CRITICAL
    decided = service.decide_human(
        suggestion.id, accepted_risk=RiskLevel.HIGH, actor="person", source="cli",
        rationale="migration runs only on disposable fixture", now=NOW,
    )
    assert decided.accepted_risk is RiskLevel.HIGH
    assert decided.accepted_by == "person" and decided.accepted_source == "cli"
    reopened = commands.repository.get_risk_suggestion(suggestion.id)
    assert reopened == decided


def test_override_requires_human_authority_and_rationale(tmp_path: Path) -> None:
    commands, service = service_at(tmp_path, actor="model", source="tool")
    suggestion = service.suggest(commands.active_run_id(), text="Fix typo", now=NOW)
    with pytest.raises(PermissionError, match="human"):
        service.decide_human(
            suggestion.id, accepted_risk=RiskLevel.MEDIUM, actor="model", source="tool",
            rationale="model choice", now=NOW,
        )
    commands2, service2 = service_at(tmp_path / "human")
    suggestion2 = service2.suggest(commands2.active_run_id(), text="Fix typo", now=NOW)
    with pytest.raises(ValueError, match="rationale"):
        service2.decide_human(
            suggestion2.id, accepted_risk=RiskLevel.HIGH, actor="person", source="cli",
            rationale=None, now=NOW,
        )


def test_risk_suggestion_command_never_changes_run_profile(tmp_path: Path) -> None:
    commands, _ = service_at(tmp_path)
    before = commands.repository.get_run(commands.active_run_id()).profile
    result = commands.execute([
        "policy", "suggest-risk", "--text", "Deploy production migration",
        "--files", "migrations/003.sql", "--format", "json",
    ])
    assert result.ok and '"suggested_risk":"critical"' in result.text
    assert commands.repository.get_run(commands.active_run_id()).profile is before
    assert "Pending risk suggestions: 1" in commands.execute(["status"]).text

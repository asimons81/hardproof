from __future__ import annotations

from importlib import resources
from pathlib import Path
import sqlite3

import pytest

from hardproof.domain.enums import EvidenceStatus, RiskLevel, RunProfile, RunStage
from hardproof.domain.models import (
    Evidence,
    PolicyDecisionRecord,
    RiskSuggestion,
    Run,
    Waiver,
)
from hardproof.policy.trace import RuleTrace
from hardproof.storage.database import Database
from hardproof.storage.migrations import apply_migration_sql, migrate
from hardproof.storage.repository import RunRepository


NOW = "2026-07-11T18:00:00Z"
LATER = "2026-07-12T18:00:00Z"


def repository_at(path: Path) -> RunRepository:
    database = Database(path)
    migrate(database)
    return RunRepository(database)


def test_v1_database_upgrades_without_losing_run_or_evidence(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    sql = resources.files("hardproof.migrations").joinpath("001_initial.sql").read_text()
    with database.connect() as connection:
        apply_migration_sql(connection, 1, sql)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "preserve", RunProfile.STANDARD, now=NOW)
    repository.create_run(run)
    evidence = Evidence(
        "evidence-1", run.id, "tests", "python -m pytest", 0, EvidenceStatus.PASSED,
        "a" * 40, "b" * 64, "c" * 64, "evidence/test.log", "d" * 64, NOW, NOW,
    )
    repository.add_evidence(evidence)

    assert migrate(database) == (2,)
    assert repository.get_run(run.id) == run
    assert repository.list_evidence(run.id) == (evidence,)
    assert migrate(database) == ()


def test_gatehouse_ledgers_round_trip_and_preserve_append_order(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "policy", RunProfile.STANDARD, now=NOW)
    repository.create_run(run)
    waiver = Waiver(
        "waiver-1", run.id, "generated-file", "project.generated.write", "write_file",
        None, "generated/**", RunProfile.STANDARD, RunStage.DESIGN,
        "generator output reviewed", "person", "cli", NOW, LATER,
    )
    repository.add_waiver(waiver)
    assert repository.list_waivers(run.id) == (waiver,)
    lifecycle = repository.list_waiver_events(waiver.id)
    assert len(lifecycle) == 1
    assert lifecycle[0].event_type == "created" and lifecycle[0].sequence == 1

    trace = (RuleTrace("project.generated.write", "waived", "named waiver matched"),)
    decision = PolicyDecisionRecord(
        "policy-1", run.id, "write_file", "allow", "project.generated.write",
        "named waiver matched", trace, "a" * 64, "b" * 64, waiver.id, RiskLevel.LOW, NOW,
    )
    repository.add_policy_decision(decision)
    stored_decision = repository.list_policy_decisions(run.id)[0]
    assert stored_decision.sequence == 1
    assert stored_decision == PolicyDecisionRecord.from_dict({**decision.to_dict(), "sequence": 1})

    risk = RiskSuggestion(
        "risk-1", run.id, None, RiskLevel.HIGH, ("migration file",), None, None, NOW
    )
    repository.add_risk_suggestion(risk)
    assert repository.list_risk_suggestions(run.id) == (risk,)


def test_database_rejects_immutable_waiver_without_model_validation(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    migrate(database)
    with database.connect() as connection, pytest.raises(sqlite3.IntegrityError), connection:
        connection.execute(
            """INSERT INTO waivers(
                id, name, rule_key, rationale, actor, source, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "waiver-direct", "unsafe", "terminal.immutable.force_push", "unsafe",
                "person", "cli", NOW, LATER,
            ),
        )

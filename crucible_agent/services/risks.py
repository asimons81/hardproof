"""Deterministic advisory risk classification and human outcomes."""

from __future__ import annotations

import re
from dataclasses import dataclass

from crucible_agent.domain.enums import RiskLevel
from crucible_agent.domain.models import RiskSuggestion, new_id
from crucible_agent.policy.terminal import TerminalCategory, classify_terminal
from crucible_agent.services.authority import require_human
from crucible_agent.services.evidence import redact_output
from crucible_agent.storage.repository import RunRepository


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    level: RiskLevel
    reasons: tuple[str, ...]


_CRITICAL_SIGNALS = (
    (re.compile(r"\b(auth(?:entication|orization)?|oauth|sso)\b", re.I), "signal:authentication"),
    (re.compile(r"\b(secrets?|credentials?|api[-_ ]?keys?|passwords?|tokens?)\b", re.I), "signal:secrets"),
    (re.compile(r"\b(billing|invoice|payment|checkout|subscription)\b", re.I), "signal:billing"),
    (re.compile(r"\b(concurren|race(?: condition)?|deadlock|thread safety)", re.I), "signal:concurrency"),
    (re.compile(r"\b(deploy|production|infrastructure)\b", re.I), "signal:deployment"),
    (re.compile(r"\b(migrat|schema upgrade|data backfill)", re.I), "signal:migration"),
)
_HIGH_SIGNALS = (
    (re.compile(r"\b(public api|breaking change|permission|network|database)\b", re.I), "signal:public-api"),
    (re.compile(r"\b(dependency|configuration|config format)\b", re.I), "signal:configuration"),
)


def classify_risk(
    *, text: str, files: tuple[str, ...] = (), command: str | None = None
) -> RiskAssessment:
    reasons: list[str] = []
    level = RiskLevel.LOW
    for pattern, reason in _CRITICAL_SIGNALS:
        if pattern.search(text):
            reasons.append(reason)
            level = RiskLevel.CRITICAL
    normalized_files = tuple(path.replace("\\", "/").lower() for path in files)
    if any(
        path.startswith(("migrations/", "infra/", "terraform/", ".github/workflows/"))
        or "/migrations/" in path
        for path in normalized_files
    ):
        reasons.append("path:migration" if any("migrat" in path for path in normalized_files) else "path:infrastructure")
        level = RiskLevel.CRITICAL
    if command:
        category = classify_terminal(command).primary.category
        terminal_reason = {
            TerminalCategory.IMMUTABLE: "terminal:immutable",
            TerminalCategory.DESTRUCTIVE: "terminal:destructive",
            TerminalCategory.DEPLOYMENT: "terminal:deployment",
            TerminalCategory.DATABASE: "terminal:database",
            TerminalCategory.CREDENTIAL: "terminal:credential",
        }.get(category)
        if terminal_reason:
            reasons.append(terminal_reason)
            level = RiskLevel.CRITICAL
    if level is not RiskLevel.CRITICAL:
        for pattern, reason in _HIGH_SIGNALS:
            if pattern.search(text):
                reasons.append(reason)
                level = RiskLevel.HIGH
    if level in {RiskLevel.LOW, RiskLevel.MEDIUM} and (
        len(normalized_files) > 1 or re.search(r"\b(refactor|multiple|cross-cutting)\b", text, re.I)
    ):
        reasons.append("scope:multiple-files")
        level = RiskLevel.MEDIUM
    documentation_only = bool(normalized_files) and all(
        path.startswith("docs/") or path.endswith((".md", ".rst", ".txt"))
        for path in normalized_files
    )
    if documentation_only and level is RiskLevel.LOW:
        reasons.append("scope:documentation-only")
    if not reasons:
        reasons.append("scope:localized")
    return RiskAssessment(level, tuple(sorted(set(reasons))))


class RiskService:
    def __init__(self, repository: RunRepository) -> None:
        self.repository = repository

    def suggest(
        self,
        run_id: str,
        *,
        text: str,
        files: tuple[str, ...] = (),
        command: str | None = None,
        task_id: str | None = None,
        now: str,
    ) -> RiskSuggestion:
        assessment = classify_risk(text=text, files=files, command=command)
        suggestion = RiskSuggestion(
            new_id("risk"), run_id, task_id, assessment.level, assessment.reasons,
            None, None, now,
        )
        self.repository.add_risk_suggestion(suggestion)
        return suggestion

    def decide_human(
        self,
        suggestion_id: str,
        *,
        accepted_risk: RiskLevel,
        actor: str,
        source: str,
        rationale: str | None,
        now: str,
    ) -> RiskSuggestion:
        require_human(actor, source, "risk suggestion decision")
        current = self.repository.get_risk_suggestion(suggestion_id)
        if current.accepted_risk is not None:
            raise ValueError("risk suggestion already decided")
        if accepted_risk is not current.suggested_risk and not (rationale or "").strip():
            raise ValueError("risk override requires rationale")
        return self.repository.decide_risk_suggestion(
            suggestion_id, accepted_risk, redact_output(rationale or ""), actor, source, now
        )

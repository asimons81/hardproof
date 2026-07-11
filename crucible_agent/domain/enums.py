"""Enumerated values persisted by the Crucible protocol."""

from __future__ import annotations

from enum import StrEnum


class RunProfile(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    CRITICAL = "critical"


class RunStage(StrEnum):
    INTAKE = "INTAKE"
    DISCOVERY = "DISCOVERY"
    DESIGN = "DESIGN"
    PLAN = "PLAN"
    IMPLEMENT = "IMPLEMENT"
    REVIEW = "REVIEW"
    VERIFY = "VERIFY"
    DELIVER = "DELIVER"
    LEARN = "LEARN"
    PAUSED = "PAUSED"
    ABORTED = "ABORTED"
    COMPLETE = "COMPLETE"


class RunStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ABORTED = "aborted"
    COMPLETE = "complete"


class ArtifactKind(StrEnum):
    DISCOVERY = "discovery"
    DESIGN = "design"
    PLAN = "plan"
    REVIEW = "review"
    COMPLETION = "completion"
    LEARNING = "learning"
    RISK = "risk"
    OTHER = "other"


class ApprovalGate(StrEnum):
    DESIGN = "design"
    PLAN = "plan"
    COMPLETION = "completion"
    TOOL_ACTION = "tool_action"
    WAIVER = "waiver"


class TaskStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    INDETERMINATE = "indeterminate"
    STALE = "stale"

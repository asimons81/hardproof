"""Immutable domain records with deterministic JSON-friendly serialization."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, ClassVar, Self
from uuid import uuid4

from crucible_agent.domain.enums import (
    ApprovalGate,
    ArtifactKind,
    EvidenceStatus,
    RiskLevel,
    RunProfile,
    RunStage,
    RunStatus,
    TaskStatus,
)
from crucible_agent.policy.trace import RuleTrace


def new_id(prefix: str) -> str:
    """Generate an opaque, sortable-in-records identifier with a type prefix."""
    clean = prefix.strip().lower().replace("_", "-")
    if not clean or not clean.replace("-", "").isalnum():
        raise ValueError("ID prefix must contain letters, numbers, or hyphens")
    return f"{clean}-{uuid4()}"


def normalize_timestamp(value: str | datetime) -> str:
    """Normalize an aware timestamp to second-precision UTC RFC 3339."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_now() -> str:
    return normalize_timestamp(datetime.now(timezone.utc))


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty")


def _enum(enum_type: type[Enum], value: Any) -> Any:
    return value if isinstance(value, enum_type) else enum_type(value)


class Serializable:
    """Small serialization contract shared by persisted dataclasses."""

    _tuple_fields: ClassVar[tuple[str, ...]] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)  # type: ignore[call-overload]
        return {
            key: value.value if isinstance(value, Enum) else list(value) if isinstance(value, tuple) else value
            for key, value in payload.items()
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Self:
        values = dict(payload)
        for field in cls._tuple_fields:
            if field in values:
                values[field] = tuple(values[field])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class Run(Serializable):
    id: str
    project_root: str
    request: str
    profile: RunProfile
    stage: RunStage
    status: RunStatus
    created_at: str
    updated_at: str
    completed_at: str | None = None
    aborted_reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("id", "project_root", "request"):
            _require_text(name, getattr(self, name))
        object.__setattr__(self, "profile", _enum(RunProfile, self.profile))
        object.__setattr__(self, "stage", _enum(RunStage, self.stage))
        object.__setattr__(self, "status", _enum(RunStatus, self.status))
        object.__setattr__(self, "created_at", normalize_timestamp(self.created_at))
        object.__setattr__(self, "updated_at", normalize_timestamp(self.updated_at))
        if self.completed_at is not None:
            object.__setattr__(self, "completed_at", normalize_timestamp(self.completed_at))

    @classmethod
    def create(
        cls,
        project_root: str,
        request: str,
        profile: RunProfile,
        *,
        now: str | datetime | None = None,
    ) -> Run:
        timestamp = normalize_timestamp(now or datetime.now(timezone.utc))
        return cls(
            id=new_id("run"), project_root=project_root, request=request,
            profile=profile, stage=RunStage.INTAKE, status=RunStatus.ACTIVE,
            created_at=timestamp, updated_at=timestamp,
        )


@dataclass(frozen=True, slots=True)
class SessionBinding(Serializable):
    session_id: str
    run_id: str
    platform: str | None
    updated_at: str

    def __post_init__(self) -> None:
        _require_text("session_id", self.session_id)
        _require_text("run_id", self.run_id)
        object.__setattr__(self, "updated_at", normalize_timestamp(self.updated_at))


@dataclass(frozen=True, slots=True)
class Event(Serializable):
    run_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str
    sequence: int | None = None

    def __post_init__(self) -> None:
        _require_text("run_id", self.run_id)
        _require_text("event_type", self.event_type)
        if self.sequence is not None and self.sequence < 1:
            raise ValueError("sequence must be positive")
        object.__setattr__(self, "created_at", normalize_timestamp(self.created_at))


@dataclass(frozen=True, slots=True)
class Artifact(Serializable):
    id: str
    run_id: str
    kind: ArtifactKind
    path: str
    sha256: str
    created_at: str

    def __post_init__(self) -> None:
        for name in ("id", "run_id", "path"):
            _require_text(name, getattr(self, name))
        object.__setattr__(self, "kind", _enum(ArtifactKind, self.kind))
        _validate_hash("sha256", self.sha256, (64,))
        object.__setattr__(self, "created_at", normalize_timestamp(self.created_at))


@dataclass(frozen=True, slots=True)
class Approval(Serializable):
    id: str
    run_id: str
    gate: ApprovalGate
    actor: str
    source: str
    reason: str | None
    created_at: str

    def __post_init__(self) -> None:
        for name in ("id", "run_id", "actor", "source"):
            _require_text(name, getattr(self, name))
        object.__setattr__(self, "gate", _enum(ApprovalGate, self.gate))
        object.__setattr__(self, "created_at", normalize_timestamp(self.created_at))


@dataclass(frozen=True, slots=True)
class Decision(Serializable):
    id: str
    run_id: str
    key: str
    question: str
    choice: str
    rationale: str
    status: str
    created_at: str

    def __post_init__(self) -> None:
        for name in ("id", "run_id", "key", "question", "choice", "rationale", "status"):
            _require_text(name, getattr(self, name))
        object.__setattr__(self, "created_at", normalize_timestamp(self.created_at))


@dataclass(frozen=True, slots=True)
class Task(Serializable):
    id: str
    run_id: str
    task_key: str
    title: str
    description: str
    status: TaskStatus
    risk: RiskLevel
    dependencies: tuple[str, ...]
    acceptance: tuple[str, ...]
    files: tuple[str, ...]
    created_at: str
    updated_at: str
    acceptance_notes: str | None = None

    _tuple_fields: ClassVar[tuple[str, ...]] = ("dependencies", "acceptance", "files")

    def __post_init__(self) -> None:
        for name in ("id", "run_id", "task_key", "title", "description"):
            _require_text(name, getattr(self, name))
        object.__setattr__(self, "status", _enum(TaskStatus, self.status))
        object.__setattr__(self, "risk", _enum(RiskLevel, self.risk))
        for name in self._tuple_fields:
            object.__setattr__(self, name, tuple(getattr(self, name)))
        object.__setattr__(self, "created_at", normalize_timestamp(self.created_at))
        object.__setattr__(self, "updated_at", normalize_timestamp(self.updated_at))
        if self.status is TaskStatus.COMPLETED and not (self.acceptance_notes or "").strip():
            raise ValueError("completed task requires acceptance_notes")


@dataclass(frozen=True, slots=True)
class VerificationCheck(Serializable):
    id: str
    run_id: str
    name: str
    command: str
    required: bool
    timeout_seconds: int

    def __post_init__(self) -> None:
        for name in ("id", "run_id", "name", "command"):
            _require_text(name, getattr(self, name))
        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")


def _validate_hash(name: str, value: str, lengths: tuple[int, ...]) -> None:
    if len(value) not in lengths or any(char not in "0123456789abcdef" for char in value.lower()):
        raise ValueError(f"{name} must be a lowercase hexadecimal digest")


@dataclass(frozen=True, slots=True)
class Evidence(Serializable):
    id: str
    run_id: str
    check_name: str
    command: str
    exit_code: int | None
    status: EvidenceStatus
    head_sha: str
    diff_sha256: str
    untracked_sha256: str
    output_path: str
    output_sha256: str
    started_at: str
    completed_at: str

    def __post_init__(self) -> None:
        for name in ("id", "run_id", "check_name", "command", "output_path"):
            _require_text(name, getattr(self, name))
        object.__setattr__(self, "status", _enum(EvidenceStatus, self.status))
        _validate_hash("head_sha", self.head_sha, (40, 64))
        for name in ("diff_sha256", "untracked_sha256", "output_sha256"):
            _validate_hash(name, getattr(self, name), (64,))
        object.__setattr__(self, "started_at", normalize_timestamp(self.started_at))
        object.__setattr__(self, "completed_at", normalize_timestamp(self.completed_at))
        if self.status is EvidenceStatus.PASSED and self.exit_code != 0:
            raise ValueError("passed evidence requires explicit zero exit_code")


@dataclass(frozen=True, slots=True)
class TransitionResult(Serializable):
    allowed: bool
    target_stage: RunStage
    blockers: tuple[str, ...]

    _tuple_fields: ClassVar[tuple[str, ...]] = ("blockers",)

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_stage", _enum(RunStage, self.target_stage))
        object.__setattr__(self, "blockers", tuple(self.blockers))
        if self.allowed and self.blockers:
            raise ValueError("allowed transition cannot contain blockers")
        if not self.allowed and not self.blockers:
            raise ValueError("denied transition requires at least one blocker")

    @classmethod
    def allow(cls, target_stage: RunStage) -> TransitionResult:
        return cls(True, target_stage, ())

    @classmethod
    def deny(cls, target_stage: RunStage, *blockers: str) -> TransitionResult:
        return cls(False, target_stage, tuple(blockers))


@dataclass(frozen=True, slots=True)
class PolicyDecision(Serializable):
    action: str
    rule_key: str
    reason: str
    requires_human_approval: bool = False
    trace: tuple[RuleTrace, ...] = ()
    waiver_id: str | None = None

    _tuple_fields: ClassVar[tuple[str, ...]] = ("trace",)

    def __post_init__(self) -> None:
        if self.action not in {"allow", "block", "approval"}:
            raise ValueError("action must be allow, block, or approval")
        _require_text("rule_key", self.rule_key)
        _require_text("reason", self.reason)
        object.__setattr__(self, "trace", tuple(self.trace))
        if self.action == "approval" and not self.requires_human_approval:
            raise ValueError("approval action must require human approval")
        if self.trace and self.trace[-1].rule_key != self.rule_key:
            raise ValueError("final trace rule must match decision rule_key")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PolicyDecision:
        values = dict(payload)
        values["trace"] = tuple(
            item if isinstance(item, RuleTrace) else RuleTrace(**item)
            for item in values.get("trace", ())
        )
        return cls(**values)


@dataclass(frozen=True, slots=True)
class PolicyDecisionRecord(Serializable):
    id: str
    run_id: str
    tool_name: str
    action: str
    rule_key: str
    reason: str
    trace: tuple[RuleTrace, ...]
    arguments_sha256: str
    config_sha256: str
    waiver_id: str | None
    suggested_risk: RiskLevel | None
    created_at: str

    _tuple_fields: ClassVar[tuple[str, ...]] = ("trace",)

    def __post_init__(self) -> None:
        for name in ("id", "run_id", "tool_name", "rule_key", "reason"):
            _require_text(name, getattr(self, name))
        if self.action not in {"allow", "block", "approval"}:
            raise ValueError("action must be allow, block, or approval")
        object.__setattr__(self, "trace", tuple(self.trace))
        if not self.trace or self.trace[-1].rule_key != self.rule_key:
            raise ValueError("final trace rule must match decision rule_key")
        _validate_hash("arguments_sha256", self.arguments_sha256, (64,))
        _validate_hash("config_sha256", self.config_sha256, (64,))
        if self.suggested_risk is not None:
            object.__setattr__(self, "suggested_risk", _enum(RiskLevel, self.suggested_risk))
        object.__setattr__(self, "created_at", normalize_timestamp(self.created_at))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PolicyDecisionRecord:
        values = dict(payload)
        values["trace"] = tuple(
            item if isinstance(item, RuleTrace) else RuleTrace(**item) for item in values["trace"]
        )
        return cls(**values)


@dataclass(frozen=True, slots=True)
class Waiver(Serializable):
    id: str
    run_id: str | None
    name: str
    rule_key: str
    tool_name: str | None
    command_sha256: str | None
    path_scope: str | None
    profile: RunProfile | None
    stage: RunStage | None
    rationale: str
    actor: str
    source: str
    created_at: str
    expires_at: str
    revoked_at: str | None = None
    revoked_by: str | None = None
    revocation_reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("id", "name", "rule_key", "rationale", "actor", "source"):
            _require_text(name, getattr(self, name))
        if self.rule_key.startswith("terminal.immutable."):
            raise ValueError("immutable rules cannot be waived")
        if self.command_sha256 is not None:
            _validate_hash("command_sha256", self.command_sha256, (64,))
        if self.profile is not None:
            object.__setattr__(self, "profile", _enum(RunProfile, self.profile))
        if self.stage is not None:
            object.__setattr__(self, "stage", _enum(RunStage, self.stage))
        created = normalize_timestamp(self.created_at)
        expires = normalize_timestamp(self.expires_at)
        if expires <= created:
            raise ValueError("waiver expiry must be after creation")
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "expires_at", expires)
        if self.revoked_at is not None:
            object.__setattr__(self, "revoked_at", normalize_timestamp(self.revoked_at))
            if not (self.revoked_by or "").strip() or not (self.revocation_reason or "").strip():
                raise ValueError("revoked waiver requires actor and reason")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Waiver:
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class WaiverEvent(Serializable):
    waiver_id: str
    event_type: str
    actor: str
    source: str
    rationale: str
    created_at: str
    sequence: int | None = None

    def __post_init__(self) -> None:
        for name in ("waiver_id", "actor", "source", "rationale"):
            _require_text(name, getattr(self, name))
        if self.event_type not in {"created", "revoked", "expired"}:
            raise ValueError("unknown waiver lifecycle event")
        if self.sequence is not None and self.sequence < 1:
            raise ValueError("waiver event sequence must be positive")
        object.__setattr__(self, "created_at", normalize_timestamp(self.created_at))


@dataclass(frozen=True, slots=True)
class RiskSuggestion(Serializable):
    id: str
    run_id: str
    task_id: str | None
    suggested_risk: RiskLevel
    reasons: tuple[str, ...]
    accepted_risk: RiskLevel | None
    override_rationale: str | None
    created_at: str

    _tuple_fields: ClassVar[tuple[str, ...]] = ("reasons",)

    def __post_init__(self) -> None:
        for name in ("id", "run_id"):
            _require_text(name, getattr(self, name))
        object.__setattr__(self, "suggested_risk", _enum(RiskLevel, self.suggested_risk))
        object.__setattr__(self, "reasons", tuple(self.reasons))
        if not self.reasons or any(not reason.strip() for reason in self.reasons):
            raise ValueError("risk suggestion requires non-empty reasons")
        if self.accepted_risk is not None:
            object.__setattr__(self, "accepted_risk", _enum(RiskLevel, self.accepted_risk))
            if self.accepted_risk is not self.suggested_risk and not (
                self.override_rationale or ""
            ).strip():
                raise ValueError("risk override requires rationale")
        object.__setattr__(self, "created_at", normalize_timestamp(self.created_at))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RiskSuggestion:
        values = dict(payload)
        values["reasons"] = tuple(values["reasons"])
        return cls(**values)

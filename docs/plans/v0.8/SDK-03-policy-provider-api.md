# SDK-03: Policy Provider API (v0.8.0)

Status: design-only. Not started.

## Goal
Public interface for external/custom policy providers: deterministic decisions, explainable traces, immutable safety floor, isolated failures.

## Decision Contract
```python
from enum import Enum
from dataclasses import dataclass
from typing import Protocol, Optional

class Decision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"

@dataclass(frozen=True, slots=True)
class DecisionContext:
    stage: str
    profile: str
    task_id: str
    args_sha256: str
    workspace_head: str

@dataclass(frozen=True, slots=True)
class DecisionResult:
    decision: Decision
    reason: str
    trace_id: str
    provider_id: str
```

## PolicyProvider Protocol
```python
class PolicyProvider(Protocol):
    def decide(self, ctx: DecisionContext) -> DecisionResult: ...
    def explain(self, trace_id: str) -> list[str]: ...
    @property
    def id(self) -> str: ...
```

## Safety Floor (Immutable, Non-Waivable)
- Terminal normalization rules (hardproof/policy/terminal.py)
- Evidence HEAD + diff recording (hardproof/services/evidence.py)
- Approval authenticity (human sources only)
- Migration forward-only (hardproof/storage/migrations.py)
- State namespace isolation (.hardproof/)
- Fail-closed on provider timeout/exception/malformed config

## Trace Schema (v1)
```json
{
  "trace_id": "uuid",
  "provider_id": "string",
  "ts": "iso8601",
  "stage": "string",
  "decision": "allow|deny|escalate",
  "reason": "string",
  "redacted_args_sha256": "sha256",
  "workspace_head": "sha"
}
```
Redaction: secrets → [REDACTED]; size ≤ 4 KiB per trace entry.

## Failure Modes
- Timeout (≤ 2s default): DENY + trace
- Exception: caught, logged, DENY + trace
- Malformed config: DENY at load time, no registration
- All failures isolated; core never crashes

## Alignment
- SDK-01 (freeze): Decision + Trace contracts frozen
- SDK-02 (capability "policy"): providers register under this key
- No private hardproof.policy.* or hermes internals exported

## Contract Tests Outline
- Deterministic: same ctx → same decision
- Safety floor: provider cannot return ALLOW on immutable deny
- Trace: redaction + size + version
- Failure: timeout/exception → DENY documented

## Open Risks (for contract + risk review)
- Provider registration surface (plugin entry point vs config)
- Trace storage lifetime vs evidence retention
- Multi-provider precedence rules (future)

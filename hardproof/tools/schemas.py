"""Exact JSON schemas for the six v0.1.0 Hardproof tools."""

from __future__ import annotations

from typing import Any


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


STRING = {"type": "string"}
STRING_ARRAY = {"type": "array", "items": STRING}

TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "hardproof_run": _schema(
        "hardproof_run",
        "Start, inspect, pause, resume, or abort a durable Hardproof run. Use status before making stage-sensitive changes.",
        {
            "action": {"type": "string", "enum": ["start", "status", "pause", "resume", "abort", "workcells_status", "workcells_run_next", "workcells_reconcile"]},
            "request": STRING,
            "profile": {"type": "string", "enum": ["quick", "standard", "critical"]},
            "run_id": STRING,
            "reason": STRING,
            "attempt_id": STRING,
        },
        ["action"],
    ),
    "hardproof_record": _schema(
        "hardproof_record",
        "Record a run artifact, decision, review, learning item, or risk. This tool cannot create human approvals or waivers.",
        {
            "kind": {"type": "string", "enum": ["artifact", "decision", "discovery", "design", "plan", "review", "learning", "risk"]},
            "title": STRING,
            "content": STRING,
            "path": STRING,
            "metadata": {"type": "object"},
        },
        ["kind", "content"],
    ),
    "hardproof_task": _schema(
        "hardproof_task",
        "Create, update, list, or inspect durable implementation tasks and their acceptance evidence.",
        {
            "action": {"type": "string", "enum": ["create", "update", "list", "get", "workcell_create_graph", "workcell_graph", "workcell_attempts", "workcell_process_result"]},
            "key": STRING,
            "title": STRING,
            "description": STRING,
            "status": {"type": "string", "enum": ["pending", "ready", "in_progress", "blocked", "completed", "skipped"]},
            "risk": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            "dependencies": STRING_ARRAY,
            "acceptance": STRING_ARRAY,
            "files": STRING_ARRAY,
            "acceptance_notes": STRING,
            "task_id": STRING,
            "attempt_id": STRING,
            "workcell_tasks": {"type": "array", "items": {"type": "object"}},
        },
        ["action"],
    ),
    "hardproof_transition": _schema(
        "hardproof_transition",
        "Request a stage transition after recording the required artifacts, tasks, review, and evidence. Gates are evaluated from durable state.",
        {
            "target_stage": {"type": "string", "enum": ["INTAKE", "DISCOVERY", "DESIGN", "PLAN", "IMPLEMENT", "REVIEW", "VERIFY", "DELIVER", "LEARN", "PAUSED", "ABORTED", "COMPLETE"]},
            "reason": STRING,
            "skip_reason": STRING,
        },
        ["target_stage", "reason"],
    ),
    "hardproof_verify": _schema(
        "hardproof_verify",
        "Run configured verification checks through Hermes and record workspace-bound evidence. Only explicit zero exit codes can pass.",
        {
            "checks": STRING_ARRAY,
            "all_required": {"type": "boolean"},
            "timeout_override": {"type": "integer", "minimum": 1},
        },
        [],
    ),
    "hardproof_report": _schema(
        "hardproof_report",
        "Inspect status or evidence and export deterministic run or completion reports without exposing secrets.",
        {
            "action": {"type": "string", "enum": ["status", "evidence", "export", "completion", "policy_explain", "risk_suggest"]},
            "path": STRING,
            "format": {"type": "string", "enum": ["markdown", "json", "both"]},
            "event_sequence": {"type": "integer", "minimum": 1},
            "tool_name": STRING,
            "arguments": {"type": "object"},
            "text": STRING,
            "files": STRING_ARRAY,
            "command": STRING,
        },
        ["action"],
    ),
}

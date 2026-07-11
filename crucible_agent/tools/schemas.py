"""Exact JSON schemas for the six v0.1.0 Crucible tools."""

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
    "crucible_run": _schema(
        "crucible_run",
        "Start, inspect, pause, resume, or abort a durable Crucible run. Use status before making stage-sensitive changes.",
        {
            "action": {"type": "string", "enum": ["start", "status", "pause", "resume", "abort"]},
            "request": STRING,
            "profile": {"type": "string", "enum": ["quick", "standard", "critical"]},
            "run_id": STRING,
            "reason": STRING,
        },
        ["action"],
    ),
    "crucible_record": _schema(
        "crucible_record",
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
    "crucible_task": _schema(
        "crucible_task",
        "Create, update, list, or inspect durable implementation tasks and their acceptance evidence.",
        {
            "action": {"type": "string", "enum": ["create", "update", "list", "get"]},
            "key": STRING,
            "title": STRING,
            "description": STRING,
            "status": {"type": "string", "enum": ["pending", "ready", "in_progress", "blocked", "completed", "skipped"]},
            "risk": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            "dependencies": STRING_ARRAY,
            "acceptance": STRING_ARRAY,
            "files": STRING_ARRAY,
            "acceptance_notes": STRING,
        },
        ["action"],
    ),
    "crucible_transition": _schema(
        "crucible_transition",
        "Request a stage transition after recording the required artifacts, tasks, review, and evidence. Gates are evaluated from durable state.",
        {
            "target_stage": {"type": "string", "enum": ["INTAKE", "DISCOVERY", "DESIGN", "PLAN", "IMPLEMENT", "REVIEW", "VERIFY", "DELIVER", "LEARN", "PAUSED", "ABORTED", "COMPLETE"]},
            "reason": STRING,
            "skip_reason": STRING,
        },
        ["target_stage", "reason"],
    ),
    "crucible_verify": _schema(
        "crucible_verify",
        "Run configured verification checks through Hermes and record workspace-bound evidence. Only explicit zero exit codes can pass.",
        {
            "checks": STRING_ARRAY,
            "all_required": {"type": "boolean"},
            "timeout_override": {"type": "integer", "minimum": 1},
        },
        [],
    ),
    "crucible_report": _schema(
        "crucible_report",
        "Inspect status or evidence and export deterministic run or completion reports without exposing secrets.",
        {
            "action": {"type": "string", "enum": ["status", "evidence", "export", "completion"]},
            "path": STRING,
            "format": {"type": "string", "enum": ["markdown", "json", "both"]},
        },
        ["action"],
    ),
}

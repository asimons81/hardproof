"""Bounded, monotonic stage-graph configuration and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hardproof.domain.enums import RunProfile, RunStage

ACTIVE_ORDER = (
    RunStage.INTAKE, RunStage.DISCOVERY, RunStage.DESIGN, RunStage.PLAN,
    RunStage.IMPLEMENT, RunStage.REVIEW, RunStage.VERIFY, RunStage.DELIVER,
    RunStage.LEARN, RunStage.COMPLETE,
)
POSITION = {stage: index for index, stage in enumerate(ACTIVE_ORDER)}
MAX_STAGE_NODES = len(RunStage)
MAX_STAGE_EDGES = 24
OPTIONAL_SKIPS = frozenset({RunStage.DISCOVERY, RunStage.LEARN})


class StageGraphError(ValueError):
    """A configured graph would weaken deterministic stage safety."""


@dataclass(frozen=True, slots=True)
class StageGraph:
    edges: tuple[tuple[RunStage, RunStage], ...]
    required: tuple[RunStage, ...]
    skipped: tuple[RunStage, ...]
    source: str = "canonical"

    def successors(self, stage: RunStage) -> tuple[RunStage, ...]:
        return tuple(target for source, target in self.edges if source is stage)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "limits": {"nodes": MAX_STAGE_NODES, "edges": MAX_STAGE_EDGES},
            "required_stages": [item.value for item in self.required],
            "skipped_stages": [item.value for item in self.skipped],
            "edges": [[source.value, target.value] for source, target in self.edges],
            "immutable_constraints": [
                "forward-only", "VERIFY and DELIVER required", "terminal stages immutable",
                "supported stage vocabulary only", "one deterministic active successor",
            ],
        }


def canonical_stage_graph() -> StageGraph:
    edges = tuple(zip(ACTIVE_ORDER[:-1], ACTIVE_ORDER[1:], strict=True))
    return StageGraph(edges, (RunStage.VERIFY, RunStage.DELIVER, RunStage.COMPLETE), ())


def compile_stage_graph(value: Any, *, profile: RunProfile | None = None) -> StageGraph:
    if value in ({}, None):
        return canonical_stage_graph()
    if not isinstance(value, dict):
        raise StageGraphError("policy.stage_graph must be a mapping")
    allowed = {"schema_version", "edges", "required_stages", "skipped_stages", "profiles"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise StageGraphError(f"policy.stage_graph has unknown keys: {', '.join(unknown)}")
    if value.get("schema_version", 1) != 1:
        raise StageGraphError("policy.stage_graph.schema_version must be 1")
    effective = dict(value)
    overlays = value.get("profiles", {})
    if not isinstance(overlays, dict):
        raise StageGraphError("policy.stage_graph.profiles must be a mapping")
    for key in overlays:
        if key not in {item.value for item in RunProfile}:
            raise StageGraphError(f"policy.stage_graph.profiles contains unknown profile: {key}")
    if profile is not None and profile.value in overlays:
        overlay = overlays[profile.value]
        if not isinstance(overlay, dict) or set(overlay) - {"edges", "required_stages", "skipped_stages"}:
            raise StageGraphError(f"policy.stage_graph.profiles.{profile.value} is malformed")
        effective.update(overlay)

    def stages(name: str) -> tuple[RunStage, ...]:
        raw = effective.get(name, [])
        if not isinstance(raw, list) or len(raw) > MAX_STAGE_NODES:
            raise StageGraphError(f"policy.stage_graph.{name} must be a bounded list")
        try:
            result = tuple(RunStage(item) for item in raw)
        except (TypeError, ValueError) as exc:
            raise StageGraphError(f"policy.stage_graph.{name} contains an unknown stage") from exc
        if len(set(result)) != len(result):
            raise StageGraphError(f"policy.stage_graph.{name} contains duplicates")
        return result

    skipped = stages("skipped_stages")
    required = stages("required_stages")
    if any(item not in OPTIONAL_SKIPS for item in skipped):
        raise StageGraphError("only DISCOVERY and LEARN may be skipped")
    if profile is RunProfile.CRITICAL and skipped:
        raise StageGraphError("critical profile cannot skip configured stages")
    immutable_required = {RunStage.VERIFY, RunStage.DELIVER, RunStage.COMPLETE}
    if set(skipped) & (immutable_required | set(required)):
        raise StageGraphError("a required or immutable stage cannot be skipped")
    active = tuple(stage for stage in ACTIVE_ORDER if stage not in skipped)
    default_edges = tuple(zip(active[:-1], active[1:], strict=True))
    raw_edges = effective.get("edges")
    if raw_edges is None:
        edges = default_edges
    else:
        if not isinstance(raw_edges, list) or len(raw_edges) > MAX_STAGE_EDGES:
            raise StageGraphError(f"policy.stage_graph.edges exceeds limit {MAX_STAGE_EDGES}")
        parsed: list[tuple[RunStage, RunStage]] = []
        for index, edge in enumerate(raw_edges):
            if not isinstance(edge, list) or len(edge) != 2:
                raise StageGraphError(f"policy.stage_graph.edges[{index}] must contain two stages")
            try:
                source, target = RunStage(edge[0]), RunStage(edge[1])
            except (TypeError, ValueError) as exc:
                raise StageGraphError(f"policy.stage_graph.edges[{index}] contains an unknown stage") from exc
            if source is target:
                raise StageGraphError(f"self-loop is forbidden: {source.value}")
            if source not in POSITION or target not in POSITION or POSITION[target] <= POSITION[source]:
                raise StageGraphError(f"backward or terminal edge is forbidden: {source.value} -> {target.value}")
            parsed.append((source, target))
        edges = tuple(parsed)
    if len(set(edges)) != len(edges):
        raise StageGraphError("policy.stage_graph.edges contains duplicate edges")
    outgoing: dict[RunStage, list[RunStage]] = {}
    for source, target in edges:
        outgoing.setdefault(source, []).append(target)
    ambiguous = next((source for source, targets in outgoing.items() if len(targets) > 1), None)
    if ambiguous:
        raise StageGraphError(f"stage {ambiguous.value} has multiple ambiguous canonical successors")
    cursor = RunStage.INTAKE
    visited = {cursor}
    while cursor is not RunStage.COMPLETE:
        targets = outgoing.get(cursor, [])
        if len(targets) != 1:
            raise StageGraphError(f"no deterministic path to COMPLETE from {cursor.value}")
        cursor = targets[0]
        if cursor in visited:
            raise StageGraphError("policy.stage_graph contains a cycle")
        visited.add(cursor)
    required_set = immutable_required | set(required)
    missing = sorted((item.value for item in required_set - visited))
    if missing:
        raise StageGraphError(f"unreachable required stages: {', '.join(missing)}")
    if RunStage.VERIFY not in visited:
        raise StageGraphError("every completion path must include VERIFY")
    return StageGraph(edges, tuple(sorted(required_set, key=POSITION.__getitem__)), skipped, "project")

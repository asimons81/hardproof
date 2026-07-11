from __future__ import annotations

import pytest

from hardproof.domain.enums import RunProfile, RunStage
from hardproof.policy.stage_graph import StageGraphError, canonical_stage_graph, compile_stage_graph


def test_canonical_graph_is_bounded_deterministic_and_verified() -> None:
    graph = canonical_stage_graph()
    assert len(graph.edges) == 9
    assert graph.successors(RunStage.REVIEW) == (RunStage.VERIFY,)
    assert graph.to_dict()["limits"] == {"nodes": 12, "edges": 24}


def test_optional_skip_compiles_one_forward_path() -> None:
    graph = compile_stage_graph({"skipped_stages": ["DISCOVERY", "LEARN"]}, profile=RunProfile.STANDARD)
    assert graph.successors(RunStage.INTAKE) == (RunStage.DESIGN,)
    assert graph.successors(RunStage.DELIVER) == (RunStage.COMPLETE,)


@pytest.mark.parametrize("value, message", [
    ({"edges": [["PLAN", "PLAN"]]}, "self-loop"),
    ({"edges": [["PLAN", "DESIGN"]]}, "backward"),
    ({"edges": [["INTAKE", "UNKNOWN"]]}, "unknown stage"),
    ({"edges": [["INTAKE", "DESIGN"], ["INTAKE", "PLAN"]]}, "ambiguous"),
    ({"skipped_stages": ["VERIFY"]}, "only DISCOVERY and LEARN"),
])
def test_unsafe_graphs_fail_closed(value: object, message: str) -> None:
    with pytest.raises(StageGraphError, match=message):
        compile_stage_graph(value)


def test_duplicate_edges_and_edge_limit_are_rejected() -> None:
    with pytest.raises(StageGraphError, match="duplicate"):
        compile_stage_graph({"edges": [["INTAKE", "DISCOVERY"], ["INTAKE", "DISCOVERY"]]})
    with pytest.raises(StageGraphError, match="exceeds limit"):
        compile_stage_graph({"edges": [["INTAKE", "DISCOVERY"]] * 25})


def test_critical_overlay_cannot_skip() -> None:
    with pytest.raises(StageGraphError, match="critical"):
        compile_stage_graph({"profiles": {"critical": {"skipped_stages": ["LEARN"]}}}, profile=RunProfile.CRITICAL)

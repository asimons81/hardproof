from crucible_agent.domain.enums import RunStage
from crucible_agent.domain.transitions import FORWARD_STAGE, possible_targets


def test_forward_stage_sequence_matches_protocol() -> None:
    stage = RunStage.INTAKE
    observed = [stage]
    while stage in FORWARD_STAGE:
        stage = FORWARD_STAGE[stage]
        observed.append(stage)
    assert observed == [
        RunStage.INTAKE,
        RunStage.DISCOVERY,
        RunStage.DESIGN,
        RunStage.PLAN,
        RunStage.IMPLEMENT,
        RunStage.REVIEW,
        RunStage.VERIFY,
        RunStage.DELIVER,
        RunStage.LEARN,
        RunStage.COMPLETE,
    ]


def test_active_stage_can_pause_abort_or_advance() -> None:
    assert possible_targets(RunStage.DESIGN) == frozenset(
        {RunStage.PLAN, RunStage.PAUSED, RunStage.ABORTED}
    )


def test_terminal_stage_is_immutable() -> None:
    assert possible_targets(RunStage.COMPLETE) == frozenset()
    assert possible_targets(RunStage.ABORTED) == frozenset()

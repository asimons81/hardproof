from crucible_agent.domain.enums import ApprovalGate, RunProfile
from crucible_agent.policy.profiles import policy_for


def test_standard_is_single_check_default_with_human_design_and_plan_gates() -> None:
    policy = policy_for(RunProfile.STANDARD)
    assert policy.minimum_verification_checks == 1
    assert policy.required_approvals == frozenset({ApprovalGate.DESIGN, ApprovalGate.PLAN})
    assert policy.requires_review


def test_critical_is_fail_closed_and_requires_completion_approval() -> None:
    policy = policy_for(RunProfile.CRITICAL)
    assert policy.minimum_verification_checks == 2
    assert ApprovalGate.COMPLETION in policy.required_approvals
    assert policy.fail_closed_on_state_error


def test_quick_never_drops_verification() -> None:
    policy = policy_for(RunProfile.QUICK)
    assert policy.minimum_verification_checks == 1
    assert not policy.required_approvals

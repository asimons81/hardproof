"""Unit tests for the Challenge Chamber reviewer dispatch and fix/re-review loop."""
from __future__ import annotations

from hardproof.services.fix_re_review import FixReReviewLoop
from hardproof.services.review_dispatch import ReviewerDispatch
from hardproof.services.hermes_children import FakeHermesChildAdapter


def test_reviewer_dispatch_launches_all_specs(monkeypatch) -> None:
    from hardproof.services import review_dispatch

    fake = FakeHermesChildAdapter()
    monkeypatch.setattr(review_dispatch, "HermesChildAdapter", lambda context: fake)

    dispatcher = ReviewerDispatch(context=object())
    launches = dispatcher.launch_reviewers("Review this change carefully")

    assert len(launches) == 3
    assert len(fake.launches) == 3
    # Security reviewer first, then architecture, then tests
    assert fake.launches[0][0] == "Security audit: vulns, secrets, authz, deps"
    assert fake.launches[1][0] == "Arch review: modularity, coupling, boundaries"
    assert fake.launches[2][0] == "Test coverage, edge cases, determinism"
    # Model tiers from the spec are propagated to the adapter
    assert fake.launches[0][2] == "stack.coding.large"
    assert fake.launches[2][2] == "stack.coding.medium"
    # Each launch is a ChildLaunch with a real handle
    assert all(launch.handle.startswith("fake-handle-") for launch in launches)


def test_reviewer_specs_have_required_fields() -> None:
    specs = ReviewerDispatch.REVIEWER_SPECS
    assert {spec.name for spec in specs} == {"security", "architecture", "tests"}
    assert all(spec.brief and spec.model_tier for spec in specs)


def test_fix_re_review_defaults() -> None:
    loop = FixReReviewLoop(run_id="run-1", blocking_finding="test flaky", reviewer="security")
    assert loop.severity == "high"
    assert loop.target_stage == "IMPLEMENT"


def test_fix_re_review_trigger_payload() -> None:
    loop = FixReReviewLoop(
        run_id="run-2",
        blocking_finding="missing authz check",
        reviewer="architecture",
        severity="medium",
    )
    payload = loop.trigger_fix()
    assert payload == {
        "action": "return_to_implement",
        "reason": "missing authz check",
        "reviewer": "architecture",
        "severity": "medium",
    }


def test_fix_re_review_requires_re_review() -> None:
    loop = FixReReviewLoop(run_id="run-3", blocking_finding="x", reviewer="tests", severity="low")
    assert loop.require_re_review() is True

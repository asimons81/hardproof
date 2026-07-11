from __future__ import annotations

from hypothesis import given, strategies as st

from hardproof.domain.enums import RunProfile
from hardproof.domain.models import Run


@given(
    request=st.text(min_size=1).filter(lambda value: bool(value.strip())),
    root=st.text(min_size=1).filter(lambda value: bool(value.strip())),
    profile=st.sampled_from(list(RunProfile)),
)
def test_run_serialization_property(request: str, root: str, profile: RunProfile) -> None:
    run = Run.create(root, request, profile)
    assert Run.from_dict(run.to_dict()) == run

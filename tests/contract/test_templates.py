from importlib import resources

import pytest


@pytest.mark.parametrize("name", ["discovery", "design", "plan", "review", "completion"])
def test_artifact_templates_have_required_protocol_sections(name: str) -> None:
    text = resources.files("crucible_agent.templates").joinpath(f"{name}.md").read_text(encoding="utf-8")
    for heading in (
        "## Purpose",
        "## Required sections",
        "## No-placeholder check",
        "## Approval status",
        "## Unresolved questions",
        "## Evidence links",
    ):
        assert heading in text

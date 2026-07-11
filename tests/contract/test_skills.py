from __future__ import annotations

import re
from pathlib import Path

import yaml

from hardproof.domain.enums import RunStage
from hardproof.plugin import SKILL_NAMES, register_skills
from hardproof.tools.schemas import TOOL_SCHEMAS


ROOT = Path(__file__).resolve().parents[2] / "hardproof" / "skills"
REQUIRED_HEADINGS = (
    "## Purpose", "## When to use", "## Inputs", "## Procedure",
    "## Required records", "## Exit criteria", "## Failure modes", "## Verification",
)


def skill_files() -> list[Path]:
    return sorted(ROOT.glob("*/SKILL.md"))


def parse(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    assert match, f"frontmatter missing: {path}"
    return yaml.safe_load(match.group(1)), match.group(2)


def test_exact_nine_unique_original_skills() -> None:
    assert len(skill_files()) == 9
    names = [parse(path)[0]["name"] for path in skill_files()]
    assert len(names) == len(set(names))
    assert set(names) == set(SKILL_NAMES)


def test_frontmatter_and_required_structure() -> None:
    for path in skill_files():
        metadata, body = parse(path)
        assert set(metadata) == {"name", "description"}
        assert 20 <= len(metadata["description"]) <= 240
        for heading in REQUIRED_HEADINGS:
            assert heading in body, f"{heading} missing from {path}"
        assert "TODO" not in body


def test_skills_reference_only_real_tools_and_stages() -> None:
    valid_tools = set(TOOL_SCHEMAS)
    valid_stages = {stage.value for stage in RunStage}
    for path in skill_files():
        _, body = parse(path)
        referenced_tools = set(re.findall(r"`(hardproof_[a-z_]+)`", body))
        assert referenced_tools <= valid_tools, (path, referenced_tools - valid_tools)
        referenced_stages = set(re.findall(r"\b[A-Z]{4,10}\b", body)) & {
            "INTAKE", "DISCOVERY", "DESIGN", "PLAN", "IMPLEMENT", "REVIEW",
            "VERIFY", "DELIVER", "LEARN", "COMPLETE", "PAUSED", "ABORTED",
        }
        assert referenced_stages <= valid_stages
        assert "`hardproof_transition`" in body


def test_no_upstream_namespace_or_banned_copied_phrases() -> None:
    banned = ("superpowers:", "brainstorming", "writing-plans", "executing-plans")
    for path in skill_files():
        text = path.read_text(encoding="utf-8").lower()
        assert all(phrase not in text for phrase in banned)


class SkillContext:
    def __init__(self) -> None:
        self.registered: list[tuple[str, Path, str]] = []

    def register_skill(self, name: str, path: Path, description: str = "") -> None:
        self.registered.append((name, path, description))


def test_registration_passes_bare_names_for_hermes_namespace() -> None:
    context = SkillContext()
    register_skills(context)
    assert {name for name, _, _ in context.registered} == set(SKILL_NAMES)
    assert all(":" not in name for name, _, _ in context.registered)
    assert all(path.name == "SKILL.md" and path.is_file() for _, path, _ in context.registered)

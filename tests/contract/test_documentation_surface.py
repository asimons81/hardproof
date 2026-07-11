"""Contract tests for documentation surface integrity."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestAgentsFiles:
    """Root and nested AGENTS.md files must exist and stay within size limits."""

    AGENTS_PATHS = [
        "AGENTS.md",
        "hardproof/AGENTS.md",
        "tests/AGENTS.md",
        "docs/AGENTS.md",
    ]
    MAX_CHARS = 16_000

    @pytest.mark.parametrize("rel_path", AGENTS_PATHS)
    def test_agents_file_exists(self, rel_path: str) -> None:
        full = REPO_ROOT / rel_path
        assert full.exists(), f"Missing AGENTS.md: {rel_path}"

    @pytest.mark.parametrize("rel_path", AGENTS_PATHS)
    def test_agents_file_size(self, rel_path: str) -> None:
        full = REPO_ROOT / rel_path
        if not full.exists():
            pytest.skip(f"{rel_path} not found")
        size = full.stat().st_size
        assert size <= self.MAX_CHARS, f"{rel_path} is {size} bytes (max {self.MAX_CHARS})"


class TestReadmeCurrentRelease:
    """README must correctly identify the current release."""

    def test_readme_refers_to_v020(self) -> None:
        readme = REPO_ROOT / "README.md"
        text = readme.read_text(encoding="utf-8")
        assert "v0.2.0 Gatehouse" in text, "README must reference v0.2.0 as current release"

    def test_v030_qualified(self) -> None:
        """v0.3.0 must be described as future work, not started."""
        readme = REPO_ROOT / "README.md"
        text = readme.read_text(encoding="utf-8")
        idx = text.find("v0.3.0")
        if idx >= 0:
            context = text[idx:idx + 120]
            assert "not started" in context or "has not begun" in context or "planned" in context, (
                f"v0.3.0 reference in README must say 'not started' or 'planned': {context}"
            )


class TestNoAbsolutePaths:
    """No committed docs should contain absolute local paths."""

    PATTERNS = ["C:\\Users\\", "/Users/", "/home/"]
    HISTORICAL_PREFIXES = [
        "docs/release/",
        "docs/rebrand/",
        "docs/plans/",
        "docs/codex/",
        "docs/maintenance/",
    ]
    ALLOWED_PATTERN_DESCRIPTIONS = [
        "docs/AGENTS.md",  # Describes anti-patterns in "Prohibited Content" section
    ]

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_no_absolute_paths_in_md(self, pattern: str) -> None:
        for md_file in REPO_ROOT.rglob("*.md"):
            if ".git" in md_file.parts:
                continue
            rel = str(md_file.relative_to(REPO_ROOT)).replace("\\", "/")
            # Skip historical docs
            if any(rel.startswith(h) for h in self.HISTORICAL_PREFIXES):
                continue
            # Skip files that intentionally describe these patterns
            if rel in self.ALLOWED_PATTERN_DESCRIPTIONS:
                continue
            text = md_file.read_text(encoding="utf-8", errors="replace")
            if pattern in text:
                pytest.fail(f"Absolute path '{pattern}' found in {rel}")


@pytest.mark.skip(reason="Check docs/README.md has no stale release-candidate status in current docs")
class TestNoStaleStatusPhrases:
    """Current-status docs should not use pre-release language for published releases."""

    # Historical release docs are exempt
    HISTORICAL = [
        "CHANGELOG.md",
        "ROADMAP.md",
        "docs/release/",
        "docs/rebrand/",
        "docs/plans/",
    ]
    STALE = [
        "release candidate",
        "unpublished release candidate",
        "publication pending",
        "v0.2.0 not published",
        "v0.2.0 development",
    ]

    def test_check_stale_phrases(self) -> None:
        for md_file in REPO_ROOT.rglob("*.md"):
            if ".git" in md_file.parts:
                continue
            rel = str(md_file.relative_to(REPO_ROOT))
            if any(rel.startswith(h) for h in self.HISTORICAL):
                continue
            text = md_file.read_text(encoding="utf-8")
            for phrase in self.STALE:
                if phrase.lower() in text.lower():
                    pytest.fail(f"Stale phrase '{phrase}' in {rel}")

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
    MAX_CHARS = 14_000
    ROOT_MIN_CHARS = 8_000

    @pytest.mark.parametrize("rel_path", AGENTS_PATHS)
    def test_agents_file_exists(self, rel_path: str) -> None:
        full = REPO_ROOT / rel_path
        assert full.exists(), f"Missing AGENTS.md: {rel_path}"

    @pytest.mark.parametrize("rel_path", AGENTS_PATHS)
    def test_agents_file_size(self, rel_path: str) -> None:
        full = REPO_ROOT / rel_path
        if not full.exists():
            pytest.skip(f"{rel_path} not found")
        # Measure characters, not bytes, so CRLF checkouts on Windows do not
        # inflate the size past the limit.
        size = len(full.read_text(encoding="utf-8", errors="replace"))
        assert size <= self.MAX_CHARS, f"{rel_path} is {size} chars (max {self.MAX_CHARS})"

    def test_root_agents_file_min_size(self) -> None:
        full = REPO_ROOT / "AGENTS.md"
        if not full.exists():
            pytest.skip("AGENTS.md not found")
        size = len(full.read_text(encoding="utf-8", errors="replace"))
        assert size >= self.ROOT_MIN_CHARS, (
            f"Root AGENTS.md is {size} chars (min {self.ROOT_MIN_CHARS})"
        )

    def test_root_agents_identifies_current_release(self) -> None:
        full = REPO_ROOT / "AGENTS.md"
        if not full.exists():
            pytest.skip("AGENTS.md not found")
        text = full.read_text(encoding="utf-8")
        assert "v1.0.1 Proven" in text, "Root AGENTS.md must state v1.0.1 Proven as current release"


class TestReadmeCurrentRelease:
    """README must correctly identify the current release."""

    def test_readme_refers_to_v101(self) -> None:
        readme = REPO_ROOT / "README.md"
        text = readme.read_text(encoding="utf-8")
        assert "v1.0.1 Proven" in text, "README must reference v1.0.1 Proven as current release"
        assert "is the current public release" in text, (
            "README must describe v1.0.1 as the current public release"
        )

    def test_no_alpha_banner_for_current_release(self) -> None:
        """v1.0.1 is stable; the README must not ship an alpha banner."""
        readme = REPO_ROOT / "README.md"
        text = readme.read_text(encoding="utf-8")
        assert "Alpha software" not in text, "README must not call the current release alpha"

    def test_readme_current_release_table_has_v101_on_top(self) -> None:
        readme = REPO_ROOT / "README.md"
        text = readme.read_text(encoding="utf-8")
        table = text.split("## Current Release", 1)[1]
        first_row = table.splitlines()[2]
        assert first_row.startswith("| Current | v1.0.1 Proven"), (
            f"Current Release table must list v1.0.1 as current: {first_row}"
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


class TestNoStaleStatusPhrases:
    """Current-status docs should not use pre-release language for published releases."""

    # Historical release docs and process records are exempt
    HISTORICAL = [
        "CHANGELOG.md",
        "ROADMAP.md",
        "docs/release/",
        "docs/rebrand/",
        "docs/plans/",
        "docs/codex/",
        "docs/maintenance/",
    ]
    STALE = [
        "release candidate",
        "unpublished release candidate",
        "publication pending",
        "v0.2.0 not published",
        "v0.2.0 development",
        "current public release: v0.3.1",
        "current development boundary: v0.4.0",
        "current development task: v0.4.0",
        "next planned product release: v0.4.0",
    ]

    def test_check_stale_phrases(self) -> None:
        for md_file in REPO_ROOT.rglob("*.md"):
            if ".git" in md_file.parts:
                continue
            rel = str(md_file.relative_to(REPO_ROOT)).replace("\\", "/")
            if any(rel.startswith(h) for h in self.HISTORICAL):
                continue
            text = md_file.read_text(encoding="utf-8", errors="replace")
            for phrase in self.STALE:
                if phrase.lower() in text.lower():
                    pytest.fail(f"Stale phrase '{phrase}' in {rel}")

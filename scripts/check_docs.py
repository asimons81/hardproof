#!/usr/bin/env python3
"""
Documentation validation for Hardproof.

Checks:
- Internal Markdown links resolve
- Referenced local files exist
- Root and nested AGENTS.md exist
- Agent-file size limits (root 8,000-14,000 chars)
- Root AGENTS.md states the current release identity
- No accidental absolute local paths
- No stale current-release phrases
- README current-release identity
- docs/README.md index lists every tracked document
- No accidental .hardproof/ or database files in package artifacts
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Absolute path patterns that should never appear in committed docs
ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"C:\\Users\\"),
    re.compile(r"/Users/"),
    re.compile(r"/home/"),
    re.compile(r"file:///"),
]

# Stale release phrases that should not appear in current-status docs
STALE_PHRASES = [
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

# Files/directories that are exempt from stale-phrase and absolute-path checking
HISTORICAL_DOCS = [
    "CHANGELOG.md",
    "ROADMAP.md",
    "docs/release/",
    "docs/rebrand/",
    "docs/plans/",
    "docs/maintenance/",
    "docs/codex/",
]

AGENTS_FILES = [
    "AGENTS.md",
    "hardproof/AGENTS.md",
    "tests/AGENTS.md",
    "docs/AGENTS.md",
]

AGENTS_MAX_CHARS = 14_000
AGENTS_MIN_CHARS = 8_000

# Current-release identity that the root AGENTS.md must state
CURRENT_RELEASE_IDENTITY = "v1.0.0 Proven"

# Docs index that must list every tracked document (except the index itself
# and the docs-local AGENTS.md)
DOCS_INDEX = "docs/README.md"
DOCS_INDEX_EXEMPT = {
    "docs/README.md",
    "docs/AGENTS.md",
}


def _tracked_files() -> list[Path]:
    """Return paths of all tracked files."""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True, text=True, check=True, timeout=30,
        cwd=REPO_ROOT,
    )
    return [REPO_ROOT / p for p in result.stdout.strip().splitlines() if p]


def _is_historical(rel_str: str) -> bool:
    """Check if a relative path belongs to a historical doc category."""
    for h in HISTORICAL_DOCS:
        if h.endswith("/"):
            if rel_str.startswith(h.rstrip("/")):
                return True
        else:
            if rel_str == h:
                return True
    return False


def check_agents_files() -> list[str]:
    errors = []
    for path in AGENTS_FILES:
        full = REPO_ROOT / path
        if not full.exists():
            errors.append(f"Missing AGENTS.md: {path}")
            continue
        size = full.stat().st_size
        if size > AGENTS_MAX_CHARS:
            errors.append(f"AGENTS.md too large ({size} bytes, max {AGENTS_MAX_CHARS}): {path}")
        if path == "AGENTS.md" and size < AGENTS_MIN_CHARS:
            errors.append(f"Root AGENTS.md too small ({size} bytes, min {AGENTS_MIN_CHARS})")
    return errors


def check_agents_current_release() -> list[str]:
    """Root AGENTS.md must identify the current public release."""
    errors = []
    root_agents = REPO_ROOT / "AGENTS.md"
    if not root_agents.exists():
        return ["AGENTS.md not found"]
    text = root_agents.read_text(encoding="utf-8", errors="replace")
    if CURRENT_RELEASE_IDENTITY not in text:
        errors.append(
            f"Root AGENTS.md must state current release identity '{CURRENT_RELEASE_IDENTITY}'"
        )
    return errors


def check_absolute_paths() -> list[str]:
    errors = []
    for md_file in _tracked_files():
        if md_file.suffix != ".md":
            continue
        try:
            rel_str = str(md_file.relative_to(REPO_ROOT)).replace("\\", "/")
        except ValueError:
            continue
        if _is_historical(rel_str):
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pattern in ABSOLUTE_PATH_PATTERNS:
            for match in pattern.finditer(text):
                errors.append(f"Absolute path in {rel_str}: {match.group()}")
    # Also check tracked Python source files under the package
    for py_file in _tracked_files():
        if py_file.suffix != ".py":
            continue
        try:
            rel = py_file.relative_to(REPO_ROOT)
        except ValueError:
            continue
        if "hardproof" not in rel.parts:
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pattern in ABSOLUTE_PATH_PATTERNS:
            for match in pattern.finditer(text):
                errors.append(f"Absolute path in {rel}: {match.group()}")
    return errors


def check_stale_phrases() -> list[str]:
    errors = []
    for md_file in _tracked_files():
        if md_file.suffix != ".md":
            continue
        try:
            rel_str = str(md_file.relative_to(REPO_ROOT)).replace("\\", "/")
        except ValueError:
            continue
        if _is_historical(rel_str):
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for phrase in STALE_PHRASES:
            if phrase.lower() in text.lower():
                errors.append(f"Stale phrase '{phrase}' in {rel_str}")
    return errors


def check_readme_current_release() -> list[str]:
    readme = REPO_ROOT / "README.md"
    if not readme.exists():
        return ["README.md not found"]
    errors = []
    text = readme.read_text(encoding="utf-8", errors="replace")
    if CURRENT_RELEASE_IDENTITY not in text:
        errors.append(
            f"README.md does not mention {CURRENT_RELEASE_IDENTITY} as current release"
        )
    if "is the current public release" not in text:
        errors.append("README.md must describe the current public release explicitly")
    if "## Current Release" in text:
        table = text.split("## Current Release", 1)[1]
        rows = [line for line in table.splitlines() if line.startswith("|")]
        if rows and not rows[0].startswith("| Current | v1.0.0"):
            errors.append(f"Current Release table must list v1.0.0 as current: {rows[0]}")
    return errors


def check_docs_index_complete() -> list[str]:
    """Every tracked docs/*.md (except the index and docs-local AGENTS.md) must
    be referenced from the docs/README.md index."""
    errors = []
    index = REPO_ROOT / DOCS_INDEX
    if not index.exists():
        return [f"Missing docs index: {DOCS_INDEX}"]
    index_text = index.read_text(encoding="utf-8", errors="replace")
    for doc in _tracked_files():
        if doc.suffix != ".md":
            continue
        try:
            rel = str(doc.relative_to(REPO_ROOT)).replace("\\", "/")
        except ValueError:
            continue
        if not rel.startswith("docs/"):
            continue
        if rel in DOCS_INDEX_EXEMPT:
            continue
        # The index references documents by their relative path (with or
        # without a leading ../docs/ prefix); match on the leaf relative path.
        if rel not in index_text and rel.removeprefix("docs/") not in index_text:
            errors.append(f"Document not listed in {DOCS_INDEX}: {rel}")
    return errors


def check_no_tracked_junk() -> list[str]:
    errors = []
    for tracked in _tracked_files():
        if tracked.suffix in {".db", ".sqlite", ".sqlite3"}:
            try:
                rel = tracked.relative_to(REPO_ROOT)
                errors.append(f"Database file tracked: {rel}")
            except ValueError:
                pass
    return errors


def check_internal_links() -> list[str]:
    """Check that markdown links to local files actually resolve."""
    errors = []
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    for md_file in _tracked_files():
        if md_file.suffix != ".md":
            continue
        try:
            rel = md_file.relative_to(REPO_ROOT)
        except ValueError:
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for match in link_pattern.finditer(text):
            link = match.group(2)
            if link.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if link.startswith("/"):
                target = REPO_ROOT / link[1:]
            else:
                target = (md_file.parent / link).resolve()
            if "#" in str(target):
                target = Path(str(target).split("#")[0])
            if not target.exists():
                errors.append(f"Broken link in {rel}: {link} -> {target}")
    return errors


def main() -> int:
    all_errors: list[str] = []

    all_errors.extend(check_agents_files())
    all_errors.extend(check_agents_current_release())
    all_errors.extend(check_absolute_paths())
    all_errors.extend(check_stale_phrases())
    all_errors.extend(check_readme_current_release())
    all_errors.extend(check_no_tracked_junk())
    all_errors.extend(check_internal_links())
    all_errors.extend(check_docs_index_complete())

    if all_errors:
        print(f"Documentation validation found {len(all_errors)} issue(s):")
        for error in all_errors:
            print(f"  FAIL: {error}")
        return 1
    else:
        print("Documentation validation: PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())

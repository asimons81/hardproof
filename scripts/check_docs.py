#!/usr/bin/env python3
"""
Documentation validation for Hardproof.

Checks:
- Internal Markdown links resolve
- Referenced local files exist
- Root and nested AGENTS.md exist
- Agent-file size limits
- No accidental absolute local paths
- No stale current-release phrases
- README current-release identity
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

AGENTS_MAX_CHARS = 16_000


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
    # Also check tracked Python source files
    for py_file in _tracked_files():
        if py_file.suffix != ".py":
            continue
        if "hardproof" not in py_file.parts:
            continue
        try:
            rel = py_file.relative_to(REPO_ROOT)
        except ValueError:
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
    if "v0.2.0 Gatehouse" not in text:
        errors.append("README.md does not mention v0.2.0 Gatehouse as current release")
    if "v0.3.0" in text and "not started" not in text.lower() and "planned" not in text.lower():
        errors.append("README.md references v0.3.0 without 'not started' or 'planned' qualifier")
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
    all_errors.extend(check_absolute_paths())
    all_errors.extend(check_stale_phrases())
    all_errors.extend(check_readme_current_release())
    all_errors.extend(check_no_tracked_junk())
    all_errors.extend(check_internal_links())

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

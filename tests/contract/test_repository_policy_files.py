from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_required_policy_files_exist() -> None:
    for relative_path in (
        "INSPIRATION.md",
        "NOTICE",
        "docs/adr/0001-clean-room-implementation.md",
    ):
        assert (ROOT / relative_path).is_file(), relative_path


def test_inspiration_declares_clean_room_boundary() -> None:
    text = (ROOT / "INSPIRATION.md").read_text(encoding="utf-8").lower()
    assert "clean-room" in text
    assert "conceptual inspiration" in text
    for prohibited in ("source code", "skills", "prompts", "fixtures", "documentation wording"):
        assert prohibited in text


def test_upstream_namespace_absent_from_package_and_skill_paths() -> None:
    package = ROOT / "hardproof"
    if not package.exists():
        return
    for path in package.rglob("*"):
        relative = path.relative_to(package).as_posix().lower()
        assert "superpowers" not in relative

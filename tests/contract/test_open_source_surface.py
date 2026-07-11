from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
    "GOVERNANCE.md", "SUPPORT.md", "CHANGELOG.md", "ROADMAP.md",
    "docs/architecture.md", "docs/development.md", "docs/releasing.md",
    ".github/CODEOWNERS", ".github/dependabot.yml",
    ".github/ISSUE_TEMPLATE/bug.yml", ".github/ISSUE_TEMPLATE/feature.yml",
    ".github/ISSUE_TEMPLATE/config.yml", ".github/pull_request_template.md",
)


def test_required_open_source_files_exist_and_are_nontrivial() -> None:
    for relative in REQUIRED:
        path = ROOT / relative
        assert path.is_file(), relative
        assert len(path.read_text(encoding="utf-8")) >= 80, relative


def test_readme_covers_product_and_operator_contract() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "alpha", "install", "enable", "first run", "profiles", "architecture",
        "security boundary", "privacy", "roadmap", "contributing", "inspiration", "apache-2.0",
    ):
        assert phrase in text
    assert "no telemetry" in text
    assert "not a security sandbox" in text


def test_governance_and_contribution_policy_are_explicit() -> None:
    governance = (ROOT / "GOVERNANCE.md").read_text(encoding="utf-8").lower()
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8").lower()
    assert "maintainer-led" in governance
    assert "rfc" in governance
    assert "developer certificate of origin" in contributing
    assert "signed-off-by" in contributing
    assert "telemetry" in governance and "opt-in" in governance


def test_license_is_full_apache_2_text() -> None:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION" in text
    assert "END OF TERMS AND CONDITIONS" in text


def test_public_docs_contain_no_scaffold_markers() -> None:
    for path in [ROOT / item for item in REQUIRED] + list((ROOT / "docs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "TODO" not in text
        assert "TBD" not in text

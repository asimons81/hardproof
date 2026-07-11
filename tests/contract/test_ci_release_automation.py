from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def workflow(name: str) -> dict:
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))


def test_ci_has_required_platform_matrix_and_jobs() -> None:
    data = workflow("ci.yml")
    serialized = str(data).lower()
    for platform in ("ubuntu-latest", "macos-latest", "windows-latest"):
        assert platform in serialized
    for version in ("3.11", "3.12"):
        assert version in serialized
    for requirement in (
        "ruff", "mypy", "unit", "integration", "build", "smoke", "package-data",
        "pip-audit", "license", "coverage",
    ):
        assert requirement in serialized
    assert "--cov-fail-under=85" in serialized
    assert "--cov-fail-under=95" in serialized


def test_security_workflows_have_least_privilege_and_expected_analysis() -> None:
    codeql = workflow("codeql.yml")
    scorecard = workflow("scorecard.yml")
    assert "security-events" in str(codeql).lower()
    assert "codeql-action" in str(codeql).lower()
    assert "scorecard-action" in str(scorecard).lower()
    assert "id-token" in str(scorecard).lower()


def test_release_requires_tag_version_signature_branch_and_trusted_publish() -> None:
    text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8").lower()
    for phrase in (
        "tags:", "git tag -v", "verify tag matches", "verify commit is on main",
        "build_sbom.py", "sha256", "attest-build-provenance", "pypi-publish",
        "environment: pypi", "id-token: write",
    ):
        assert phrase in text


def test_sbom_script_and_workflows_exist() -> None:
    for relative in (
        "scripts/build_sbom.py", ".github/workflows/ci.yml", ".github/workflows/codeql.yml",
        ".github/workflows/scorecard.yml", ".github/workflows/release.yml",
    ):
        assert (ROOT / relative).is_file(), relative

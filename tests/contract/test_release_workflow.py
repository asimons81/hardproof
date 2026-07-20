from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def test_release_workflow_preserves_publish_contract() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    for required in (
        'tags: ["v*"]',
        "contents: write",
        "id-token: write",
        "attestations: write",
        "uses: softprops/action-gh-release@v3",
        "generate_release_notes: true",
        "dist/*.whl",
        "dist/*.tar.gz",
        "dist/*.json",
        "dist/SHA256SUMS",
        "uses: pypa/gh-action-pypi-publish@release/v1",
    ):
        assert required in text, f"release workflow lost required contract: {required}"

    release_index = text.index("uses: softprops/action-gh-release@v3")
    cleanup_index = text.index("Clean dist for PyPI")
    publish_index = text.index("uses: pypa/gh-action-pypi-publish@release/v1")
    assert release_index < cleanup_index < publish_index


def test_release_workflow_uses_reproducible_python_environment() -> None:
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    for required in (
        "PIP_CONSTRAINT: constraints/ci.txt",
        "PIP_BUILD_CONSTRAINT: constraints/ci.txt",
        "cache-dependency-path:",
        "constraints/ci.txt",
        'python -m pip install --upgrade "pip==26.1.2"',
        'python -m pip install -e ".[dev]"',
    ):
        assert required in text, f"release workflow lost reproducibility contract: {required}"

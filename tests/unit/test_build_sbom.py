from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

from scripts.build_sbom import sha256_file, write_checksums


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_sbom.py"


def run_generator(directory: Path) -> None:
    subprocess.run(
        [sys.executable, str(SCRIPT), str(directory)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_checksum_manifest_is_sorted_and_reproducible(tmp_path: Path) -> None:
    (tmp_path / "b.whl").write_bytes(b"b")
    (tmp_path / "a.tar.gz").write_bytes(b"a")
    destination = tmp_path / "SHA256SUMS"
    write_checksums([tmp_path / "b.whl", tmp_path / "a.tar.gz"], destination)
    first = destination.read_bytes()
    write_checksums([tmp_path / "a.tar.gz", tmp_path / "b.whl"], destination)
    assert destination.read_bytes() == first
    assert destination.read_text(encoding="utf-8").splitlines()[0].endswith("  a.tar.gz")
    assert sha256_file(tmp_path / "a.tar.gz") in destination.read_text(encoding="utf-8")


def test_sbom_generation_is_reproducible_and_preserves_project_contract(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "dist"
    directory.mkdir()
    (directory / "hardproof-0.3.1-py3-none-any.whl").write_bytes(b"wheel")
    (directory / "hardproof-0.3.1.tar.gz").write_bytes(b"sdist")

    run_generator(directory)
    first_sbom = (directory / "hardproof.cdx.json").read_bytes()
    first_checksums = (directory / "SHA256SUMS").read_bytes()
    run_generator(directory)

    assert (directory / "hardproof.cdx.json").read_bytes() == first_sbom
    assert (directory / "SHA256SUMS").read_bytes() == first_checksums

    document = json.loads(first_sbom)
    assert document["bomFormat"] == "CycloneDX"
    assert document["specVersion"] == "1.6"
    assert "serialNumber" not in document
    assert "timestamp" not in document["metadata"]
    assert {item["name"] for item in document["metadata"]["properties"]} == {
        "cdx:reproducible"
    }

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    root = document["metadata"]["component"]
    assert root["name"] == project["name"]
    assert root["version"] == project["version"]
    assert {component["name"] for component in document["components"]} == {"PyYAML"}

    checksum_text = first_checksums.decode("utf-8")
    assert "hardproof.cdx.json" in checksum_text
    assert "hardproof-0.3.1-py3-none-any.whl" in checksum_text
    assert "hardproof-0.3.1.tar.gz" in checksum_text


def test_sbom_toolchain_does_not_reintroduce_cyclonedx_cli_chardet_cap() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    constraints = (ROOT / "constraints" / "ci.txt").read_text(encoding="utf-8")

    assert "cyclonedx-python-lib>=11" in pyproject
    assert "cyclonedx-bom" not in pyproject
    assert "cyclonedx-bom==" not in constraints
    assert "chardet==" not in constraints

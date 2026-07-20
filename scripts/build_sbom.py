"""Generate a reproducible CycloneDX SBOM and deterministic artifact checksums."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from importlib.metadata import version
from pathlib import Path
from typing import Any, Iterable

from cyclonedx.model import Property
from cyclonedx.model.bom import Bom, BomMetaData
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.dependency import Dependency
from cyclonedx.model.license import DisjunctiveLicense, LicenseAcknowledgement
from cyclonedx.model.tool import ToolRepository
from cyclonedx.output.json import JsonV1Dot6
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packageurl import PackageURL


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_checksums(paths: Iterable[Path], destination: Path) -> None:
    lines = [
        f"{sha256_file(path)}  {path.name}"
        for path in sorted(paths, key=lambda item: item.name)
    ]
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def project_metadata(pyproject: Path) -> dict[str, Any]:
    document = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = document.get("project")
    if not isinstance(project, dict):
        raise ValueError(f"missing [project] table in {pyproject}")
    return project


def declared_licenses(project: dict[str, Any]) -> list[DisjunctiveLicense]:
    declared = project.get("license")
    if not isinstance(declared, str) or not declared:
        return []
    return [
        DisjunctiveLicense(
            id=declared,
            acknowledgement=LicenseAcknowledgement.DECLARED,
        )
    ]


def direct_dependency_components(project: dict[str, Any]) -> list[Component]:
    raw_dependencies = project.get("dependencies", [])
    if not isinstance(raw_dependencies, list):
        raise ValueError("project.dependencies must be a list")

    components: list[Component] = []
    for index, raw in enumerate(raw_dependencies, start=1):
        if not isinstance(raw, str):
            raise ValueError("project.dependencies entries must be strings")
        requirement = Requirement(raw)
        components.append(
            Component(
                name=requirement.name,
                type=ComponentType.LIBRARY,
                bom_ref=f"requirements-L{index}",
                description=f"project dependency: {raw}",
                purl=PackageURL(
                    type="pypi",
                    name=canonicalize_name(requirement.name),
                ),
            )
        )
    return components


def build_bom(project: dict[str, Any]) -> Bom:
    root = Component(
        name=str(project["name"]),
        version=str(project["version"]),
        type=ComponentType.LIBRARY,
        bom_ref="root-component",
        description=str(project.get("description", "")) or None,
        licenses=declared_licenses(project),
    )
    components = direct_dependency_components(project)
    dependency_nodes = [Dependency(component.bom_ref) for component in components]
    tool = Component(
        name="cyclonedx-python-lib",
        group="CycloneDX",
        version=version("cyclonedx-python-lib"),
        type=ComponentType.LIBRARY,
        bom_ref="tool-cyclonedx-python-lib",
        purl=PackageURL(type="pypi", name="cyclonedx-python-lib"),
    )
    metadata = BomMetaData(
        component=root,
        tools=ToolRepository(components=[tool]),
        properties=[Property(name="cdx:reproducible", value="true")],
    )
    return Bom(
        components=components,
        metadata=metadata,
        dependencies=[
            *dependency_nodes,
            Dependency(root.bom_ref, dependencies=dependency_nodes),
        ],
    )


def write_reproducible_sbom(bom: Bom, destination: Path) -> None:
    document = json.loads(JsonV1Dot6(bom).output_as_string())
    document.pop("serialNumber", None)
    metadata = document.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("timestamp", None)
    destination.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default="dist", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    artifacts = [
        path
        for path in directory.iterdir()
        if path.is_file() and (path.suffix == ".whl" or path.name.endswith(".tar.gz"))
    ]
    if not artifacts:
        parser.error(f"no wheel or sdist artifacts found in {directory}")

    sbom = directory / "hardproof.cdx.json"
    project = project_metadata(Path("pyproject.toml").resolve())
    write_reproducible_sbom(build_bom(project), sbom)
    write_checksums([*artifacts, sbom], directory / "SHA256SUMS")
    print(f"SBOM: {sbom}")
    print(f"Checksums: {directory / 'SHA256SUMS'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate a CycloneDX environment SBOM and deterministic artifact checksums."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_checksums(paths: Iterable[Path], destination: Path) -> None:
    lines = [f"{sha256_file(path)}  {path.name}" for path in sorted(paths, key=lambda item: item.name)]
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default="dist", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    artifacts = [
        path for path in directory.iterdir()
        if path.is_file() and (path.suffix == ".whl" or path.name.endswith(".tar.gz"))
    ]
    if not artifacts:
        parser.error(f"no wheel or sdist artifacts found in {directory}")
    sbom = directory / "hardproof.cdx.json"
    subprocess.run(
        [
            sys.executable, "-m", "cyclonedx_py", "environment",
            "--output-format", "JSON", "--output-file", str(sbom),
        ],
        check=True,
    )
    write_checksums([*artifacts, sbom], directory / "SHA256SUMS")
    print(f"SBOM: {sbom}")
    print(f"Checksums: {directory / 'SHA256SUMS'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

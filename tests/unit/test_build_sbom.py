from pathlib import Path

from scripts.build_sbom import sha256_file, write_checksums


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

from __future__ import annotations

import importlib
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_version_metadata_matches_manifest() -> None:
    import tomllib

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text(encoding="utf-8"))
    package = importlib.import_module("crucible_agent")
    assert metadata["project"]["version"] == "0.2.0"
    assert metadata["project"]["version"] == manifest["version"] == package.__version__


def test_entry_point_and_root_wrapper_resolve() -> None:
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'crucible = "crucible_agent.plugin"' in metadata
    root_wrapper = importlib.import_module("__init__")
    plugin = importlib.import_module("crucible_agent.plugin")
    assert root_wrapper.register is plugin.register


def test_built_wheel_contains_required_package_data() -> None:
    wheels = sorted((ROOT / "dist").glob("*.whl"))
    assert wheels, "build the wheel before running this contract"
    with zipfile.ZipFile(wheels[-1]) as archive:
        names = set(archive.namelist())
    assert "crucible_agent/templates/completion.md" in names
    assert "crucible_agent/migrations/001_initial.sql" in names
    assert "crucible_agent/migrations/002_gatehouse.sql" in names
    assert "crucible_agent/skills/orchestrate/SKILL.md" in names

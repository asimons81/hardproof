from __future__ import annotations

from pathlib import Path

import pytest

from crucible_agent.config import ConfigError, load_config
from crucible_agent.domain.enums import RunProfile


def test_missing_config_loads_safe_defaults_without_creating_file(tmp_path: Path) -> None:
    path = tmp_path / ".crucible" / "config.yaml"
    config = load_config(path)
    assert config.schema_version == 1
    assert config.default_profile is RunProfile.STANDARD
    assert config.artifact_directory == Path(".crucible/runs")
    assert config.verification_checks
    assert not path.exists()


def test_project_config_overrides_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "schema_version: 1\ndefault_profile: critical\nmaximum_stored_output_size: 2048\n",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.default_profile is RunProfile.CRITICAL
    assert config.maximum_stored_output_size == 2048
    assert config.terminal_blocked_patterns


def test_unknown_top_level_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("schema_version: 1\nsurprise: true\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="unknown config keys"):
        load_config(path)


def test_malformed_yaml_is_actionable(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("schema_version: [", encoding="utf-8")
    with pytest.raises(ConfigError, match="YAML"):
        load_config(path)


def test_artifact_path_rejects_traversal(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("schema_version: 1\nartifact_directory: ../outside\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="artifact_directory"):
        load_config(path)


def test_environment_expansion_only_applies_to_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CRUCIBLE_ARTIFACT_ROOT", "project-artifacts")
    path = tmp_path / "config.yaml"
    path.write_text(
        "schema_version: 1\nartifact_directory: ${CRUCIBLE_ARTIFACT_ROOT}/runs\n",
        encoding="utf-8",
    )
    assert load_config(path).artifact_directory == Path("project-artifacts/runs")
    path.write_text("schema_version: 1\ndefault_profile: ${PROFILE}\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def test_verification_check_validation(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "schema_version: 1\nverification_checks:\n  - name: tests\n    command: python -m pytest\n    required: true\n    timeout_seconds: 0\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="timeout"):
        load_config(path)

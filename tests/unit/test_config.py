from __future__ import annotations

from pathlib import Path

import pytest

from hardproof.config import ConfigError, config_fingerprint, load_config
from hardproof.domain.enums import RunProfile, RunStage


def test_missing_config_loads_safe_defaults_without_creating_file(tmp_path: Path) -> None:
    path = tmp_path / ".hardproof" / "config.yaml"
    config = load_config(path)
    assert config.schema_version == 2
    assert config.default_profile is RunProfile.STANDARD
    assert config.artifact_directory == Path(".hardproof/runs")
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
    assert config.schema_version == 2
    assert config.source_schema_version == 1


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
    monkeypatch.setenv("HARDPROOF_ARTIFACT_ROOT", "project-artifacts")
    path = tmp_path / "config.yaml"
    path.write_text(
        "schema_version: 1\nartifact_directory: ${HARDPROOF_ARTIFACT_ROOT}/runs\n",
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


def test_v2_named_policy_rules_are_strict_and_typed(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """schema_version: 2
policy:
  state_failure_mode: closed
  packs: [python, node]
  rules:
    - key: project.generated.allow
      effect: allow
      tools: [write_file]
      path_glob: generated/**
      profiles: [standard]
      stages: [DESIGN]
      rationale: Generated client output is reviewed.
""",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.policy.state_failure_mode == "closed"
    assert config.policy.packs == ("python", "node")
    rule = config.policy.rules[0]
    assert rule.key == "project.generated.allow"
    assert rule.profiles == (RunProfile.STANDARD,)
    assert rule.stages == (RunStage.DESIGN,)
    assert config_fingerprint(config) == config_fingerprint(load_config(path))


@pytest.mark.parametrize(
    ("rule_yaml", "message"),
    [
        ("key: terminal.immutable.force_push\n      effect: allow", "project rule key"),
        ("key: project.bad\n      effect: bypass", "effect"),
        ("key: project.bad\n      effect: deny\n      command_regex: '(a+)+$'", "unsafe"),
        ("key: project.bad\n      effect: deny\n      path_glob: ../outside/**", "path_glob"),
        ("key: project.bad\n      effect: deny\n      surprise: true", "unknown"),
    ],
)
def test_unsafe_or_unknown_policy_rule_fields_fail_closed(
    tmp_path: Path, rule_yaml: str, message: str
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "schema_version: 2\npolicy:\n  rules:\n    - " + rule_yaml + "\n      tools: [terminal]\n      rationale: reviewed\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match=message):
        load_config(path)


def test_policy_rejects_duplicate_keys_unknown_pack_and_open_critical_default(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """schema_version: 2
default_profile: critical
policy:
  state_failure_mode: open
  packs: [unknown]
  rules:
    - {key: project.same, effect: deny, tools: [terminal], rationale: one}
    - {key: project.same, effect: deny, tools: [terminal], rationale: two}
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="state_failure_mode.*critical"):
        load_config(path)


@pytest.mark.parametrize(
    ("policy_yaml", "message"),
    [
        ("packs: [python, unknown]", "unknown packs"),
        (
            """rules:
    - {key: project.same, effect: deny, tools: [terminal], rationale: one}
    - {key: project.same, effect: approval, tools: [terminal], rationale: two}""",
            "keys must be unique",
        ),
    ],
)
def test_policy_pack_and_rule_identity_validation(
    tmp_path: Path, policy_yaml: str, message: str
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("schema_version: 2\npolicy:\n  " + policy_yaml + "\n", encoding="utf-8")
    with pytest.raises(ConfigError, match=message):
        load_config(path)


def test_v1_compatibility_migration_has_same_effective_fingerprint(tmp_path: Path) -> None:
    v1 = tmp_path / "v1.yaml"
    v2 = tmp_path / "v2.yaml"
    v1.write_text("schema_version: 1\ndefault_profile: standard\n", encoding="utf-8")
    v2.write_text("schema_version: 2\ndefault_profile: standard\n", encoding="utf-8")
    first = load_config(v1)
    second = load_config(v2)
    assert first.source_schema_version == 1 and second.source_schema_version == 2
    assert config_fingerprint(first) == config_fingerprint(second)


def test_policy_regex_and_glob_values_never_expand_environment(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        """schema_version: 2
policy:
  rules:
    - key: project.literal
      effect: deny
      tools: [terminal]
      command_regex: '${TOKEN}'
      path_glob: '${HOME}/**'
      rationale: literal values
""",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.policy.rules[0].command_regex == "${TOKEN}"
    assert config.policy.rules[0].path_glob == "${HOME}/**"

"""Strict project configuration with safe local defaults."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from hardproof.constants import SCHEMA_VERSION
from hardproof.domain.enums import RunProfile
from hardproof.paths import safe_project_relative


class ConfigError(ValueError):
    """Project configuration is malformed or unsafe."""


@dataclass(frozen=True, slots=True)
class VerificationCheckConfig:
    name: str
    command: str
    required: bool = True
    timeout_seconds: int = 300

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.command.strip():
            raise ConfigError("verification check name and command must be non-empty")
        if self.timeout_seconds < 1:
            raise ConfigError("verification check timeout must be positive")


@dataclass(frozen=True, slots=True)
class HardproofConfig:
    schema_version: int
    default_profile: RunProfile
    artifact_directory: Path
    verification_checks: tuple[VerificationCheckConfig, ...]
    stage_policy_overrides: dict[str, Any]
    terminal_read_only_prefixes: tuple[str, ...]
    terminal_blocked_patterns: tuple[str, ...]
    output_redaction_patterns: tuple[str, ...]
    maximum_stored_output_size: int
    mutating_tools: tuple[str, ...]


DEFAULTS: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "default_profile": "standard",
    "artifact_directory": ".hardproof/runs",
    "verification_checks": [
        {"name": "tests", "command": "python -m pytest", "required": True, "timeout_seconds": 300}
    ],
    "stage_policy_overrides": {},
    "terminal_read_only_prefixes": ["git status", "git diff", "git log", "python -m pytest"],
    "terminal_blocked_patterns": ["git push --force", "git reset --hard", "git clean -f"],
    "output_redaction_patterns": [
        r"(?i)(api[_-]?key|token|password|authorization|cookie)\s*[:=]\s*\S+"
    ],
    "maximum_stored_output_size": 1_048_576,
    "mutating_tools": ["write_file", "patch", "edit_file", "execute_code", "terminal"],
}

ALLOWED_KEYS = frozenset(DEFAULTS)
_ENV = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_SECRET_ENV = re.compile(r"(?i)(secret|token|password|key|credential|auth|cookie)")


def _expand_path(value: Any) -> Path:
    if not isinstance(value, str):
        raise ConfigError("artifact_directory must be a string path")

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if _SECRET_ENV.search(name):
            raise ConfigError("artifact_directory cannot expand a secret-like environment variable")
        if name not in os.environ:
            raise ConfigError(f"artifact_directory environment variable {name} is not set")
        return os.environ[name]

    try:
        return safe_project_relative(_ENV.sub(replace, value))
    except ValueError as exc:
        raise ConfigError(f"invalid artifact_directory: {exc}") from exc


def _string_tuple(name: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ConfigError(f"{name} must be a list of non-empty strings")
    return tuple(value)


def load_config(path: str | Path) -> HardproofConfig:
    """Load a project config over defaults without creating or modifying it."""
    config_path = Path(path)
    supplied: dict[str, Any] = {}
    if config_path.exists():
        try:
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigError(f"invalid YAML in {config_path}: {exc}") from exc
        if loaded is None:
            loaded = {}
        if not isinstance(loaded, dict):
            raise ConfigError("YAML config root must be a mapping")
        supplied = loaded
    unknown = sorted(set(supplied) - ALLOWED_KEYS)
    if unknown:
        raise ConfigError(f"unknown config keys: {', '.join(unknown)}")
    values = {**DEFAULTS, **supplied}
    if values["schema_version"] != SCHEMA_VERSION:
        raise ConfigError(f"unsupported config schema_version: {values['schema_version']}")
    try:
        profile = RunProfile(values["default_profile"])
    except (TypeError, ValueError) as exc:
        raise ConfigError("default_profile must be quick, standard, or critical") from exc
    checks_value = values["verification_checks"]
    if not isinstance(checks_value, list) or not checks_value:
        raise ConfigError("verification_checks must be a non-empty list")
    try:
        checks = tuple(VerificationCheckConfig(**item) for item in checks_value)
    except (TypeError, ConfigError) as exc:
        raise ConfigError(f"invalid verification_checks: {exc}") from exc
    if len({check.name for check in checks}) != len(checks):
        raise ConfigError("verification check names must be unique")
    overrides = values["stage_policy_overrides"]
    if not isinstance(overrides, dict):
        raise ConfigError("stage_policy_overrides must be a mapping")
    maximum = values["maximum_stored_output_size"]
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
        raise ConfigError("maximum_stored_output_size must be a positive integer")
    return HardproofConfig(
        schema_version=SCHEMA_VERSION,
        default_profile=profile,
        artifact_directory=_expand_path(values["artifact_directory"]),
        verification_checks=checks,
        stage_policy_overrides=dict(overrides),
        terminal_read_only_prefixes=_string_tuple(
            "terminal_read_only_prefixes", values["terminal_read_only_prefixes"]
        ),
        terminal_blocked_patterns=_string_tuple(
            "terminal_blocked_patterns", values["terminal_blocked_patterns"]
        ),
        output_redaction_patterns=_string_tuple(
            "output_redaction_patterns", values["output_redaction_patterns"]
        ),
        maximum_stored_output_size=maximum,
        mutating_tools=_string_tuple("mutating_tools", values["mutating_tools"]),
    )

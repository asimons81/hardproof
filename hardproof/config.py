"""Strict project configuration with safe local defaults."""

from __future__ import annotations

import os
import re
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from hardproof.constants import CONFIG_SCHEMA_VERSION
from hardproof.domain.enums import RunProfile, RunStage
from hardproof.paths import safe_project_relative
from hardproof.policy.stage_graph import StageGraphError, compile_stage_graph


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
class PolicyRuleConfig:
    key: str
    effect: str
    tools: tuple[str, ...]
    rationale: str
    command_regex: str | None = None
    path_glob: str | None = None
    profiles: tuple[RunProfile, ...] = ()
    stages: tuple[RunStage, ...] = ()


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    state_failure_mode: str
    rules: tuple[PolicyRuleConfig, ...]
    packs: tuple[str, ...]
    stage_graph: dict[str, Any]


@dataclass(frozen=True, slots=True)
class WorkcellsConfig:
    enabled: bool
    maximum_attempts: int
    default_model_tier: str
    profile_minimum_tiers: dict[RunProfile, str]
    model_selectors: dict[str, str]
    maximum_active_children: int
    allow_shared_workspace_concurrency: bool
    maximum_concurrent_mutating_tasks: int
    brief_size_limit: int
    context_manifest_size_limit: int
    result_size_limit: int
    claim_timeout_seconds: int
    recovery_behavior: str


@dataclass(frozen=True, slots=True)
class HardproofConfig:
    schema_version: int
    source_schema_version: int
    default_profile: RunProfile
    artifact_directory: Path
    verification_checks: tuple[VerificationCheckConfig, ...]
    stage_policy_overrides: dict[str, Any]
    terminal_read_only_prefixes: tuple[str, ...]
    terminal_blocked_patterns: tuple[str, ...]
    output_redaction_patterns: tuple[str, ...]
    maximum_stored_output_size: int
    mutating_tools: tuple[str, ...]
    policy: PolicyConfig
    workcells: WorkcellsConfig


DEFAULTS: dict[str, Any] = {
    "schema_version": CONFIG_SCHEMA_VERSION,
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
    "policy": {
        "state_failure_mode": "profile",
        "rules": [],
        "packs": [],
        "stage_graph": {},
    },
    "workcells": {
        "enabled": True,
        "maximum_attempts": 3,
        "default_model_tier": "standard",
        "profile_minimum_tiers": {"quick": "economy", "standard": "standard", "critical": "strong"},
        "model_selectors": {"economy": "economy", "standard": "standard", "strong": "strong"},
        "maximum_active_children": 1,
        "allow_shared_workspace_concurrency": False,
        "maximum_concurrent_mutating_tasks": 1,
        "brief_size_limit": 65_536,
        "context_manifest_size_limit": 32_768,
        "result_size_limit": 65_536,
        "claim_timeout_seconds": 900,
        "recovery_behavior": "interrupt",
    },
}

ALLOWED_KEYS = frozenset(DEFAULTS)
_ENV = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_SECRET_ENV = re.compile(r"(?i)(secret|token|password|key|credential|auth|cookie)")
_PROJECT_RULE_KEY = re.compile(r"^project\.[a-z0-9][a-z0-9_.-]{0,126}$")
_NESTED_QUANTIFIER = re.compile(r"\([^)]*[+*][^)]*\)[+*{]")
_POLICY_KEYS = frozenset({"state_failure_mode", "rules", "packs", "stage_graph"})
_RULE_KEYS = frozenset(
    {"key", "effect", "tools", "rationale", "command_regex", "path_glob", "profiles", "stages"}
)
_PACKS = frozenset({"python", "node", "rust", "go"})
_WORKCELL_KEYS = frozenset({
    "enabled", "maximum_attempts", "default_model_tier", "profile_minimum_tiers",
    "model_selectors", "maximum_active_children", "allow_shared_workspace_concurrency",
    "maximum_concurrent_mutating_tasks", "brief_size_limit", "context_manifest_size_limit",
    "result_size_limit", "claim_timeout_seconds", "recovery_behavior",
})
_MODEL_TIERS = frozenset({"economy", "standard", "strong"})


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


def _policy_rule(value: Any, index: int) -> PolicyRuleConfig:
    location = f"policy.rules[{index}]"
    if not isinstance(value, dict):
        raise ConfigError(f"{location} must be a mapping")
    unknown = sorted(set(value) - _RULE_KEYS)
    if unknown:
        raise ConfigError(f"{location} has unknown keys: {', '.join(unknown)}")
    key = value.get("key")
    if not isinstance(key, str) or not _PROJECT_RULE_KEY.fullmatch(key):
        raise ConfigError(f"{location}.key must be a project rule key beginning with project.")
    effect = value.get("effect")
    if effect not in {"allow", "deny", "approval"}:
        raise ConfigError(f"{location}.effect must be allow, deny, or approval")
    tools = _string_tuple(f"{location}.tools", value.get("tools"))
    if len(tools) > 32:
        raise ConfigError(f"{location}.tools cannot contain more than 32 entries")
    rationale = value.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ConfigError(f"{location}.rationale must be non-empty")
    command_regex = value.get("command_regex")
    if command_regex is not None:
        if not isinstance(command_regex, str) or not command_regex or len(command_regex) > 256:
            raise ConfigError(f"{location}.command_regex must be 1 to 256 characters")
        if "(?" in command_regex or re.search(r"\\[1-9]", command_regex) or _NESTED_QUANTIFIER.search(command_regex):
            raise ConfigError(f"{location}.command_regex uses an unsafe regex construct")
        try:
            re.compile(command_regex)
        except re.error as exc:
            raise ConfigError(f"{location}.command_regex is invalid: {exc}") from exc
    path_glob = value.get("path_glob")
    if path_glob is not None:
        if not isinstance(path_glob, str) or not path_glob or len(path_glob) > 256:
            raise ConfigError(f"{location}.path_glob must be 1 to 256 characters")
        normalized = PurePosixPath(path_glob.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ConfigError(f"{location}.path_glob must be project-relative without traversal")
    profiles_value = value.get("profiles", [])
    stages_value = value.get("stages", [])
    try:
        profiles = tuple(RunProfile(item) for item in _string_tuple(f"{location}.profiles", profiles_value))
    except ValueError as exc:
        raise ConfigError(f"{location}.profiles contains an unknown profile") from exc
    try:
        stages = tuple(RunStage(item) for item in _string_tuple(f"{location}.stages", stages_value))
    except ValueError as exc:
        raise ConfigError(f"{location}.stages contains an unknown stage") from exc
    return PolicyRuleConfig(
        key, effect, tools, rationale.strip(), command_regex, path_glob, profiles, stages
    )


def _policy(value: Any, default_profile: RunProfile) -> PolicyConfig:
    if not isinstance(value, dict):
        raise ConfigError("policy must be a mapping")
    unknown = sorted(set(value) - _POLICY_KEYS)
    if unknown:
        raise ConfigError(f"policy has unknown keys: {', '.join(unknown)}")
    mode = value.get("state_failure_mode", "profile")
    if mode not in {"profile", "open", "closed"}:
        raise ConfigError("policy.state_failure_mode must be profile, open, or closed")
    if mode == "open" and default_profile is RunProfile.CRITICAL:
        raise ConfigError("policy.state_failure_mode open is invalid with critical default_profile")
    rules_value = value.get("rules", [])
    if not isinstance(rules_value, list):
        raise ConfigError("policy.rules must be a list")
    if len(rules_value) > 128:
        raise ConfigError("policy.rules cannot contain more than 128 entries")
    rules = tuple(_policy_rule(item, index) for index, item in enumerate(rules_value))
    if len({rule.key for rule in rules}) != len(rules):
        raise ConfigError("policy.rules keys must be unique")
    packs = _string_tuple("policy.packs", value.get("packs", []))
    unknown_packs = sorted(set(packs) - _PACKS)
    if unknown_packs:
        raise ConfigError(f"policy.packs contains unknown packs: {', '.join(unknown_packs)}")
    if len(set(packs)) != len(packs):
        raise ConfigError("policy.packs must not contain duplicates")
    stage_graph = value.get("stage_graph", {})
    try:
        compile_stage_graph(stage_graph, profile=default_profile)
        for profile in RunProfile:
            compile_stage_graph(stage_graph, profile=profile)
    except StageGraphError as exc:
        raise ConfigError(str(exc)) from exc
    return PolicyConfig(mode, rules, packs, dict(stage_graph))


def _workcells(value: Any) -> WorkcellsConfig:
    if not isinstance(value, dict):
        raise ConfigError("workcells must be a mapping")
    unknown = sorted(set(value) - _WORKCELL_KEYS)
    if unknown:
        raise ConfigError(f"workcells has unknown keys: {', '.join(unknown)}")
    merged = {**DEFAULTS["workcells"], **value}
    enabled = merged["enabled"]
    if not isinstance(enabled, bool):
        raise ConfigError("workcells.enabled must be boolean")
    maximum_attempts = merged["maximum_attempts"]
    if not isinstance(maximum_attempts, int) or isinstance(maximum_attempts, bool) or not 1 <= maximum_attempts <= 10:
        raise ConfigError("workcells.maximum_attempts must be between 1 and 10")
    tier = merged["default_model_tier"]
    if tier not in _MODEL_TIERS:
        raise ConfigError("workcells.default_model_tier must be a known tier")
    selectors = merged["model_selectors"]
    if not isinstance(selectors, dict) or set(selectors) != _MODEL_TIERS or any(
        not isinstance(item, str) or not item.strip() or len(item) > 128 for item in selectors.values()
    ):
        raise ConfigError("workcells.model_selectors must map every tier to a non-empty selector")
    minima = merged["profile_minimum_tiers"]
    if not isinstance(minima, dict) or set(minima) != {item.value for item in RunProfile} or any(
        item not in _MODEL_TIERS for item in minima.values()
    ):
        raise ConfigError("workcells.profile_minimum_tiers must map every profile to a known tier")
    active = merged["maximum_active_children"]
    mutating = merged["maximum_concurrent_mutating_tasks"]
    shared = merged["allow_shared_workspace_concurrency"]
    if not isinstance(active, int) or isinstance(active, bool) or not 1 <= active <= 4:
        raise ConfigError("workcells.maximum_active_children must be between 1 and 4")
    if not isinstance(shared, bool) or not isinstance(mutating, int) or isinstance(mutating, bool) or not 1 <= mutating <= active:
        raise ConfigError("workcells concurrency configuration is invalid")
    if not shared and mutating != 1:
        raise ConfigError("workcells concurrency requires allow_shared_workspace_concurrency")
    limits = ("brief_size_limit", "context_manifest_size_limit", "result_size_limit")
    for name in limits:
        limit = merged[name]
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1_024 <= limit <= 1_048_576:
            raise ConfigError(f"workcells.{name} must be between 1024 and 1048576")
    timeout = merged["claim_timeout_seconds"]
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 60 <= timeout <= 86_400:
        raise ConfigError("workcells.claim_timeout_seconds must be between 60 and 86400")
    recovery = merged["recovery_behavior"]
    if recovery != "interrupt":
        raise ConfigError("workcells.recovery_behavior must be interrupt")
    return WorkcellsConfig(
        enabled, maximum_attempts, str(tier),
        {RunProfile(key): str(item) for key, item in minima.items()},
        {str(key): str(item) for key, item in selectors.items()}, active, shared, mutating,
        int(merged["brief_size_limit"]), int(merged["context_manifest_size_limit"]),
        int(merged["result_size_limit"]), timeout, recovery,
    )


def config_fingerprint(config: HardproofConfig) -> str:
    """Hash the effective, validated configuration for durable policy evidence."""
    payload = {
        "schema_version": config.schema_version,
        "default_profile": config.default_profile.value,
        "artifact_directory": config.artifact_directory.as_posix(),
        "verification_checks": [
            {
                "name": item.name, "command": item.command, "required": item.required,
                "timeout_seconds": item.timeout_seconds,
            }
            for item in config.verification_checks
        ],
        "stage_policy_overrides": config.stage_policy_overrides,
        "terminal_read_only_prefixes": config.terminal_read_only_prefixes,
        "terminal_blocked_patterns": config.terminal_blocked_patterns,
        "output_redaction_patterns": config.output_redaction_patterns,
        "maximum_stored_output_size": config.maximum_stored_output_size,
        "mutating_tools": config.mutating_tools,
        "policy": {
            "state_failure_mode": config.policy.state_failure_mode,
            "rules": [
                {
                    "key": rule.key, "effect": rule.effect, "tools": rule.tools,
                    "rationale": rule.rationale, "command_regex": rule.command_regex,
                    "path_glob": rule.path_glob,
                    "profiles": [item.value for item in rule.profiles],
                    "stages": [item.value for item in rule.stages],
                }
                for rule in config.policy.rules
            ],
            "packs": config.policy.packs,
            "stage_graph": config.policy.stage_graph,
        },
        "workcells": {
            "enabled": config.workcells.enabled,
            "maximum_attempts": config.workcells.maximum_attempts,
            "default_model_tier": config.workcells.default_model_tier,
            "profile_minimum_tiers": {key.value: value for key, value in config.workcells.profile_minimum_tiers.items()},
            "model_selectors": config.workcells.model_selectors,
            "maximum_active_children": config.workcells.maximum_active_children,
            "allow_shared_workspace_concurrency": config.workcells.allow_shared_workspace_concurrency,
            "maximum_concurrent_mutating_tasks": config.workcells.maximum_concurrent_mutating_tasks,
            "brief_size_limit": config.workcells.brief_size_limit,
            "context_manifest_size_limit": config.workcells.context_manifest_size_limit,
            "result_size_limit": config.workcells.result_size_limit,
            "claim_timeout_seconds": config.workcells.claim_timeout_seconds,
            "recovery_behavior": config.workcells.recovery_behavior,
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
    source_schema = supplied.get("schema_version", CONFIG_SCHEMA_VERSION)
    if not isinstance(source_schema, int) or isinstance(source_schema, bool) or source_schema not in {1, 2, 3}:
        raise ConfigError(f"unsupported config schema_version: {source_schema}")
    if source_schema == 1 and "policy" in supplied:
        raise ConfigError("config schema_version 1 does not support policy; use schema_version 2")
    if source_schema < 3 and "workcells" in supplied:
        raise ConfigError("config schema_version 1 or 2 does not support workcells; use schema_version 3")
    unknown = sorted(set(supplied) - ALLOWED_KEYS)
    if unknown:
        raise ConfigError(f"unknown config keys: {', '.join(unknown)}")
    values = {**DEFAULTS, **supplied}
    values["schema_version"] = CONFIG_SCHEMA_VERSION
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
        schema_version=CONFIG_SCHEMA_VERSION,
        source_schema_version=source_schema,
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
        policy=_policy(values["policy"], profile),
        workcells=_workcells(values["workcells"]),
    )

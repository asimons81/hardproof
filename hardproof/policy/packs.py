"""Versioned, data-only language policy packs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hardproof.policy.terminal import TerminalCategory, TerminalSegment

PACK_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class PolicyPack:
    key: str
    indicators: tuple[str, ...]
    commands: dict[tuple[str, ...], tuple[TerminalCategory, str]]
    checks: tuple[str, ...]


PACKS = {
    "python": PolicyPack("python", ("pyproject.toml", "setup.py", "requirements.txt"), {
        ("pytest",): (TerminalCategory.TEST, "test"), ("ruff",): (TerminalCategory.READ_ONLY, "lint"),
        ("mypy",): (TerminalCategory.READ_ONLY, "typecheck"), ("pyright",): (TerminalCategory.READ_ONLY, "typecheck"),
        ("tox",): (TerminalCategory.TEST, "test"), ("nox",): (TerminalCategory.TEST, "test"),
        ("twine", "upload"): (TerminalCategory.DEPLOYMENT, "publish"),
    }, ("python -m pytest", "ruff check .", "mypy --strict")),
    "node": PolicyPack("node", ("package.json", "pnpm-lock.yaml", "yarn.lock"), {
        ("npm", "test"): (TerminalCategory.TEST, "test"), ("pnpm", "test"): (TerminalCategory.TEST, "test"),
        ("yarn", "test"): (TerminalCategory.TEST, "test"), ("vitest",): (TerminalCategory.TEST, "test"),
        ("jest",): (TerminalCategory.TEST, "test"), ("eslint",): (TerminalCategory.READ_ONLY, "lint"),
        ("tsc",): (TerminalCategory.BUILD, "typecheck"), ("npm", "publish"): (TerminalCategory.DEPLOYMENT, "publish"),
        ("npx", "vitest"): (TerminalCategory.TEST, "test"), ("npx", "jest"): (TerminalCategory.TEST, "test"),
        ("npx", "eslint"): (TerminalCategory.READ_ONLY, "lint"), ("npx", "tsc"): (TerminalCategory.BUILD, "typecheck"),
    }, ("npm test", "npm run lint", "npx tsc --noEmit")),
    "rust": PolicyPack("rust", ("Cargo.toml", "Cargo.lock"), {
        ("cargo", "test"): (TerminalCategory.TEST, "test"), ("cargo", "check"): (TerminalCategory.READ_ONLY, "check"),
        ("cargo", "clippy"): (TerminalCategory.READ_ONLY, "lint"), ("cargo", "fmt"): (TerminalCategory.BUILD, "format"),
        ("cargo", "build"): (TerminalCategory.BUILD, "build"), ("cargo", "publish"): (TerminalCategory.DEPLOYMENT, "publish"),
    }, ("cargo test", "cargo clippy", "cargo fmt --check")),
    "go": PolicyPack("go", ("go.mod", "go.sum"), {
        ("go", "test"): (TerminalCategory.TEST, "test"), ("go", "vet"): (TerminalCategory.READ_ONLY, "lint"),
        ("go", "fmt"): (TerminalCategory.BUILD, "format"), ("go", "build"): (TerminalCategory.BUILD, "build"),
        ("go", "generate"): (TerminalCategory.BUILD, "generate"), ("go", "install"): (TerminalCategory.DEPLOYMENT, "install"),
    }, ("go test ./...", "go vet ./...")),
}


def detect_packs(root: Path) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
    matches = {key: tuple(name for name in pack.indicators if (root / name).exists()) for key, pack in PACKS.items()}
    return tuple(key for key in PACKS if matches[key]), matches


def classify_with_packs(tokens: tuple[str, ...], active: tuple[str, ...]) -> TerminalSegment | None:
    lower = tuple(token.lower() for token in tokens)
    if lower and lower[0].endswith(".exe"):
        lower = (lower[0][:-4],) + lower[1:]
    for key in active:
        pack = PACKS[key]
        for prefix, (category, label) in pack.commands.items():
            if lower[:len(prefix)] == prefix:
                return TerminalSegment(tokens, category, f"pack.{key}.{label}", f"{key} pack {label} rule matched (v{PACK_VERSION}).")
    return None

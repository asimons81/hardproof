"""Bounded, non-executing normalization and classification of terminal input."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


MAX_COMMAND_CHARACTERS = 16_384
MAX_SEGMENTS = 32
MAX_TOKENS = 256
MAX_TOKEN_CHARACTERS = 512
MAX_WRAPPER_DEPTH = 4


class TerminalCategory(StrEnum):
    AMBIGUOUS = "ambiguous"
    IMMUTABLE = "immutable"
    DESTRUCTIVE = "destructive"
    DEPLOYMENT = "deployment"
    DATABASE = "database"
    CREDENTIAL = "credential"
    TEST = "test"
    BUILD = "build"
    READ_ONLY = "read_only"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TerminalSegment:
    tokens: tuple[str, ...]
    category: TerminalCategory
    rule_key: str
    explanation: str


@dataclass(frozen=True, slots=True)
class TerminalClassification:
    segments: tuple[TerminalSegment, ...]
    primary_index: int
    ambiguous: bool = False

    @property
    def primary(self) -> TerminalSegment:
        return self.segments[self.primary_index]


_PRIORITY = {
    TerminalCategory.IMMUTABLE: 100,
    TerminalCategory.AMBIGUOUS: 95,
    TerminalCategory.DESTRUCTIVE: 80,
    TerminalCategory.DEPLOYMENT: 70,
    TerminalCategory.DATABASE: 60,
    TerminalCategory.CREDENTIAL: 55,
    TerminalCategory.UNKNOWN: 30,
    TerminalCategory.BUILD: 20,
    TerminalCategory.TEST: 20,
    TerminalCategory.READ_ONLY: 10,
}


def _ambiguous(reason: str) -> TerminalClassification:
    segment = TerminalSegment((), TerminalCategory.AMBIGUOUS, "terminal.ambiguous", reason)
    return TerminalClassification((segment,), 0, True)


def _tokenize(command: str) -> tuple[tuple[str, ...], ...] | None:
    if not command.strip() or len(command) > MAX_COMMAND_CHARACTERS:
        return None
    segments: list[tuple[str, ...]] = []
    tokens: list[str] = []
    token: list[str] = []
    quote: str | None = None
    escaped = False
    index = 0

    def finish_token() -> bool:
        if token:
            value = "".join(token)
            if len(value) > MAX_TOKEN_CHARACTERS:
                return False
            tokens.append(value)
            token.clear()
        return len(tokens) <= MAX_TOKENS

    def finish_segment() -> bool:
        if not finish_token():
            return False
        if tokens:
            segments.append(tuple(tokens))
            tokens.clear()
        return len(segments) <= MAX_SEGMENTS

    while index < len(command):
        character = command[index]
        if escaped:
            token.append(character)
            escaped = False
        elif quote:
            if character == quote:
                quote = None
            elif character == "`" and quote == '"':
                escaped = True
            elif character == "\\" and quote == '"':
                if index + 1 < len(command) and command[index + 1] in {'"', "\\"}:
                    escaped = True
                else:
                    token.append(character)
            else:
                token.append(character)
        elif character in {"'", '"'}:
            quote = character
        elif character == "`":
            escaped = True
        elif character == "\\":
            if index + 1 < len(command) and (
                command[index + 1].isspace() or command[index + 1] in {'"', "'", "\\", ";", "|", "&"}
            ):
                escaped = True
            else:
                token.append(character)
        elif character.isspace() and character not in {"\r", "\n"}:
            if not finish_token():
                return None
        elif character in {";", "|", "&", "\r", "\n"}:
            if not finish_segment():
                return None
            if index + 1 < len(command) and command[index + 1] == character:
                index += 1
        else:
            token.append(character)
        index += 1
    if quote or escaped or not finish_segment() or not segments:
        return None
    return tuple(segments)


def _unwrap(tokens: tuple[str, ...], depth: int = 0) -> tuple[tuple[str, ...], ...] | None:
    if depth >= MAX_WRAPPER_DEPTH or not tokens:
        return (tokens,)
    lowered = tuple(value.lower() for value in tokens)
    start = 0
    if lowered[0] == "sudo":
        start = 1
        while start < len(tokens) and tokens[start].startswith("-"):
            start += 1
    elif lowered[0] == "env":
        start = 1
        while start < len(tokens) and "=" in tokens[start] and not tokens[start].startswith("="):
            start += 1
    if start:
        return _unwrap(tokens[start:], depth + 1)
    if lowered[0] == "command":
        return _unwrap(tokens[1:], depth + 1)
    wrapper_flags = {
        "cmd": {"/c", "/k"},
        "powershell": {"-command", "-c"},
        "powershell.exe": {"-command", "-c"},
        "pwsh": {"-command", "-c"},
        "bash": {"-c"},
        "sh": {"-c"},
    }
    flags = wrapper_flags.get(lowered[0])
    if flags and len(tokens) >= 3 and lowered[1] in flags:
        inner = " ".join(tokens[2:])
        parsed = _tokenize(inner)
        if parsed is None:
            return None
        expanded: list[tuple[str, ...]] = []
        for segment in parsed:
            child = _unwrap(segment, depth + 1)
            if child is None:
                return None
            expanded.extend(child)
        return tuple(expanded)
    return (tokens,)


def _has_flag(tokens: tuple[str, ...], letter: str) -> bool:
    return any(token.startswith("-") and letter in token.lstrip("-").lower() for token in tokens)


def _segment(tokens: tuple[str, ...]) -> TerminalSegment:
    lower = tuple(token.lower() for token in tokens)
    command = lower[0] if lower else ""
    pair = lower[:2]
    if pair == ("git", "push") and any(
        token in {"-f", "--force", "--force-with-lease"} for token in lower[2:]
    ):
        return TerminalSegment(tokens, TerminalCategory.IMMUTABLE, "terminal.immutable.force_push", "Immutable force-push rule matched.")
    if pair == ("git", "reset") and "--hard" in lower[2:]:
        return TerminalSegment(tokens, TerminalCategory.DESTRUCTIVE, "terminal.destructive.git_reset_hard", "Destructive hard-reset rule matched.")
    if pair == ("git", "clean") and _has_flag(lower[2:], "f"):
        return TerminalSegment(tokens, TerminalCategory.DESTRUCTIVE, "terminal.destructive.git_clean", "Destructive Git-clean rule matched.")
    if pair == ("git", "branch") and "-d" in lower[2:]:
        return TerminalSegment(tokens, TerminalCategory.DESTRUCTIVE, "terminal.destructive.git_branch_delete", "Destructive branch-delete rule matched.")
    if command == "rm" and _has_flag(lower[1:], "r") and _has_flag(lower[1:], "f"):
        return TerminalSegment(tokens, TerminalCategory.DESTRUCTIVE, "terminal.destructive.recursive_delete", "Recursive-delete rule matched.")
    if command in {"remove-item", "del", "rmdir"} and any(
        token in {"-recurse", "/s", "/q"} for token in lower[1:]
    ):
        return TerminalSegment(tokens, TerminalCategory.DESTRUCTIVE, "terminal.destructive.recursive_delete", "Recursive-delete rule matched.")
    if command in {"chmod", "chown", "icacls", "takeown"}:
        return TerminalSegment(tokens, TerminalCategory.DESTRUCTIVE, "terminal.destructive.permissions", "Permission or ownership mutation rule matched.")
    if pair in {("npm", "publish"), ("twine", "upload"), ("docker", "push"), ("vercel", "deploy")}:
        return TerminalSegment(tokens, TerminalCategory.DEPLOYMENT, "terminal.deployment.publish", "Package or image publication rule matched.")
    if command in {"kubectl", "terraform", "pulumi", "helm"} and len(lower) > 1 and lower[1] in {
        "apply", "delete", "destroy", "deploy", "install", "upgrade",
    }:
        return TerminalSegment(tokens, TerminalCategory.DEPLOYMENT, "terminal.deployment.infrastructure", "Infrastructure deployment rule matched.")
    if pair in {("alembic", "upgrade"), ("prisma", "migrate"), ("django-admin", "migrate")} or (
        len(lower) >= 4 and lower[:4] == ("python", "manage.py", "migrate", "--run-syncdb")
    ):
        return TerminalSegment(tokens, TerminalCategory.DATABASE, "terminal.database.migration", "Database migration rule matched.")
    if pair in {("gh", "auth"), ("aws", "configure"), ("gcloud", "auth"), ("az", "login")}:
        return TerminalSegment(tokens, TerminalCategory.CREDENTIAL, "terminal.credential.access", "Credential-oriented command rule matched.")
    if command in {"pytest", "tox", "nox"} or pair in {
        ("python", "-m"), ("npm", "test"), ("cargo", "test"), ("go", "test"),
    }:
        if pair == ("python", "-m") and len(lower) > 2 and lower[2] not in {"pytest", "unittest"}:
            pass
        else:
            return TerminalSegment(tokens, TerminalCategory.TEST, "terminal.read_only.test", "Test-command rule matched.")
    if pair in {("cargo", "build"), ("go", "build"), ("npm", "run"), ("python", "-m")}:
        return TerminalSegment(tokens, TerminalCategory.BUILD, "terminal.read_only.build", "Build-command rule matched.")
    if pair in {("git", "status"), ("git", "diff"), ("git", "log"), ("git", "show")} or command in {
        "ls", "dir", "pwd", "get-childitem",
    }:
        return TerminalSegment(tokens, TerminalCategory.READ_ONLY, "terminal.read_only.inspect", "Read-only inspection rule matched.")
    return TerminalSegment(tokens, TerminalCategory.UNKNOWN, "terminal.unknown", "No known terminal category matched.")


def classify_terminal(command: str) -> TerminalClassification:
    """Return a deterministic classification without executing or expanding input."""
    parsed = _tokenize(command)
    if parsed is None:
        return _ambiguous("Terminal input is empty, malformed, or exceeds normalization bounds.")
    expanded: list[tuple[str, ...]] = []
    for tokens in parsed:
        unwrapped = _unwrap(tokens)
        if unwrapped is None:
            return _ambiguous("Terminal wrapper input is malformed or exceeds normalization bounds.")
        expanded.extend(unwrapped)
    if not expanded or len(expanded) > MAX_SEGMENTS:
        return _ambiguous("Terminal input exceeds segment normalization bounds.")
    segments = tuple(_segment(tokens) for tokens in expanded)
    primary_index = max(
        range(len(segments)), key=lambda index: (_PRIORITY[segments[index].category], -index)
    )
    return TerminalClassification(segments, primary_index)

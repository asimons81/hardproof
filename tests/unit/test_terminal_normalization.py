from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

from hardproof.policy.terminal import TerminalCategory, classify_terminal


@pytest.mark.parametrize(
    ("command", "category", "rule"),
    [
        ("git push origin main --force-with-lease", TerminalCategory.IMMUTABLE, "terminal.immutable.force_push"),
        ("sudo git reset --hard HEAD~1", TerminalCategory.DESTRUCTIVE, "terminal.destructive.git_reset_hard"),
        ("git clean -fdx", TerminalCategory.DESTRUCTIVE, "terminal.destructive.git_clean"),
        ("git branch -D obsolete", TerminalCategory.DESTRUCTIVE, "terminal.destructive.git_branch_delete"),
        ("rm -rf build", TerminalCategory.DESTRUCTIVE, "terminal.destructive.recursive_delete"),
        ("Remove-Item build -Recurse -Force", TerminalCategory.DESTRUCTIVE, "terminal.destructive.recursive_delete"),
        ("chmod -R 777 .", TerminalCategory.DESTRUCTIVE, "terminal.destructive.permissions"),
        ("npm publish", TerminalCategory.DEPLOYMENT, "terminal.deployment.publish"),
        ("kubectl apply -f deploy.yaml", TerminalCategory.DEPLOYMENT, "terminal.deployment.infrastructure"),
        ("alembic upgrade head", TerminalCategory.DATABASE, "terminal.database.migration"),
        ("gh auth token", TerminalCategory.CREDENTIAL, "terminal.credential.access"),
        ("python -m pytest -q", TerminalCategory.TEST, "terminal.read_only.test"),
        ("cargo build --release", TerminalCategory.BUILD, "terminal.read_only.build"),
        ("git status --short", TerminalCategory.READ_ONLY, "terminal.read_only.inspect"),
    ],
)
def test_cross_shell_classification(command: str, category: TerminalCategory, rule: str) -> None:
    result = classify_terminal(command)
    assert result.primary.category is category
    assert result.primary.rule_key == rule
    assert not result.ambiguous


def test_chained_command_uses_highest_safety_precedence() -> None:
    result = classify_terminal("python -m pytest && git push --force origin main")
    assert len(result.segments) == 2
    assert result.primary.rule_key == "terminal.immutable.force_push"
    assert [item.category for item in result.segments] == [
        TerminalCategory.TEST,
        TerminalCategory.IMMUTABLE,
    ]


@pytest.mark.parametrize(
    "command",
    [
        'cmd /c "git clean -fd"',
        'powershell -Command "Remove-Item build -Recurse"',
        'pwsh -c "git push --force origin main"',
        'bash -c "rm -rf build"',
        "env CI=1 command python -m pytest",
    ],
)
def test_common_wrappers_are_unwrapped_deterministically(command: str) -> None:
    first = classify_terminal(command)
    second = classify_terminal(command)
    assert first == second
    assert first.primary.category is not TerminalCategory.UNKNOWN


@pytest.mark.parametrize("command", ["echo 'unterminated", "x" * 20_000, "", "   "])
def test_malformed_or_bounded_input_is_conservatively_ambiguous(command: str) -> None:
    result = classify_terminal(command)
    assert result.ambiguous
    assert result.primary.rule_key == "terminal.ambiguous"
    if command.strip():
        assert command.strip() not in result.primary.explanation


def test_secret_value_is_not_copied_into_explanations() -> None:
    secret = "token-value-that-must-not-be-persisted"
    result = classify_terminal(f"gh auth login --with-token {secret}")
    assert result.primary.category is TerminalCategory.CREDENTIAL
    assert secret not in result.primary.explanation


def test_windows_path_backslashes_are_preserved_in_tokens() -> None:
    result = classify_terminal(r"Remove-Item C:\work\build -Recurse -Force")
    assert result.primary.rule_key == "terminal.destructive.recursive_delete"
    assert result.primary.tokens[1] == r"C:\work\build"


@given(st.text(max_size=1_024))
def test_arbitrary_bounded_text_always_returns_a_valid_classification(command: str) -> None:
    result = classify_terminal(command)
    assert result.segments
    assert 0 <= result.primary_index < len(result.segments)

from __future__ import annotations

from pathlib import Path

import pytest

from hardproof.policy.packs import PACK_VERSION, classify_with_packs, detect_packs
from hardproof.policy.terminal import TerminalCategory


@pytest.mark.parametrize("pack,tokens,category,key", [
    ("python", ("pytest.exe", "-q"), TerminalCategory.TEST, "pack.python.test"),
    ("node", ("npm", "publish"), TerminalCategory.DEPLOYMENT, "pack.node.publish"),
    ("rust", ("cargo", "clippy"), TerminalCategory.READ_ONLY, "pack.rust.lint"),
    ("go", ("go", "generate", "./..."), TerminalCategory.BUILD, "pack.go.generate"),
])
def test_pack_classification(pack: str, tokens: tuple[str, ...], category: TerminalCategory, key: str) -> None:
    result = classify_with_packs(tokens, (pack,))
    assert result is not None
    assert (result.category, result.rule_key) == (category, key)
    assert PACK_VERSION in result.explanation


def test_local_detection_is_ordered_and_does_not_execute(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "go.mod").touch()
    detected, evidence = detect_packs(tmp_path)
    assert detected == ("python", "go")
    assert evidence["python"] == ("pyproject.toml",)

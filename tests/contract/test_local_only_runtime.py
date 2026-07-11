from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "hardproof"
NETWORK_MODULES = frozenset(
    {"aiohttp", "http", "httpx", "requests", "socket", "urllib", "websockets"}
)


def test_runtime_has_no_network_client_imports() -> None:
    violations: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = (alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = (node.module.split(".", 1)[0],)
            else:
                continue
            for module in modules:
                if module in NETWORK_MODULES:
                    violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert violations == []

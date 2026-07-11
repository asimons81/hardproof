"""Build or install a Hardproof wheel in a clean virtual environment and smoke-import it."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path, help="Path to a built hardproof wheel")
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    if not wheel.is_file():
        parser.error(f"wheel not found: {wheel}")
    with tempfile.TemporaryDirectory(prefix="hardproof-smoke-") as temporary:
        environment = Path(temporary) / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", str(wheel)], check=True)
        code = (
            "import importlib.metadata as m; import hardproof; "
            "ep=next(e for e in m.entry_points(group='hermes_agent.plugins') if e.name=='hardproof'); "
            "mod=ep.load(); assert callable(mod.register); assert hardproof.__version__=='0.1.0'"
        )
        subprocess.run([str(python), "-c", code], check=True)
    print(f"PASS clean wheel install: {wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

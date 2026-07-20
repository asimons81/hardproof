from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence

TAIL_LINES = 200


def run_pytest(args: Sequence[str]) -> int:
    """Run pytest and emit only the useful tail of its combined output."""
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines = completed.stdout.splitlines()
    omitted = max(0, len(lines) - TAIL_LINES)
    if omitted:
        print(f"... omitted {omitted} earlier pytest output lines ...")
    print("\n".join(lines[-TAIL_LINES:]))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(run_pytest(sys.argv[1:]))

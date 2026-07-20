from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

TAIL_LINES = 200


def run_pytest(args: Sequence[str]) -> int:
    """Run pytest, persist its output when requested, and emit a useful tail."""
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log_path = os.environ.get("HARDPROOF_PYTEST_LOG")
    if log_path:
        Path(log_path).write_text(completed.stdout, encoding="utf-8")
    lines = completed.stdout.splitlines()
    omitted = max(0, len(lines) - TAIL_LINES)
    if omitted:
        print(f"... omitted {omitted} earlier pytest output lines ...")
    print("\n".join(lines[-TAIL_LINES:]))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(run_pytest(sys.argv[1:]))

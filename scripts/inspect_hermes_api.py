"""Print the installed Hermes public plugin compatibility report."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crucible_agent.compat import inspect_context


def main() -> int:
    try:
        from hermes_cli.plugins import PluginContext
    except ImportError:
        print('{"compatible": false, "error": "hermes-agent is not installed"}')
        return 1

    # Capability inspection needs the public type surface, not a live manager.
    context = object.__new__(PluginContext)
    report = inspect_context(context)
    print(report.to_json())
    return 0 if report.compatible else 1


if __name__ == "__main__":
    raise SystemExit(main())

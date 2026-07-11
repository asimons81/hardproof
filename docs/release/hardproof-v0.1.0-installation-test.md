# Hardproof v0.1.0 Installation Test

## Environment

- OS: Windows 10 (native)
- Python: 3.11
- Hermes Agent: 0.18.2
- Date: 2026-07-11

## Wheel Installation

```bash
pip install dist/hardproof-0.1.0-py3-none-any.whl
```

Result: Package installs successfully.

## Package Import

```python
import hardproof
print(hardproof.__version__)  # 0.1.0
```

Result: Import succeeds, version matches.

## Entry-Point Discovery

```python
import importlib.metadata
eps = importlib.metadata.entry_points(group="hermes_agent.plugins")
# hardproof entry point registered
```

Result: Plugin entry point discovered.

## Plugin Manifest

- plugin.yaml: name=hardproof, version=0.1.0
- Tools: hardproof_run, hardproof_record, hardproof_task, hardproof_transition, hardproof_verify, hardproof_report
- Hooks: pre_llm_call, pre_tool_call, post_tool_call, pre_verify, on_session_start, on_session_finalize, on_session_reset

## Package Data

- migrations/001_initial.sql: included
- templates/completion.md: included
- skills/orchestrate/SKILL.md: included
- All 9 skill files: included

## Clean Environment Test

Installed in a fresh virtual environment with no pre-existing dependencies.
No install errors. Single runtime dependency (PyYAML) resolved.

## Smoke Test

```python
from hardproof.paths import ProjectPaths
from hardproof.config import load_config, DEFAULTS
from hardproof.constants import PLUGIN_KEY
assert PLUGIN_KEY == "hardproof"
assert ".hardproof" in DEFAULTS["artifact_directory"]
```

Result: All assertions pass.

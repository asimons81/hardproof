# First Standard Run

This sanitized transcript records the repeatable end-to-end scenario in `tests/e2e/test_standard_workflow.py`. It was executed on 2026-07-11 against a new temporary Git repository. Generated identifiers and temporary paths are omitted.

## Request

```text
Change value to two
```

## Transcript

```text
REGISTER  6 tools, 9 namespaced skills, slash command, CLI command, and hooks
START     standard -> INTAKE; durable run created
ADVANCE   INTAKE -> DISCOVERY
ARTIFACT  discovery.md: current value is one
ADVANCE   DISCOVERY -> DESIGN
ARTIFACT  design.md: return two
BLOCKED   DESIGN -> PLAN: human design approval missing
APPROVE   design, actor=human, source=cli, reason=reviewed
ADVANCE   DESIGN -> PLAN
ARTIFACT  plan.md: edit code and run the focused test
APPROVE   plan, actor=human, source=cli, reason=reviewed
ADVANCE   PLAN -> IMPLEMENT
TASK      T1 created, source and test changed, acceptance recorded complete
ADVANCE   IMPLEMENT -> REVIEW
REVIEW    independent review artifact and approval event recorded
ADVANCE   REVIEW -> VERIFY
VERIFY    python -m pytest -> exit 0; output and workspace snapshot stored
EDIT      source changed after verification
STALE     prior passing evidence no longer matches the workspace
BLOCKED   VERIFY -> DELIVER: fresh passing verification required
VERIFY    python -m pytest -> exit 0 against the changed workspace
ADVANCE   VERIFY -> DELIVER
REPORT    deterministic Markdown and JSON exports generated
ADVANCE   DELIVER -> LEARN
LEARN     learning artifact recorded
ADVANCE   LEARN -> COMPLETE
RESTART   state reopened from project-local SQLite; run, task, and evidence intact
```

Both real verifier subprocesses ran the temporary project's test and returned explicit exit code zero. The package's local-only contract test also scans every shipped Python module and rejects imports of common network-client modules.

Run the evidence again with:

```bash
python -m pytest tests/e2e/test_standard_workflow.py tests/contract/test_local_only_runtime.py -q
```

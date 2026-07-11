# Contributing to Hardproof

Hardproof welcomes issues, documentation, tests, policy analysis, compatibility reports, and code contributions.

## Before changing code

Open an issue for substantial behavior or public-contract changes. Use an RFC issue for breaking commands, schemas, profile semantics, migrations, extension interfaces, telemetry proposals, or changes to immutable safety rules. Record accepted architecture decisions in `docs/adr/`.

Preserve the clean-room boundary in `INSPIRATION.md`. Do not copy source, skill prose, prompts, fixtures, diagrams, templates, layout, or documentation wording from other workflow projects.

## Development

Use Python 3.11 or newer. Install development dependencies with `python -m pip install -e ".[dev]"`, then run:

```bash
python -m pytest
python -m ruff check hardproof tests scripts
python -m mypy hardproof
python -m build
python -m twine check dist/*
```

Add tests for both allowed and refusal paths. Never weaken a gate to make a test pass. Keep commits coherent, secret-free, and buildable. Conventional subjects are encouraged but not required for external contributors. Pull requests are squash-merged by default.

## Developer Certificate of Origin

Hardproof uses the Developer Certificate of Origin 1.1 instead of a CLA. Sign each commit with:

```text
Signed-off-by: Your Name <your.email@example.com>
```

Use `git commit -s`. The sign-off certifies that you have the right to submit the contribution under this project's license.

## Pull requests

Describe behavior, risk, tests, migrations, documentation, and compatibility impact. Link the issue or ADR. Do not include credentials, private transcripts, generated caches, local databases, or unredacted verification output.

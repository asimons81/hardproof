# tests/ AGENTS.md — Testing Instructions

## Test Structure

```
tests/
├── unit/                   # Unit tests — primary suite, fast
├── integration/            # Integration tests — real DB, Git, filesystem
├── contract/               # Contract tests — package data, open source, rename, skills, docs surface
└── e2e/                    # End-to-end tests — full workflow through plugin
```

## Running Tests

Run focused tests first, then the full suite:

```bash
python -m pytest tests/path/to/test_file.py -q    # Focused
python -m pytest                                   # Full suite
```

## Rules

1. **Reproduce before repairing** — demonstrate the bug with a failing test before fixing production code.
2. **Test allowed and refusal paths** — every permission or gate needs both the happy path and the blocked path. A change that adds an approval must also test what happens when approval is missing.
3. **Test security boundaries** — waivers cannot bypass immutable rules, tools cannot create approvals or waivers, tools cannot modify authority records, etc.
4. **Add migration tests for persisted-state changes** — test fresh database creation, upgrades from v1, v2 dry-run, actual migration, rollback (where supported), idempotence (running migrate twice).
5. **Use `tmp_path` fixtures** — never write to the real project directory or user home.
6. **Test Windows path behavior where relevant** — `.exe` pack detection, path normalization, etc.
7. **Avoid brittle count snapshots** — do not assert exact test counts, model enumeration lengths, or file counts.
8. **Preserve real integration coverage** — use real SQLite (not mocks), real temp directories, real `subprocess.run` where practical. Mocks hide integration bugs.
9. **Avoid change-detector tests** — test behavior contracts, not frozen values. A test that fails whenever a config version or model enum changes is a liability.
10. **Do not weaken a gate to make a test pass** — if gate logic blocks a test, the test or the gate logic needs a design review, not a quick bypass.

## Specific Fixture Patterns

- **Migration fixtures:** Use `tests/integration/` for migration workflows with real SQLite databases at known schema versions.
- **Command fixtures:** Create temporary project roots with `tmp_path`, initialize `.hardproof/` state, and exercise commands through `CommandService`.
- **Security regression tests:** Each authority boundary (approval creation, waiver creation, immutable rule override) should have a dedicated test that proves the model cannot bypass it via tool handlers.

## Cross-Platform Concerns

- CI runs tests on ubuntu-latest (Python 3.11, 3.12), macos-latest (Python 3.11), and windows-latest (Python 3.11).
- Tests that interact with the filesystem must use `pathlib.Path` and avoid hardcoded POSIX-only paths.
- Temporary directories must use `tmp_path` from pytest (cross-platform).

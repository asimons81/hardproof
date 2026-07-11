# Hardproof Independent Release-Readiness Audit

**Auditor**: Hermes (default profile)  
**Date**: 2026-07-11  
**Scope**: Full repository inspection, both Hardproof branches  
**Authority**: Repair P0 and P1 findings; do not publish, push, tag, or reserve names  

---

## Decision

**GO FOR FINAL SANITY CHECK**

All required conditions are met. Zero open P0 findings. All P1 findings repaired. Both branches have clean working trees, passing tests, clean lint/mypy/build/audit gates.

---

## Audit 1: Real Git History

### Branch State (Verified)

| Branch | Commit | Status |
|--------|--------|--------|
| `codex/v0.1.0` | `4cf302f` | Untouched. Original Crucible v0.1.0 release boundary. |
| `codex/v0.2.0` | `aea355b` | **REPAIRED** (was at `ab98c73`). Now at original Gatehouse boundary. |
| `release/hardproof-v0.1.0` | `4a55097` | Release-ready with all repair commits. |
| `chore/hardproof-rename` | `30287f7` | Development branch with all repair commits. |

### Ancestry

```
codex/v0.1.0                          codex/v0.2.0
    |                                      |
    | 4cf302f (Crucible v0.1.0)            | aea355b (Gatehouse boundary)
    |______________________________________|
    |               |
    |               ├── release/hardproof-v0.1.0 (197276d → 4a55097)
    |               |    19ad9d9  rename
    |               |    50246c4  release docs
    |               |    197276d  README rewrite
    |               |    fa502ca  migrate-state (audit repair)
    |               |    1c562f3  doc fixes (audit repair)
    |               |    4a55097  mypy fixes (audit repair)
    |               |
    |               └── chore/hardproof-rename (aea355b → 30287f7)
    |                    ab98c73  rename manifest
    |                    86f943c  rename code
    |                    3a3c3bd  release artifacts
    |                    07df576  README rewrite
    |                    e1bf6f7  migrate bugfix (audit repair)
    |                    2b7f45c  auto-create fix (audit repair)
    |                    30287f7  mypy fixes (audit repair)
```

### Merge Bases

| Pair | Merge Base | Verified |
|------|-----------|----------|
| `codex/v0.1.0` ↔ `release/hardproof-v0.1.0` | `4cf302f` | Yes |
| `codex/v0.2.0` ↔ `chore/hardproof-rename` | `aea355b` | Yes (after repair) |
| `release/...` ↔ `chore/...` | `4cf302f` | Yes |

### Discoveries

- **P1 (REPAIRED)**: `codex/v0.2.0` had been moved from `aea355b` to `ab98c73`, contaminating it with rename commits. Reset to `aea355b`.
- No tags, no remotes, no stashes, clean worktrees on both branches.
- No Git remotes configured. No publication has occurred.

---

## Audit 2: Diff Comparison

### `codex/v0.1.0..release/hardproof-v0.1.0` (149 files)

Limited to:
- Brand identity (name, description, slug)
- Package and plugin identity (hardproof import, entry points)
- Command identity (/hardproof, hermes hardproof)
- Configuration and state paths (.hardproof/)
- State migration (Crucible → Hardproof)
- Documentation (README, CHANGELOG, release docs)
- Security and release hardening
- Packaging
- CI and release preparation
- Defect fixes necessary for public alpha

**No Gatehouse (v0.2.0) features leaked into the release branch.** Verified: no `authority.py`, `risks.py`, `waivers.py`, `terminal.py`, or `trace.py` modules exist on the release branch.

### `codex/v0.2.0..chore/hardproof-rename` (172 files)

Additional content beyond the v0.1.0 rename:
- Gatehouse policy system (terminal classification, trace contracts, risk assessment, waivers)
- Rename-specific regression tests (`test_hardproof_rename.py`, 268 lines)
- Rename ADR and rebrand documentation

### `release/hardproof-v0.1.0..chore/hardproof-rename` (49 files)

The development-only delta: 3743 insertions of Gatehouse v0.2.0 features. Correctly absent from the release branch.

---

## Audit 3: Identity Consistency

### Release Branch Scan: CLEAN

- Zero unexplained "Crucible", "crucible_agent", "crucible-agent", ".crucible", or "hermes crucible" references found outside approved historical contexts.
- Python source, imports, package metadata, plugin manifests, entry points, command registration, tool schemas, state paths, configuration, environment variables, database migration code all use `hardproof` only.
- Old-name references retained only in: ADR 0007 (rename), `docs/codex/GOAL.md` (historical), `CHANGELOG.md` (historical), `INSPIRATION.md` (provenance), release documents (clean-room discussion), and `docs/release/` (discussion of pre-rename state).

### Development Branch Scan: CLEAN

Same pattern. All old-brand references confined to approved historical contexts.

---

## Audit 4: Hermes Integration

### Verified

| Check | Status |
|-------|--------|
| `hardproof` entry point resolves | PASS |
| Root plugin wrapper (`hardproof.plugin:register`) resolves | PASS |
| Plugin manifest (`plugin.yaml`) valid | PASS |
| Plugin remains opt-in | PASS |
| `/hardproof` slash command registers via `ctx.register_command` | PASS |
| `hermes hardproof` CLI registers via `ctx.register_cli_command` | PASS |
| Plugin skills register under correct namespace | PASS |
| Six-tool public surface intact (run, record, task, transition, verify, report) | PASS |
| Uses only public Hermes APIs (`register_tool`, `register_hook`, `register_skill`, `register_command`, `register_cli_command`, `dispatch_tool`, `profile_name`) | PASS |
| No use of `ctx._cli_ref` | PASS |
| No Hermes-core modification | PASS |
| No monkey-patching | PASS |
| No private API dependency | PASS |

---

## Audit 5: State Migration

### Verified Scenarios

| Scenario | Result |
|----------|--------|
| Neither `.crucible/` nor `.hardproof/` exists | Graceful: "Nothing to migrate" |
| Only `.crucible/` exists with valid DB | Migration succeeds, backup created, report written |
| Only `.hardproof/` exists | Graceful: "Already exists, nothing to migrate" |
| Both directories exist, `.hardproof` is auto-created skeleton | **FIXED**: Auto-detects skeleton, removes it, migration proceeds |
| Both directories exist with real state | Graceful: "Resolve manually" |
| Valid old database | Integrity check passes, migration proceeds |
| Backup already exists | Graceful: "Remove or rename backup" |

### Safety Properties

- No automatic deletion of source directory
- No silent merge of state stores
- No destination overwrite without explicit detection
- Backup created before any modification
- Database integrity validated before and after
- Conflict cases reported clearly
- No path traversal
- No data loss paths identified

### Repairs Applied

- **P1 (REPAIRED)**: `migrate-state` command was missing from `release/hardproof-v0.1.0`. Full implementation ported from dev branch with corrected source path (`old_dir = project / ".crucible"`).
- **P1 (REPAIRED)**: Dev branch had `old_dir = project / ".hardproof"` (wrong — should be `.crucible`). Fixed on both branches.
- **P1 (REPAIRED)**: Migration blocked by `CommandService.__init__` auto-creating `.hardproof/`. Added skeleton-detection logic to safely remove auto-created directories before migration.

---

## Audit 6: Policy and Security Invariants

### Gatehouse Features (Dev Branch Only)

All gated correctly — none exist on the release branch:
- Explainable policy traces
- Scoped human waivers
- Deterministic risk suggestions
- Terminal command classification

### Shared v0.1.0 Invariants (Both Branches)

| Invariant | Verified |
|-----------|----------|
| Human-only approvals (design, plan, completion) | PASS |
| Human-only waivers (stage-gate) | PASS |
| Protected namespaces not waivable | PASS |
| Deterministic policy explanation | PASS |
| Secret-safe policy output | PASS |
| Advisory-only risk suggestions (dev branch) | PASS |
| Attributed human risk overrides | PASS |
| Task-risk integrity | PASS |
| Run-profile integrity | PASS |
| Evidence freshness | PASS |
| Workspace snapshot binding | PASS |
| Protected completion gates | PASS |
| State-machine monotonicity | PASS |
| Model inability to create human authority records | PASS |

Focused tests verified: approvals, waivers, policy explanations, risk suggestions, state transitions, evidence freshness, verification, redaction, database integrity, migration, path safety.

---

## Audit 7: Tests and Quality Gates

### Release Branch (`release/hardproof-v0.1.0`)

| Gate | Result |
|------|--------|
| pytest | **217 passed** (0 failed, 0 skipped) |
| ruff check | All checks passed |
| mypy --strict (source) | Success: no issues found in 44 source files |
| mypy --strict (tests) | 29 pre-existing cosmetic errors (P2) |
| python -m build | Wheel + sdist built successfully |
| twine check | PASSED (both artifacts) |
| pip-audit | No vulnerabilities in direct dependencies |

Platform: Windows 10, Python 3.11.9

### Development Branch (`chore/hardproof-rename`)

| Gate | Result |
|------|--------|
| pytest | **334 passed** (0 failed, 0 skipped) |
| ruff check | All checks passed |
| mypy --strict (source) | Success: no issues found in 50 source files |
| mypy --strict (tests) | 29 pre-existing cosmetic errors (P2) |
| python -m build | Wheel + sdist built successfully |
| twine check | PASSED (both artifacts) |

Platform: Windows 10, Python 3.11.9

---

## Audit 8: Clean Installation and Packaging

### Release Branch

| Check | Result |
|-------|--------|
| Wheel install in clean venv | PASS |
| Sdist install in clean venv | PASS |
| `import hardproof` | PASS |
| `import crucible_agent` from shipped artifacts | Correctly fails (module not found) |
| Hermes plugin entry point resolves | PASS |
| Plugin manifest ships | PASS |
| Skills ship (9 SKILL.md files) | PASS |
| Templates ship (5 .md files) | PASS |
| SQL migrations ship (001_initial.sql) | PASS |
| py.typed marker ships | PASS |
| No private/local paths in metadata | PASS |
| Uninstall removes package, preserves project state | PASS |
| No unexpected network activity during install | PASS |

---

## Audit 9: Public Documentation Accuracy

### README.md

- Correctly identifies HARDPROOF as the product
- Correct tagline: "Software has to earn done."
- Alpha status clearly declared
- v0.1.0 and v0.2.0 status accurately described
- Installation instructions correct (GitHub, pending PyPI)
- First-run examples use `/hardproof` and `hermes hardproof`
- Profile descriptions accurate
- Architecture, security, privacy, roadmap, contributing, inspiration, license, affiliation all accurate
- No v0.2.0 features presented as shipped
- Pending PyPI publication correctly noted

### Other Documentation

- CHANGELOG, ROADMAP, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, GOVERNANCE, SUPPORT, INSPIRATION all present and correct
- LICENSE (Apache-2.0) and NOTICE present
- Release documentation directory complete

### Documentation Repairs

- **P1 (REPAIRED)**: `docs/codex/STATUS.md` referenced old branch `codex/v0.1.0` — updated to `release/hardproof-v0.1.0`
- **P1 (REPAIRED)**: `docs/codex/GOAL.md` referenced non-existent `hardproof_codex_plan_and_roadmap.md` — corrected to `ROADMAP.md`

---

## Audit 10: Open-Source Repository Readiness

All expected files present:

- LICENSE, NOTICE, README.md, CHANGELOG.md, ROADMAP.md
- CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, GOVERNANCE.md, SUPPORT.md, INSPIRATION.md
- .github/CODEOWNERS, .github/ISSUE_TEMPLATE/ (bug.yml, feature.yml, config.yml)
- .github/pull_request_template.md, .github/dependabot.yml
- .github/workflows/ (ci.yml, codeql.yml, scorecard.yml, release.yml)

Workflow permissions verified:
- Release workflow uses `environment: pypi` with trusted publishing
- No static PyPI tokens in workflows
- SBOM and checksum generation configured
- Dependabot configured for weekly updates
- CodeQL and Scorecard configurations valid
- Minimal workflow permissions (contents: read, id-token: write for trusted publishing)

---

## Audit 11: Complete History and Privacy Scan

### Methods Used

- Git log grep for API key patterns, tokens, passwords, credentials
- File tree scan for local paths, usernames, private emails
- `.env` file detection

### Findings

| Category | Result |
|----------|--------|
| API keys (sk-...) | CLEAN |
| GitHub tokens | CLEAN |
| AWS keys | CLEAN |
| Private paths (C:\Users\) | CLEAN (only synthetic test value `C:\Users\person\...`) |
| Explicit passwords | CLEAN |
| Bearer tokens | CLEAN |
| .env files committed | CLEAN |
| Private emails | CLEAN (only public maintainer email in documented locations) |

All `asimo` references are legitimate: GitHub username in CODEOWNERS, issue templates, README badges, and documented maintainer email. No real secrets found.

---

## Audit 12: PyPI Availability

- PyPI simple API: 404 (package not reserved)
- PyPI project page: Cloudflare challenge (anti-bot), but `/simple/` endpoint is authoritative
- **`hardproof` is available on PyPI as of audit time**
- Must be re-checked immediately before publication (availability is time-sensitive)

---

## Repairs Applied

| ID | Finding | Classification | Branch(es) | Commit |
|----|---------|---------------|------------|--------|
| R1 | `codex/v0.2.0` contaminated with rename commits | P1 | repo | (branch reset, no commit) |
| R2 | `migrate-state` missing from release branch | P1 | release | `fa502ca` |
| R2a | `migrate-state` used wrong source path | P1 | dev | `e1bf6f7` |
| R2b | `migrate-state` blocked by auto-created `.hardproof/` | P1 | both | `fa502ca`, `2b7f45c` |
| R3 | mypy test overrides needed for clean source check | P1 | both | `4a55097`, `30287f7` |
| R4 | STATUS.md referenced wrong branch | P1 | release | `1c562f3` |
| R5 | GOAL.md referenced non-existent file | P1 | release | `1c562f3` |

---

## Remaining Findings

### P2 (Acceptable Alpha Limitations)

1. **Test file mypy coverage**: 29 cosmetic type errors remain in test files (var-annotated, type-arg, return-value). Source code passes strict mypy with zero errors. These are pre-existing and do not affect correctness.
2. **`__pycache__` directories**: Stale `.pyc` files from dev branch checkouts exist on disk. Tracked by `.gitignore`, not committed. Harmless.
3. **Coverage statistics**: The reported 91.55% overall / 99.21% critical-module coverage could not be independently verified. The claim was removed from STATUS.md.
4. **pip-audit on system packages**: Several system-level packages in the development venv (pydantic-settings, starlette, python-multipart) have known CVEs. These are NOT Hardproof dependencies. Hardproof's only runtime dependency (PyYAML) has no known vulnerabilities.
5. **Stale build artifacts**: The `test_built_wheel_contains_required_package_data` test can fail if `dist/` contains a previous branch's build. Requires `rm -rf dist/` before running full suite, or rebuilding.

### P3 (Polish / Future Improvement)

1. Git identity integration for more granular actor attribution
2. WSL path testing coverage
3. Symlink/junction edge case coverage on Windows
4. Migration rollback documentation
5. Automated coverage verification in CI
6. Hermes plugin discovery smoke test automation

---

## Final State

### Release Artifacts

- **Release branch**: `release/hardproof-v0.1.0`
- **Release commit**: `4a55097`
- **Version**: 0.1.0
- **Wheel**: `dist/hardproof-0.1.0-py3-none-any.whl`
- **Sdist**: `dist/hardproof-0.1.0.tar.gz`
- **Tests**: 217 passing
- **Source mypy**: Clean

### Development Artifacts

- **Development branch**: `chore/hardproof-rename`
- **Development commit**: `30287f7`
- **Version**: 0.2.0
- **Tests**: 334 passing

### Original Branches (Preserved)

- `codex/v0.1.0`: `4cf302f` (untouched)
- `codex/v0.2.0`: `aea355b` (repaired to original)

### Publication Session Requirements

The final publication session must:
1. Verify `hardproof` is still available on PyPI
2. Create the `asimons81/hardproof` GitHub repository
3. Push `release/hardproof-v0.1.0` to the remote
4. Tag `v0.1.0` at commit `4a55097`
5. Publish to PyPI via trusted publishing
6. Update STATUS.md and docs/codex/STATUS.md post-publication
7. Do NOT publish `chore/hardproof-rename` (v0.2.0) — it is not ready for release

---

## Decision

**GO FOR FINAL SANITY CHECK**

The release branch passes all required gates. All P0 and P1 findings have been repaired. The repository is internally consistent, the rename is complete, state migration works, identity is clean, tests pass, quality gates pass, and no secrets are present.

The final sanity check should verify PyPI availability and confirm GitHub repository readiness before tagging and publishing.

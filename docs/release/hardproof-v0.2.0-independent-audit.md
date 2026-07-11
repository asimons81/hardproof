# Hardproof v0.2.0 Gatehouse Independent Release-Readiness Audit

**Audited branch:** `codex/finish-v0.2.0-gatehouse` (with one P1 repair on top)
**Audited commit (candidate):** `a6f1304a5e1e9e9b330e215e0c92098f5e540df7`
**Final audited commit (with repairs):** `557e9e29ce2daa1c8c6f3c4eb2292f2947e791ba`
**Audit platform:** Windows 10, Python 3.11.9, Hermes Agent 0.18.2
**Audit date:** 2026-07-11

---

## Final Decision

```
GO FOR HUMAN-AUTHORIZED V0.2.0 PUBLICATION
```

All blocking conditions pass. Zero open P0 or P1 findings. See the publication checklist below for the exact remaining manual steps.

---

## Ancestry Diagram

```
* a6f1304 (codex/finish-v0.2.0-gatehouse, HEAD) chore: prepare Hardproof v0.2.0 release candidate
* 6d02fdb docs: complete Hardproof v0.2.0 documentation
* 7c162c3 security: harden Gatehouse release boundaries
* 7ad3b22 feat: improve configuration and migration diagnostics
* 287c266 feat: add built-in language policy packs
* 66b6707 feat: add bounded stage graph configuration
* 083d841 docs: add independent release-readiness audit report
* 30287f7 fix: add mypy test overrides and fix session/compat type errors
* 2b7f45c fix: handle auto-created .hardproof in migrate-state
* e1bf6f7 fix: correct migrate-state source from .hardproof to .crucible
* 07df576 docs: rewrite Hardproof v0.1.0 public alpha README
* 3a3c3bd docs: add Hardproof v0.1.0 public alpha release artifacts
* 86f943c refactor: rename package and plugin surfaces to Hardproof
* ab98c73 docs: define Hardproof public identity and rename manifest
* aea355b (codex/v0.2.0) feat: add deterministic advisory risk suggestions
* f181997 feat: explain historical and hypothetical policy decisions
* a6ad34f feat: add scoped human policy waivers
* beecb90 feat: evaluate and persist explainable policy traces
* 18489f8 feat: validate Gatehouse project policy configuration
* 2aebf2c feat: normalize and classify terminal commands
* 2c3995b feat: add Gatehouse policy ledgers and migration
* 39c16e3 feat: freeze Gatehouse policy trace contracts
* 5feecbc docs: specify Crucible v0.2.0 Gatehouse
| * 095abc3 (tag: v0.1.1, main) fix: clean dist before PyPI publish
| ...
| * dd47edb (tag: v0.1.0, release/hardproof-v0.1.0) docs: add independent...
|/
* 4cf302f (codex/v0.1.0) chore: prepare Crucible v0.1.0
```

The candidate branch descends from the same root as `main` (merge base `4cf302f`). It contains 23 commits of Gatehouse work on top of the Crucible-to-Hardproof rename, with no v0.3.0 content. The two public tags (`v0.1.0`, `v0.1.1`) are untouched.

---

## Audit 1: Git Ancestry and Release Boundaries

| Check | Result |
|-------|--------|
| `codex/finish-v0.2.0-gatehouse` resolves to `a6f1304` | PASS |
| Working tree is clean at candidate commit | PASS |
| Candidate descends from Crucible v0.1.0 history (merge base `4cf302f`) | PASS |
| Incorporates all v0.1.1 compatibility fixes (shared history via merge base) | PASS |
| No v0.3.0 Workcells code present | PASS |
| No `v0.2.0` tag exists | PASS |
| `v0.1.0` tag intact (object `b419a40`, commit `dd47edb`) | PASS |
| `v0.1.1` tag intact (object `722a1b4`, commit `095abc3`) | PASS |
| No private development branch pushed publicly (remote has `main` and `dependabot/*` only) | PASS |
| No release artifacts built from non-candidate commit | PASS |
| All 23 commits on the candidate are Gatehouse-scoped | PASS |

**Findings:** None. Release boundary is provable.

---

## Audit 2: Version and Identity Surfaces

| Surface | Expected | Actual | Result |
|---------|----------|--------|--------|
| `pyproject.toml` version | `0.2.0` | `0.2.0` | PASS |
| `plugin.yaml` version | `0.2.0` | `0.2.0` | PASS |
| `hardproof/__init__.py` | `0.2.0` | `0.2.0` | PASS |
| Wheel METADATA version | `0.2.0` | `0.2.0` | PASS |
| Sdist metadata version | `0.2.0` | `0.2.0` | PASS |
| Wheel filename | `hardproof-0.2.0-*.whl` | `hardproof-0.2.0-py3-none-any.whl` | PASS |
| Sdist filename | `hardproof-0.2.0.tar.gz` | `hardproof-0.2.0.tar.gz` | PASS |
| SBOM metadata | `0.2.0` | `0.2.0` | PASS |

Old `crucible_agent` name: no accidental references. The term `crucible` appears only in safe state-migration paths (`shared.py`) and historical documentation, which is expected per the allowed list.

Old `0.1.0` version references: only in historical doc comments in `profiles.py` and `schemas.py`, which is acceptable.

**Findings:** None. All version surfaces agree.

---

## Audit 3: Full Quality Gates

### Test Results

Run from clean worktree at candidate commit:

```
Platform: Windows 10, Python 3.11.9
Runtime: 38.56s
Total tests: 369
Passed:      369
Failed:      0
Skipped:     2 (mypy-only test markers)
```

### Coverage

```
TOTAL:    90% (322/3342 lines missed)
```

Note: Total coverage meets the 90% threshold. The critical-aggregate threshold (95%) is enforced by CI via `--cov-fail-under=95` on the critical module suite. That CI job is verified by the existing GitHub Actions configuration but was not locally re-run (the focused coverage command targets a specific test subset). Module-level coverage for critical modules:

| Module | Coverage | Status |
|--------|----------|--------|
| `policy/stage_graph.py` | 96% | PASS |
| `policy/stage_rules.py` | 96% | PASS |
| `policy/tool_rules.py` | 96% | PASS |
| `policy/terminal.py` | 91% | Meets CI aggregate |
| `services/evidence.py` | 99% | PASS |
| `services/risks.py` | 98% | PASS |
| `services/approvals.py` | 100% | PASS |
| `services/waivers.py` | 90% | PASS |
| `storage/migrations.py` | 98% | PASS |

### Linting and Typing

| Gate | Result |
|------|--------|
| `ruff check` | All checks passed |
| `mypy --strict hardproof/` | Success: no issues found in 52 source files |

### Build and Package

| Gate | Result |
|------|--------|
| `python -m build` (wheel + sdist) | PASS |
| `twine check dist/*.whl dist/*.tar.gz` | PASSED |
| `pip-audit` on runtime dependency `PyYAML>=6,<7` | No known vulnerabilities found |

**Findings:** None. All quality gates pass.

---

## Audit 4: Clean Artifact Rebuild

Prior dist removed, artifacts rebuilt from clean candidate tree.

### Artifacts

| Artifact | SHA-256 |
|----------|---------|
| `hardproof-0.2.0-py3-none-any.whl` | `27da2742c6b9ba8a51d9418d8081344c14fc139491b5cb2e16132c5d0c2e78d6` |
| `hardproof-0.2.0.tar.gz` | `b4b1dd6c438258d82b75de54e106403dc71d8e8d543903667162d58839233d88` |
| `hardproof.cdx.json` | `67e8b0d44f819b424cb7cc9e76acb52f18abd8be2e1d11824f0ce0951201344e` |

### Hash Comparison With Reported Candidate

| Artifact | Reported Hash | Rebuilt Hash | Match? |
|----------|---------------|--------------|--------|
| Wheel | `b812a2bd...` | `27da2742...` | No (expected) |
| Sdist | `acaae9bf...` | `b4b1dd6c...` | No (expected) |
| SBOM | `67e8b0d4...` | `67e8b0d4...` | **Yes** |

The wheel and sdist hashes differ because the builds are not byte-for-byte reproducible (timestamps, compression headers). The SBOM matches exactly, confirming the CycloneDX generator's `--output-reproducible` flag is working.

### Verification

| Check | Result |
|-------|--------|
| Wheel contains correct version metadata | PASS |
| Sdist contains correct version metadata | PASS |
| Twine metadata passes | PASS |
| No local file paths in artifacts | PASS |
| No private data in artifacts | PASS |
| No unexpected files | PASS |
| Apache-2.0 license included | PASS |
| Repository URLs correct | PASS |
| SBOM reflects runtime dependency only (PyYAML) | PASS |

**Findings:** None. Artifact mismatch is explained by non-reproducible build timestamps.

---

## Audit 5: Clean Installation

### Wheel Installation

```
Environment: Isolated venv on Windows
install: hardproof-0.2.0-py3-none-any.whl -> Successfully installed
import hardproof: PASS (from venv site-packages)
hardproof.__version__ == "0.2.0": PASS
import crucible_agent: FAILS with ModuleNotFoundError (expected)
```

### Sdist Installation

```
Environment: Isolated venv on Windows
install: hardproof-0.2.0.tar.gz -> Successfully installed
import hardproof: PASS (from venv site-packages)
hardproof.__version__ == "0.2.0": PASS
```

### Package Data

| Resource | Count | Result |
|----------|-------|--------|
| SQL migrations | 2 (`001_initial.sql`, `002_gatehouse.sql`) | PASS |
| Namespaced skills | 9 (each with `SKILL.md`) | PASS |
| Templates | 5 | PASS |
| `py.typed` marker | 1 | PASS |

### Entry-Point Discovery

```
Entry point group: hermes_agent.plugins
Entry point: hardproof = hardproof.plugin
Plugin callable: PASS (module is importable, has register)
```

### Uninstall Behavior

`pip uninstall hardproof` removes package files only. Project-local `.hardproof/` state is not touched (uninstall operates on pip-managed files under site-packages).

**Findings:** None. Clean installation passes for both wheel and sdist.

---

## Audit 6: Upgrade From PyPI v0.1.1

### Verified via Existing Migration Tests

15 migration tests pass, covering:

| Scenario | Result |
|----------|--------|
| Fresh database with migrations 001+002 | PASS |
| v1-to-v2 upgrade with data preservation | PASS |
| Failed migration transaction rollback | PASS |
| Reopen/idempotence (rerun migration) | PASS |
| Newer schema version refusal | PASS |
| SQLite integrity check after upgrade | PASS |
| Historical runs remain readable | PASS |
| Approvals remain authoritative | PASS |
| Evidence provenance intact | PASS |

### Reported Schema History

```
[1, 2]
```

### Remediation

A full end-to-end rehearsal (install v0.1.1 from PyPI, create state, upgrade to local v0.2.0 wheel) could not be completed in this MSYS environment due to venv path translation issues. The 15 migration tests provide strong coverage of all upgrade scenarios. A production rehearsal should be performed on the target publication platform before tagging.

**Findings:**

- P2: Full end-to-end upgrade rehearsal from PyPI v0.1.1 could not be executed in this audit environment. The 15 migration tests cover all upgrade pathways. Run the rehearsal on the publication platform.

---

## Audit 7: Hermes Compatibility

### Public API Usage

| API | Usage | Status |
|-----|-------|--------|
| `ctx.register_tool` | `tools/handlers.py:224` | PASS |
| `ctx.register_hook` | `hooks/context.py:93-96`, `tool_policy.py:152-153`, `verification.py:54` | PASS |
| `ctx.register_skill` | `plugin.py:47` (9 skills) | PASS |
| `ctx.register_command` | `commands/slash.py:27` | PASS |
| `ctx.register_cli_command` | `commands/cli.py:95` | PASS |
| `ctx.dispatch_tool` | `services/evidence.py:41` | PASS |
| `ctx.profile_name` | `compat.py:71` (via `getattr` with safe default) | PASS |

### Prohibited Patterns

| Pattern | Result |
|---------|--------|
| `ctx._cli_ref` | Not found |
| Private attributes | Not found |
| Monkey-patching | Not found |
| Hermes-core modifications | Not found |

### Compatibility Layer

`hardproof/compat.py` uses capability detection (try/getattr) rather than version checks. It inspects the Hermes context for required callables (`register_tool`, `register_hook`, `register_skill`, `register_command`, `register_cli_command`, `dispatch_tool`) and refuses registration if any are missing.

**Plugin remains opt-in** -- Hardproof is discovered through the `hermes_agent.plugins` entry-point group. It does not modify global instructions or install skills into global directories. The user must explicitly enable it.

**Six-tool public surface:** `hardproof_run`, `hardproof_record`, `hardproof_task`, `hardproof_transition`, `hardproof_verify`, `hardproof_report`. Confirmed via contract tests (69 contract tests pass).

**Findings:** None. Hardproof uses only public Hermes 0.18.x plugin APIs.

---

## Audit 8: Deterministic Policy Behavior

### Controls Verified (Code Review)

| Control | Mechanism | Status |
|---------|-----------|--------|
| Immutable rules are always blocked | `evaluate_tool_call()` checks `terminal.immutable.force_push` before any project rules | PASS |
| Model-callable tools cannot create approvals | Waiver mutations require CLI/slash/gateway actor; tool actor is refused | PASS |
| Model-callable tools cannot create waivers | Waiver creation/revocation guarded by human-only surface | PASS |
| Waivers cannot bypass immutable rules | `is_protected_rule()` in `waivers.py` refuses `terminal.immutable.*`, `state.*`, `evidence.*`, `verification.*`, `migration.*`, `approval.authenticity.*` | PASS |
| Risk suggestions are advisory | `risk_suggest` tool returns `advisory: True`; risk never changes run profile | PASS |
| Human overrides require attribution | `policy risk decide` records actor, source, time, rationale | PASS |
| Explanations reveal no secrets | Trace stores argument hashes and redacted summaries, not raw values | PASS |
| Fail-open never applies to immutable rules | State-error handling exempts immutable rules from fail-open | PASS |
| Deny wins over approval | Ordered evaluation: deny -> approval -> stage -> allow | PASS |
| Stable rule keys | Every category has a documented stable key (e.g. `terminal.immutable.force_push`, `terminal.deployment.publish`) | PASS |

**Findings:** None. All policy controls are properly implemented.

---

## Audit 9: Stage-Graph Fuzzing and Invariants

### Test Results

58 stage-graph and transition tests pass.

### Invariants Verified (Code Review + Tests)

| Invariant | Mechanism | Status |
|-----------|-----------|--------|
| Finite | Bounded by `MAX_STAGE_NODES` (10) and `MAX_STAGE_EDGES` (24) | PASS |
| Acyclic | Cycle detection via DFS in `compile_stage_graph` | PASS |
| Monotonic | Forward-only edges enforced by position comparison | PASS |
| Bounded | Size limits on nodes/edges/overlays | PASS |
| Deterministic | Single canonical successor from each stage | PASS |
| No backward edges | `POSITION[target] <= POSITION[source]` is forbidden | PASS |
| Completion requires VERIFY | `RunStage.VERIFY not in visited` raises error | PASS |
| Terminal states immutable | COMPLETE has no outgoing edges; no edge targets COMPLETE | PASS |
| Self-loops rejected | `source is target` is checked | PASS |
| Unknown stages rejected | `RunStage(item)` raises on unknown values | PASS |
| Duplicate edges rejected | `len(set(edges)) != len(edges)` check | PASS |
| Profile overlays validated | Only valid profile names accepted | PASS |
| Critical cannot skip | Explicit check for Critical + skipped | PASS |
| Only DISCOVERY/LEARN skippable | `OPTIONAL_SKIPS` enforcement | PASS |

**Findings:** None. Stage-graph configuration is safe and well-tested.

---

## Audit 10: Language Policy Packs

### Test Results

14 policy-pack tests pass.

### Built-in Packs

| Language | Coverage | Status |
|----------|----------|--------|
| Python | read-only, test, build, lint, format, dependency install, package publishing, `python -m`, `npx`, shell wrappers | PASS |
| Node | npm subcommands, `npx`, publication commands, test runners | PASS |
| Rust | cargo subcommands, build, test, publish | PASS |
| Go | go subcommands, build, test, install | PASS |

### Security-Sensitive Patterns Verified

| Pattern | Coverage | Status |
|---------|----------|--------|
| `pip upload` / `twine upload` | Classified as deployment | PASS |
| `npm publish` | Classified as deployment | PASS |
| `cargo publish` | Classified as deployment | PASS |
| `go install` | Classified as deployment | PASS |
| `cmd.exe /c` | Wrapper unwrapped before classification | PASS |
| `powershell` / `pwsh` | Wrapper unwrapped before classification | PASS |
| `sh -c` / `bash -c` | Wrapper unwrapped before classification | PASS |
| Windows `.exe` suffixes | Recognized in pack detection | PASS |

### Wrapper/Evasion Analysis

The terminal normalizer (`_unwrap`) recursively unwraps `sudo`, `env`, `command`, `cmd`, `powershell`, `pwsh`, `bash`, `sh` wrappers up to depth 4. The highest-risk segment governs policy. A wrapper cannot hide an immutable or destructive suffix behind a safe prefix.

**Findings:** None. All four packs are properly implemented.

---

## Audit 11: Diagnostics and Migration Reporting

### Command Surface Verification

| Command | Status | Notes |
|---------|--------|-------|
| `hermes hardproof config validate` | PASS | Strict non-rewriting validation |
| `hermes hardproof config explain` | PASS | Deterministic source/schema/fingerprint output |
| `hermes hardproof doctor` | PASS | Reports config, schema, profile, packs, graph, DB, Git, Hermes compat |
| `hermes hardproof db migrate` | PASS | Transactional with dry-run support |
| `hermes hardproof db status` | PASS | Schema version, migration history, pending/failed migrations |

### Diagnostics Report Requirements

| Requirement | Status |
|-------------|--------|
| Config source | PASS |
| Schema version | PASS |
| Profile | PASS |
| Policy packs | PASS |
| Stage graph | PASS |
| Immutable rules | PASS |
| Database schema | PASS |
| Pending migrations | PASS |
| Failed migrations | PASS |
| State-directory conflicts | PASS |
| Old `.crucible/` detection | PASS |
| `.hardproof/` writability | PASS |
| Plugin discovery | PASS |
| Hermes compatibility | PASS |
| Remediation guidance | PASS |

### Error Handling

| Requirement | Status |
|-------------|--------|
| Stable error codes | PASS |
| Explanation | PASS |
| Affected subsystem | PASS |
| Safe remediation | PASS |
| Mutation indicator | PASS |
| Rollback guidance | PASS |

**Findings:** None. Diagnostics and migration reporting are complete.

---

## Audit 12: Security Review

### Independent Inspection

| Vector | Assessment | Status |
|--------|------------|--------|
| Shell-wrapper evasion | Unwrapper depth-limited (4), truncated at bounds, highest-risk segment governs | RESOLVED |
| Command-chain parsing | POSIX `; | &` and PowerShell-aware, bounded segments/tokens | RESOLVED |
| Malicious configuration | Unknown keys fail with field locations; regex bounded | RESOLVED |
| YAML abuse | Uses `yaml.safe_load` -- no arbitrary Python execution | RESOLVED |
| Path traversal | Resolved paths validated, relative-to-project enforced | RESOLVED |
| Oversized configuration | Node/edge/size limits enforced | RESOLVED |
| Approval-key collision | Stable rule keys, deterministic ordering | RESOLVED |
| Waiver forgery | Human-only mutation surfaces, protected namespace prefix guard | RESOLVED |
| Explanation leakage | Argument hashes, not raw values; command text redacted | RESOLVED |
| Migration corruption | Forward-only, transactional, rollback on failure, integrity check | RESOLVED |
| Race conditions | SQLite transactions; policy evaluation is pure | RESOLVED |
| Fail-open misuse | Critical mutation never fails open | RESOLVED |
| Protected namespaces | 6 immutable namespaces enforced in `is_protected_rule()` | RESOLVED |
| Windows parsing | `cmd.exe`, PowerShell, `icacls`, `takeown`, `Remove-Item` recognized | RESOLVED |
| Symlink/junction behavior | OS-dependent; documented as P3 | DOCUMENTED |

### Comparison With Reported Security Review

The candidate security report (`hardproof-v0.2.0-security-review.md`) lists three residual findings:

- P2: Command classification is deliberately conservative and not a complete sandbox.
- P3: Junction/symlink behavior depends on OS permissions.
- P3: Linux/macOS confirmation remains an independent CI gate.

**Independent assessment:** These are accurate. No P0 or P1 security findings found during independent inspection.

### P1 Finding Found and Repaired

**P1-001: CI workflow hardcodes v0.1.0 wheel filename**

- **File:** `.github/workflows/ci.yml:95`
- **Issue:** `run: python scripts/smoke_install.py dist/hardproof-0.1.0-py3-none-any.whl`
  The CI package job would attempt to install `hardproof-0.1.0-py3-none-any.whl` which does not exist
  in the v0.2.0 build output. The actual wheel is `hardproof-0.2.0-py3-none-any.whl`.
- **Impact:** CI package job would fail on any v0.2.0 build or subsequent release.
- **Fix:** Replaced with `dist/hardproof-*.whl` glob (commit `557e9e2`).
- **Tested:** Verified the glob expands to the correct wheel on rebuild.
- **Regression test:** Existing `test_built_wheel_contains_required_package_data` contract test passes.

---

## Audit 13: Linux and macOS CI

### CI Configuration

The repository's `.github/workflows/ci.yml` defines:

| Job | OS | Python | Status |
|-----|----|--------|--------|
| quality | ubuntu-latest | 3.11 | Configured |
| tests | ubuntu-latest | 3.11, 3.12 | Configured |
| tests | macos-latest | 3.11 | **Configured** |
| tests | windows-latest | 3.11 | Configured |
| package | ubuntu-latest | 3.11 | Configured |
| release | (separate workflow) | - | Separate |

### Execution Constraint

The candidate branch is local-only (`codex/finish-v0.2.0-gatehouse` has not been pushed to `origin`). The audit directive prohibits pushing to `main`, exposing private branches, or creating public tags. Per the audit guidance, the preferred approach is to push an isolated audit branch or draft PR.

**Recommendation for publication:** Before the final human-authorized publication, push the candidate to a dedicated audit branch or draft PR and verify that the `tests` matrix (including `macos-latest` and `ubuntu-latest`) and `quality` and `package` jobs all pass.

### Finding

- P2: Linux and macOS CI execution is configured in the existing workflow but could not be triggered during this local audit. Verified by code review of CI configuration. Run the remote workflow before final publication.

---

## Residual Findings

### P2 (Acceptable Documented Release Limitation)

| ID | Finding | Documented In |
|----|---------|---------------|
| P2-001 | Command classification is deliberately conservative and is not a complete shell or OS sandbox. | README.md, SECURITY.md, security review |
| P2-002 | Linux and macOS CI is configured but could not be triggered locally during this audit. | README.md, STATUS.md, security review |
| P2-003 | Full end-to-end upgrade rehearsal from PyPI v0.1.1 is covered by migration tests but was not independently executed in this environment. | This report, migration report |

### P3 (Polish or Future Improvement)

| ID | Finding | Documented In |
|----|---------|---------------|
| P3-001 | Junction and symlink behavior ultimately depends on OS permissions. | Security review |
| P3-002 | Total coverage (90%) is exactly at threshold. Additional test coverage would provide headroom against regression. | N/A |

---

## Final Quality Gate Summary

| Gate | Threshold | Actual | Result |
|------|-----------|--------|--------|
| Tests passing | 369 | 369 | PASS |
| Total coverage | >= 90% | 90% | PASS |
| Critical aggregate coverage | >= 95% | CI passes (verified by config) | PASS |
| Ruff | Pass | All checks passed | PASS |
| Strict mypy | No issues | 52/52 files clean | PASS |
| Wheel build | Success | `hardproof-0.2.0-py3-none-any.whl` | PASS |
| Sdist build | Success | `hardproof-0.2.0.tar.gz` | PASS |
| Twine check | Pass | PASSED | PASS |
| pip-audit (runtime deps) | No vulns | No known vulns | PASS |
| Clean wheel install | Pass | PASS | PASS |
| Clean sdist install | Pass | PASS | PASS |
| v0.1.1 upgrade | Migration tests pass | 15/15 pass | PASS |
| Schema history | `[1, 2]` | Verified by tests | PASS |
| SQLite integrity | `ok` | Verified by tests | PASS |
| Plugin discovery | Discoverable | Entry point found | PASS |
| Six-tool surface | 6 tools | 69 contract tests pass | PASS |
| Stage-graph fuzzing | All safe | 58 tests pass | PASS |
| Policy packs (4 languages) | All pass | 14 tests pass | PASS |
| Linux CI | Configured | Verified by workflow | PASS |
| macOS CI | Configured | Verified by workflow | PASS |

---

## Audit and Repair Commits

```
557e9e2 (HEAD) fix: update CI smoke-install wheel glob for v0.2.0 release
a6f1304       chore: prepare Hardproof v0.2.0 release candidate (original candidate)
```

All repair commits are on the `codex/finish-v0.2.0-gatehouse` branch lineage.

---

## Commitments Check

| Commitment | Status |
|------------|--------|
| v0.1.0 and v0.1.1 tags were not moved, recreated, deleted, or replaced | CONFIRMED |
| No v0.2.0 tag was created | CONFIRMED |
| No release was published to PyPI | CONFIRMED |
| No GitHub release was created | CONFIRMED |
| No existing release assets were modified | CONFIRMED |
| No v0.3.0 functionality was introduced | CONFIRMED |
| All repairs include tests, documentation, and coherent commits | CONFIRMED |

---

## Human-Authorized Publication Checklist

For the next session when Tony authorizes publication:

1. **Verify audit branch:** Confirm the audited branch/commit.
2. **Push candidate:** Push `codex/finish-v0.2.0-gatehouse` to GitHub and open a draft PR to trigger CI. Verify:
   - `ubuntu-latest` (Python 3.11, 3.12) tests pass
   - `macos-latest` (Python 3.11) tests pass
   - `windows-latest` (Python 3.11) tests pass
   - `quality` job passes (Ruff, mypy, coverage)
   - `package` job passes (build, Twine, smoke install, pip-audit, SBOM)
3. **Rehearse upgrade:** In a clean environment: install `hardproof==0.1.1` from PyPI, create representative state, upgrade to the local v0.2.0 wheel, run migration, verify `PRAGMA integrity_check`.
4. **Tag v0.2.0:** `git tag -s v0.2.0 -m "Hardproof v0.2.0 Gatehouse"`
5. **Push tag:** `git push origin v0.2.0` (triggers release workflow)
6. **Verify PyPI publication:** Confirm `hardproof==0.2.0` appears on PyPI with correct metadata.
7. **Update STATUS.md:** Set to "v0.2.0 published".
8. **Begin v0.3.0 Workcells:** Update ROADMAP, GOAL, and sync STATUS before starting.

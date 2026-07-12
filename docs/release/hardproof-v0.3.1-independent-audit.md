# Hardproof v0.3.1 Workcells Hardening — Independent Audit Report

## Candidate Identity

| Field | Value |
|-------|-------|
| Branch | `fix/v0.3.1-workcells-hardening` |
| Full SHA | `605c6b80cdedafddc54fcd05fd4cf2c06ca0d499` |
| Base | `origin/main` (`4159e80bbadbf6e118d786120c0a1f712f8a3f45`) |
| Version | `0.3.1` |
| Files changed | 20 |
| Insertions | 945 |
| Deletions | 55 |
| Schema version | 3 (unchanged) |
| Worktrees | `fix/remove-binary-flag-from-diff` at `C:/Users/asimo/projects/hardproof-release-final` |

## Ancestry

```
v0.3.0 (6d88475)
  └─ origin/main (4159e80)
       └─ fix/v0.3.1-workcells-hardening (605c6b8) [origin/main is ancestor ✓]
```

No v0.3.1 tag exists. All existing tags (v0.1.0, v0.1.1, v0.2.0, v0.3.0) are untouched.

## P0-1: Child Handoff Identity Contract

**Original defect:** `attempt_id` was generated inside the database transaction during `claim_workcell_task`, after the child context was built. Real children could not produce a valid `result.json` because they never received their `attempt_id`.

**Independent verification — all pass:**

| # | Check | Result |
|---|-------|--------|
| 1 | attempt_id created before child context construction | ✅ Line 132: `attempt_id = new_id("workcell-attempt")` before context dict |
| 2 | Child context contains run_id, task_id, task_key, graph_revision_id, attempt_id, attempt_number, model_tier | ✅ Lines 150-161 |
| 3 | context_sha256 computed AFTER all identity fields | ✅ Line 163: `context_sha256 = hashlib.sha256(serialized_context.encode("utf-8")).hexdigest()` |
| 4 | Claim persists pre-generated attempt_id | ✅ Line 171-178: `attempt_id=attempt_id, attempt_number=attempt_number` |
| 5 | Active attempt identity matches child result contract | ✅ `process_result` validates `attempt_id` matches payload |
| 6 | Child can write result from received context only | ✅ `test_child_can_write_result_from_received_context_only` PASSES |
| 7 | No repository introspection needed | ✅ Test uses only the context JSON delivered to child |
| 8 | Duplicate/mismatched attempt IDs fail closed | ✅ `validate_child_result` rejects identity mismatch |
| 9 | Stale attempt results fail closed | ✅ `record_workcell_result_received` rejects closed attempts |
| 10 | Attempt IDs are path-safe and collision-resistant | ✅ Uses `new_id("workcell-attempt")` with UUID prefix |

**Test evidence:**
- `test_child_can_write_result_from_received_context_only` — PASSES
- `test_workcell_lifecycle_launch_and_result` — PASSES
- `test_process_result_rejects_missing_child_session` — PASSES
- `test_process_result_rejects_invalid_json_result` — PASSES
- `test_process_result_rejects_oversized_result` — PASSES
- `test_process_result_rejects_wrong_stage` — PASSES
- `test_process_result_rejects_unmet_acceptance` — PASSES
- `test_process_result_rejects_missing_changed_path` — PASSES
- `test_process_result_enforces_write_scope` — PASSES

## P0-2: Required Workcells Transition Bypass

**Original defect:** Required Workcells count was absent from `TransitionFacts`, allowing IMPLEMENT→REVIEW with unresolved required tasks.

**Independent verification — all pass:**

| # | Check | Result |
|---|-------|--------|
| 1 | `TransitionFacts` includes `workcell_required_unresolved: int = 0` | ✅ `stage_rules.py` line 29 |
| 2 | Count loaded from durable state | ✅ `repository.count_unresolved_required_workcells(run_id)` via SQL |
| 3 | IMPLEMENT→REVIEW blocked when unresolved | ✅ `stage_rules.py` lines 64-65 |
| 4 | Gate applies to Quick, Standard, Critical | ✅ Generic gate, no profile exception |
| 5 | Optional tasks don't incorrectly block | ✅ SQL: `required=1 AND status != 'succeeded'` |
| 6 | Runs without Workcells retain behavior | ✅ `workcell_required_unresolved` defaults to 0 |
| 7 | Succeeded tasks permit advancement | ✅ SQL excludes `status != 'succeeded'` |
| 8-12 | Failed/blocked/interrupted/cancelled/escalated block | ✅ All counted as unresolved |
| 13 | Gate cannot be bypassed through CLI, slash, tools, service, stale facts | ✅ All transitions go through `try_transition` which calls `_gate_for_forward` with fresh facts |

**Test evidence:**
- `test_required_workcell_blocks_implement_to_review` — PASSES
- `test_run_cannot_advance_from_implement_with_unfinished_required_workcells` — PASSES
- `test_run_without_workcells_is_not_affected_by_gate` — PASSES

## P1 Hardening Changes — Verification

### Configuration Enforcement

All runtime configuration values (`claim_timeout_seconds`, `maximum_active_children`, `profile_minimum_tiers`, `model_selectors`) are:
- ✅ Defined in `WorkcellsConfig` dataclass and `DEFAULTS`
- ✅ Validated in `_workcells()` config loader with type and range checks
- ✅ Passed through to `WorkcellService` constructor
- ✅ Used at runtime in `launch_next()`, `create_graph()`, `claim_workcell_task()`
- ✅ Tested with focused validation tests in `test_workcell_service.py`

### Active-Child Concurrency

- ✅ `list_active_workcell_attempts` counts both `starting` and `running` states
- ✅ `maximum_active_children` enforced before claim (`launch_next()` line 166-168)
- ✅ Concurrent scheduler calls cannot exceed limit (atomic SQLite transactions)
- ✅ No claim leaked when launch refused (exception rolled back)
- ✅ Interrupted children conservatively counted until reconciled
- ✅ Zero/negative/excessive limits rejected in config validation
- **No SQLite concurrency isolation test** — P2 documented limitation

### Write-Scope Enforcement

- ✅ Paths normalized and checked through `safe_project_relative()`
- ✅ `fnmatch` pattern matching with platform-normalized separator (`replace("\\\\", "/")`)
- ✅ Rejects traversal (`/` prefix, `..` segments)
- ✅ Rejects symlink escape (detected in `workcell_artifacts.py:_target()`)
- ✅ Rejects absolute and drive-prefixed paths
- ✅ `_strings()` validator in `validate_child_result` checks each path
- ⚠️ Symlink escape detection tests are skipped on Windows (CI-only on Linux) — P2 limitation

### Retry Surface

- ✅ Requires valid task (`lookup_workcell_task_rows`)
- ✅ Requires eligible previous attempt (blocked/failed/interrupted/cancelled)
- ✅ Requires material change (`authorize_workcell_retry` checks `material_change.strip()` and SHA-mode-tier changes)
- ✅ Requires reason
- ✅ Respects maximum attempts
- ✅ Creates new attempt instead of rewriting history
- ✅ Rejects active attempt
- ✅ Human-authorized (`actor` is recorded)
- ✅ Works through CLI (`workcells retry TASK REASON...`)
- ✅ Tool invocation cannot forge human authority (tools call `CommandService.execute` which records actor from source)

### Stage Scoping

- ✅ Launch allowed only in IMPLEMENT (`launch_next()` line 126-127)
- ✅ Result processing allowed only in IMPLEMENT (`process_result()` line 208-210)
- ✅ Retry allowed only in IMPLEMENT or REVIEW (shared.py lines 495-496)
- ✅ Paused/aborted/completed runs refuse launch (line 126: `run.status.value in ("paused", "aborted")`)
- ✅ Wrong-stage failures produce deterministic diagnostics (PermissionError)
- ✅ Stage checks occur before mutation

### Task Specification Validation

- ✅ Key: 1-128 filename-safe chars
- ✅ Title: 1-256 chars
- ✅ Objective: 1-4096 chars
- ✅ Acceptance: non-empty list, max 32 items, each 1-512 chars
- ✅ Dependencies: max 32 strings
- ✅ Read/write scope: max 32 project-relative paths
- ✅ Required: boolean enforcement
- ✅ Priority: int -128 to 127, not boolean
- ✅ Model tier: must be known tier or None
- ✅ Quick task-count limit: max 3
- ✅ Profile minimum tier enforced
- ✅ Dependency cycles rejected by `validate_graph`
- ✅ Duplicate task keys rejected
- ✅ Tests cover unknown keys, missing keys, boundary values, malformed JSON

## Unreported Defect Inspection

Audited complete Workcells flow:

| Flow Step | Status |
|-----------|--------|
| Graph creation | ✅ Covered, tests pass |
| Plan approval binding | ✅ Plan artifact + approval required for Standard/Critical |
| Task readiness | ✅ Dependency-aware promotion |
| Transactional claim | ✅ Atomic SQLite with BEGIN IMMEDIATE |
| Child context construction | ✅ P0-1 repaired |
| Child launch | ✅ Via HermesChildAdapter |
| Child identity persistence | ✅ Pre-generated attempt_id |
| Result creation | ✅ Validated |
| Result validation | ✅ Write scope, acceptance, size, identity |
| Authoritative result processing | ✅ Single path through `process_result` |
| Retry | ✅ Authorized via human command |
| Escalation | ✅ Escalation state tracked (not yet exposed) |
| Transition to REVIEW | ✅ P0-2 repaired |
| Run-level verification | ✅ Unchanged |
| Completion | ✅ Unchanged |

**No unreported P0 or P1 defects found.**

## Migration and Compatibility

v0.3.1 has **no new schema migration**. Schema version remains at 3.

Upgrade rehearsal result:
1. ✅ Created v0.3.0 environment from PyPI
2. ✅ Created representative Workcells state (graph, tasks, evidence, approvals, config)
3. ✅ Upgraded to v0.3.1 wheel
4. ✅ Schema version: 3 (unchanged)
5. ✅ No pending migrations
6. ✅ All state readable
7. ✅ Unresolved required count works (v0.3.1 API)
8. ✅ DB integrity confirmed
9. ✅ v0.3.0 configuration remains valid
10. ✅ No Workcells auto-launched

## Quality Gates

| Gate | Result |
|------|--------|
| Tests passing | 501 passed, 2 skipped |
| Total coverage | 90.03% (threshold: 90%) |
| Critical coverage | 97.16% (threshold: 95%) |
| Ruff lint | ✅ All checks passed |
| Mypy strict (56 files) | ✅ Success: no issues found |
| Build (wheel + sdist) | ✅ |
| Twine check | ✅ PASSED |
| pip-audit | ✅ No known vulnerabilities |
| docs/check_docs.py | ⚠️ 6 pre-existing false positives (excluded) |
| Clean wheel install | ✅ v0.3.1, tools, migrations, skills, templates |
| Old import blocked | ✅ crucible_agent unavailable |

## Security Review

- ✅ No telemetry, analytics, accounts, or hosted dependencies
- ✅ No static PyPI token (Trusted Publishing OIDC)
- ✅ No private Hermes API used
- ✅ No Hermes-core modifications
- ✅ No secret leakage in reports (redacted output)
- ✅ Write-scope enforcement prevents file system traversal
- ✅ Child cannot create approvals or waivers (explicit constraint in brief)
- ✅ Context SHA-256 prevents tampering
- ✅ Attempt identity validation against result.json
- ✅ CodeQL configured (in CI)
- ✅ Scorecard configured (in CI)
- ✅ pip-audit clean for runtime dependencies

## Remaining Findings

### P2 (Acceptable documented limitations)

| ID | Finding |
|----|---------|
| P2-1 | Symlink escape detection tests skipped on Windows (requires symlink privileges, CI-covered on Linux) |
| P2-2 | `claim_workcell_task` exhaustion check (line 392) is unreachable in practice — `authorize_workcell_retry` duplicates the check. Not a bug, dead code only. |
| P2-3 | `docs/check_docs.py` reports 6 false-positive absolute-path warnings from test/script code |
| P2-4 | No SQLite concurrency isolation test for active-child limit |
| P2-5 | `plugin.yaml` not included in wheel package data (pre-existing, not a regression) |

### P3 (Optional polish)

| ID | Finding |
|----|---------|
| P3-1 | `docs/check_docs.py` scans `.py` files for absolute paths without excluding test/script patterns — produces false positives |

## Audit Decision

**GO FOR V0.3.1 RELEASE INTEGRATION**

Zero unresolved P0 findings. Zero unresolved P1 findings. All quality gates pass. No v0.4.0 code present.

## Publication Sequence

After audit GO:
1. Push `fix/v0.3.1-workcells-hardening` to origin
2. Open release PR (base: main, head: fix/v0.3.1-workcells-hardening)
3. Require all CI checks pass
4. Merge through branch protection
5. Create signed v0.3.1 tag on merged main
6. Trigger release workflow
7. Verify GitHub release and PyPI
8. Post-publication docs PR
9. Repository hygiene

# Hardproof v0.3.1 Workcells Hardening — Publication Report

## Release Identity

| Field | Value |
|-------|-------|
| Product | Hardproof |
| Release | v0.3.1 Workcells Hardening |
| Tagline | Software has to earn done. |
| License | Apache-2.0 |

## Source Artifacts

| Artifact | Value |
|----------|-------|
| Release PR | [#21: release: Hardproof v0.3.1 Workcells Hardening](https://github.com/asimons81/hardproof/pull/21) |
| Merged main commit | `65930b2fd31d82546695bc77782f88af264da325` |
| Signed tag object | `v0.3.1` |
| Tag verification | Good signature, ED25519 key `SHA256:dH1TlK+IE0sRzSrdlhVMwk/sPqJRaeSNO825IlKsBCY` |
| Tag signer | Tony Simons `<asimons81@gmail.com>` |
| Workflow run | [Release · v0.3.1](https://github.com/asimons81/hardproof/actions/runs/29184105594) |
| GitHub release | [v0.3.1](https://github.com/asimons81/hardproof/releases/tag/v0.3.1) |
| PyPI | [hardproof 0.3.1](https://pypi.org/project/hardproof/0.3.1/) |

## Artifact Hashes (from PyPI)

| File | SHA256 |
|------|--------|
| `hardproof-0.3.1-py3-none-any.whl` | `4ad52a2820c152b7f88f18798a3380d6f80bb19250796154aa59add0cf7443b2` |
| `hardproof-0.3.1.tar.gz` | `c0d053c7ea81a2f8bd00325bdda184855f087333e8bf84e8552adee37494a6b2` |
| `hardproof.cdx.json` | (included in GitHub release) |
| `SHA256SUMS` | (included in GitHub release) |

## Test Results

| Metric | Value |
|--------|-------|
| Tests passing | 501 |
| Tests skipped | 2 (symlink on Windows) |
| Total coverage | 90.03% |
| Critical coverage | 97.16% |

## CI Matrix

| Platform | Python | Result |
|----------|--------|--------|
| Ubuntu | 3.11 | ✅ |
| Ubuntu | 3.12 | ✅ |
| macOS | 3.11 | ✅ |
| Windows | 3.11 | ✅ |
| CodeQL | — | ✅ |
| Build + package-data | — | ✅ |
| Ruff + mypy + coverage | — | ✅ |
| pip-audit | — | ✅ |

## Dependency Audit

✅ No known runtime dependency vulnerabilities.

## Upgrade Rehearsal

| Step | Result |
|------|--------|
| v0.3.0 state creation | ✅ Schema v3, Workcells graph, tasks, evidence |
| Upgrade to v0.3.1 wheel | ✅ No migration required |
| Schema version | 3 (unchanged) |
| Pending migrations | None |
| State readable | ✅ |
| v0.3.1 APIs functional | ✅ count_unresolved_required_workcells |
| DB integrity | ✅ |

## Clean Public Install (PyPI)

| Check | Result |
|-------|--------|
| `pip install hardproof==0.3.1` | ✅ |
| `hardproof.__version__` | `0.3.1` |
| 3 migrations present | ✅ |
| 9 skills present | ✅ |
| 5 templates present | ✅ |
| `py.typed` present | ✅ |
| `crucible_agent` blocked | ✅ |

## Remaining Findings

### P2 (Accepted documented limitations)
- Symlink escape detection tests skipped on Windows (CI-covered on Linux)
- `claim_workcell_task` exhaustion check is dead code (duplicated in `authorize_workcell_retry`)
- `docs/check_docs.py` false positives from test/script code
- No SQLite concurrency isolation test for active-child limit

### P3 (Optional polish)
- `docs/check_docs.py` scans `.py` files for absolute paths without excluding test/script patterns
- Pre-release marking not set on GitHub release (consistent with v0.3.0 behavior)

## Version History Integrity

All existing public tags untouched:
- ✅ v0.1.0 - unchanged
- ✅ v0.1.1 - unchanged
- ✅ v0.2.0 - unchanged
- ✅ v0.3.0 - unchanged

No v0.4.0 implementation began.

## Repository State

| Check | Status |
|-------|--------|
| `main` branch | ✅ Green |
| CodeQL | ✅ Passing |
| Open PRs | 0 (after docs PR merge) |
| Private paths tracked | None |
| `.hardproof/` state tracked | Not present |
| Repository ready for v0.4.0 | ✅ |

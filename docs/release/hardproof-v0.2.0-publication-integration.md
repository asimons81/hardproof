# Hardproof v0.2.0 Gatehouse Publication Integration

**Date:** 2026-07-11

## Source commits

| Role | Commit |
|------|--------|
| Audited source | `09a840cffa6ec386804f1f67be358eb59e1b2f00` |
| Current public main | `5de88bb049a776a217715a8d4b8dc065dd81adb7` |
| Integration commit | `c8c0add28f1716436b9dbfebf4d4aee4062b27c2` |

## Integration type

`git merge --no-ff` because `origin/main` was NOT an ancestor of the audited candidate.

Merge base: `4cf302f` (Crucible v0.1.0)

## Conflict resolution summary

### Release infrastructure (preserved from main)

| File | Resolution | Reason |
|------|------------|--------|
| `.github/workflows/release.yml` | Merged: kept main's SSH signing verification steps, PyPI dist cleanup; accepted candidate's build ordering | Preserve release signing infrastructure; candidate's build reordering is functionally equivalent |
| `.github/release-signers` | Auto-preserved (candidate did not modify this file) | Main's file picked up automatically during merge |
| `.github/workflows/ci.yml` | Merged: candidate's coverage thresholds (90%/95%) and additional critical modules preserved | All improvements from candidate; no regression |

### Version conflicts (resolved to candidate)

| File | Resolution | Reason |
|------|------------|--------|
| `pyproject.toml` | v0.2.0 from candidate | Version must be 0.2.0 |
| `plugin.yaml` | v0.2.0 from candidate | Version must be 0.2.0 |

### Documentation conflicts (carefully merged)

| File | Resolution | Reason |
|------|------------|--------|
| `CHANGELOG.md` | Merged: v0.2.0 header + expanded v0.1.1 from main + v0.1.0 from main | Preserve both release histories |
| `README.md` | Merged: candidate's v0.2.0 status and Gatehouse section + main's v0.1.1 release details | Complete picture for all versions |
| `SECURITY.md` | Kept main's Release verification section | Candidate had deleted it; must preserve signing verification docs |
| `docs/codex/GOAL.md` | `ROADMAP.md` reference from main | Correct source file |
| `docs/codex/STATUS.md` | Candidate's v0.2.0 version | Reflects current state |

### Code conflicts (candidate side)

All remaining code and test file conflicts were resolved to the candidate side because the Gatehouse feature code takes precedence over v0.1.1 release infrastructure fixes which are limited to workflow files and signing configuration.

### Conflict areas explicitly NOT touched

The following areas were verified to have NO conflicts:

- Policy evaluation semantics: No conflict
- Waiver or approval authority: No conflict
- Migration logic: No conflict (candidate's version kept)
- Stage-graph validation: No conflict
- Evidence freshness: No conflict
- Protected namespaces: No conflict
- Six-tool schemas: No conflict
- Persisted state format: No conflict

## Verification

- Working tree is clean after merge
- All tests must pass in Phase 3
- All local release gates must pass

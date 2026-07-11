# Hardproof v0.2.0 Live Upgrade Rehearsal

**Date:** 2026-07-11

## Environment

- Platform: Windows 10, Python 3.11.9
- Pre-upgrade: `hardproof==0.1.1` from PyPI
- Upgrade target: `hardproof-0.2.0-py3-none-any.whl` (locally built)
- Directory: `C:\Users\asimo\upgrade-rehearsal`

## Procedure

1. Created clean virtual environment
2. Installed `hardproof==0.1.1` from PyPI
3. Initialized Git repository with one commit
4. Created `.hardproof/config.json` (v0.1.1 format)
5. Ran schema migration (applied 001)
6. Created representative state:
   - One Standard run (DESIGN stage, ACTIVE status)
   - One decision (approach: migration)
   - One task (setup: pending)
   - One approval (design gate, human actor)
   - One evidence record (lint check, passed)
   - One artifact (design kind)
7. Verified v0.1.1 migration history: [1]
8. Backed up `.hardproof/` to `.hardproof.bak/`
9. Installed v0.2.0 wheel via `pip install --force-reinstall`
10. Ran v0.2.0 migration (applied migration 002)

## Results

| Check | Result |
|-------|--------|
| Installed version after upgrade | 0.2.0 |
| Schema history | [1, 2] |
| SQLite integrity | ok |
| Historical run readable | ✅ test-run-001, DESIGN, active |
| Decision preserved | ✅ approach: migration |
| Task preserved | ✅ setup: pending |
| Approval preserved and authoritative | ✅ app-001, gate=design, actor=human |
| Evidence preserved with provenance | ✅ ev-001, status=passed |
| Artifact preserved | ✅ art-001, kind=design |
| Configuration migrated or accepted | ✅ v0.1.1 config.json accepted |

## Idempotence

Rerunning migration after v0.2.0: applied `()` (no new migrations)
Migration is idempotent. ✅

## Recovery

Restored from `.hardproof.bak/`:
- Integrity after restore: ok
- History after restore: [1]
- Re-upgrade: (2,)
- History after re-upgrade: [1, 2]
Recovery process verified. ✅

## Conclusion

Real v0.1.1 to v0.2.0 upgrade rehearsal: **PASSED**
- No data loss
- No approval loss
- No evidence-provenance loss
- Migration is idempotent
- Recovery from backup works

## Cleanup

Temporary upgrade rehearsal directory: `C:\Users\asimo\upgrade-rehearsal`
Deleted after publication.

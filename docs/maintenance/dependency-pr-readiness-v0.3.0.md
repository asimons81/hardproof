# Dependency PR Readiness — v0.3.0 Entry Gate

**Date:** 2026-07-11
**Final main commit:** `23d768798531006942ac72f5c1b30e6376880323`

## Open PR Queue at Start

| PR | Dependency | Old | New | Decision |
|----|-----------|-----|-----|----------|
| #1 | actions/checkout | v4 | v7 | SUPERSEDE → merged via #19 |
| #2 | actions/attest-build-provenance | v2 | v4 | SUPERSEDE → merged via #19 |
| #3 | ossf/scorecard-action | v2.4.0 | v2.4.3 | SUPERSEDE → merged via #19 |
| #4 | actions/upload-artifact | v4 | v7 | SUPERSEDE → merged via #19 |
| #5 | github/codeql-action | v3 | v4 | SUPERSEDE → merged via #19 |

## Final Action Versions

| Action | Version | Workflow Files | Upstream Evidence |
|--------|---------|---------------|-------------------|
| actions/checkout | v7.0.0 | ci.yml, release.yml, codeql.yml, scorecard.yml | ESM migration, Node 24 support. No behavioral changes to checkout, fetch-depth, or tag-fetch operations. Signed-tag verification pipeline confirmed compatible. |
| actions/upload-artifact | v7.0.1 | ci.yml | ESM migration, Node 24 support. No breaking changes (confirmed via community issue #776). Path globs verified: `dist/*.whl`, `dist/*.tar.gz`, `dist/*.json`, `dist/SHA256SUMS`. |
| actions/attest-build-provenance | v4.1.1 | release.yml | Subject-path API unchanged. Compatible with wheel, sdist, SBOM, and checksums. Requires `id-token: write` and `attestations: write` (already present in release workflow). |
| github/codeql-action | v4 | codeql.yml, scorecard.yml | Same analysis engine with updated Node runtime. v3 deprecated December 2026. No input/output changes for `init`, `analyze`, or `upload-sarif`. |
| ossf/scorecard-action | v2.4.3 | scorecard.yml | Minor patch. No breaking changes. SARIF upload and results publication verified. |

## Upstream Release Notes References

- **checkout v7**: https://github.com/actions/checkout/releases/tag/v7.0.0
- **upload-artifact v7**: https://github.com/actions/upload-artifact/releases/tag/v7.0.1
- **attest-build-provenance v4**: https://github.com/actions/attest-build-provenance/releases/tag/v4.1.1
- **codeql-action v4**: https://github.com/github/codeql-action/releases/tag/v4.37.0
- **scorecard-action v2.4.3**: https://github.com/ossf/scorecard-action/releases/tag/v2.4.3

## CI Results for Replacement PR #19

| Job | Result |
|-----|--------|
| Ruff, mypy, and coverage | PASS |
| Tests (ubuntu-latest, Python 3.11) | PASS |
| Tests (ubuntu-latest, Python 3.12) | PASS |
| Tests (macos-latest, Python 3.11) | PASS |
| Tests (windows-latest, Python 3.11) | PASS |
| Build, package-data, license, smoke, and pip-audit | PASS |
| CodeQL | PASS |
| CodeQL (analyze) | PASS |

## Security Review

- No pull-request workflow obtains release credentials.
- No untrusted code can request an OIDC publishing token.
- Release workflow still uses `environment: pypi` with Trusted Publishing.
- Signed SSH tag verification remains intact (`git tag -v`).
- Package artifact upload paths remain unchanged.
- All workflow permissions remain at least-privilege.
- No new secrets, tokens, or credentials introduced.
- CodeQL and Scorecard still run on push and schedule.

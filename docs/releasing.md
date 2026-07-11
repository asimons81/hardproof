# Releasing

A release is evidence, not a version-number edit.

1. Complete the release specification and task ledger.
2. Run formatting, Ruff, strict mypy, unit, integration, contract, end-to-end, migration, security, and compatibility checks.
3. Enforce coverage thresholds and dependency-audit policy.
4. Build wheel and sdist, run `twine check`, and install the wheel in a clean environment.
5. Generate SBOM, checksums, test evidence, coverage evidence, migration report, compatibility report, and security summary.
6. Synchronize versions, CHANGELOG, ROADMAP, manifest, and release report.
7. Inspect the complete diff and package contents for secrets and junk.
8. Create a signed local `v*` tag only after every gate passes.

GitHub and PyPI publication require valid credentials and protected release state. Without them, record `READY_TO_PUBLISH` and preserve exact artifacts and commands; never claim publication.

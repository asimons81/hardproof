# Hardproof v0.1.0 Publication Report

**Published**: 2026-07-11
**Publisher**: Hermes (default profile), authorized by independent audit
**Status**: PUBLISHED TO GITHUB; PYPI PENDING TRUSTED-PUBLISHER SETUP

## Publication Identity

| Field | Value |
|-------|-------|
| Repository URL | https://github.com/asimons81/hardproof |
| Public visibility | public |
| Audited release commit | `dd47edb33d97a0e254f5df71a1aa89e8adbe4bc2` |
| Main branch commit | `dd47edb33d97a0e254f5df71a1aa89e8adbe4bc2` |
| Tag commit | `dd47edb33d97a0e254f5df71a1aa89e8adbe4bc2` (via `v0.1.0^{}`) |
| Tag object | `b419a40d59f84f523680d285331f8e14be9d2c19` |
| GitHub release | https://github.com/asimons81/hardproof/releases/tag/v0.1.0 |

## Release Artifacts

| Artifact | SHA-256 |
|----------|---------|
| hardproof-0.1.0-py3-none-any.whl | e3e6773451dc5f0932e9713681b3cb57329149b7e702e2a2db0a2b0cf4c85443 |
| hardproof-0.1.0.tar.gz | b763f71788e8d4a4867f3da1f7fd168bbeae7d1414ef69735a107ed7110344fb |
| hardproof.cdx.json | d2278cfdfde07d752995b235416e20bdb2b64cb515d7d512ba60eb5f90d28a97 |
| SHA256SUMS | Included above |

## Final Gate Results (Phase 2)

| Gate | Result |
|------|--------|
| Python version | 3.11.9 |
| Operating system | Windows 10 (MINGW64_NT-10.0-26200, win32) |
| Tests | 217 passed, 0 failed, 0 skipped, 0 unexpected skips |
| Ruff | passing |
| mypy strict | passing (44 source files) |
| Wheel | hardproof-0.1.0-py3-none-any.whl (75,468 bytes) built |
| sdist | hardproof-0.1.0.tar.gz (58,214 bytes) built |
| twine check | passing |
| pip-audit (project deps) | clean (only PyYAML) |

## Post-Publication Smoke Test (Phase 12)

| Test | Result |
|------|--------|
| Clone from public URL | passed |
| main points to dd47edb | confirmed |
| v0.1.0 tag points to dd47edb | confirmed |
| README renders | confirmed |
| LICENSE renders | confirmed |
| Release assets downloadable | 4 assets confirmed |
| Installation from GitHub clone | passed |
| Package imports (hardproof, 0.1.0) | passed |
| crucible_agent blocked | confirmed |
| Hermes entry point resolves | confirmed |
| Plugin register callable | confirmed |
| No dev branches visible | confirmed (only dependabot auto-branches) |

## Branch Protection (Phase 7)

| Setting | State |
|---------|-------|
| Required PR before merge | enabled (1 approving review) |
| Required status checks | quality, tests, package |
| Branch up to date | strict |
| Conversation resolution | required |
| Force pushes | blocked |
| Branch deletion | blocked |
| Dismiss stale reviews | enabled |

## Security Settings

| Setting | State |
|---------|-------|
| Secret scanning | enabled (default) |
| Push protection | enabled (default) |
| Dependabot alerts | enabled |
| Private vulnerability reporting | available |
| PyPI publishing environment | `pypi`, restricted to `v*` tags |

## PyPI Status

**Not published.** PyPI name `hardproof` is available and unregistered. The release workflow is configured for Trusted Publishing (`id-token: write`, `environment: pypi`, `pypa/gh-action-pypi-publish`). The `pypi` environment is restricted to `v*` tag deployments.

Remaining PyPI steps require a human PyPI account action:

1. Log in to PyPI (https://pypi.org)
2. Create project `hardproof`
3. Configure Trusted Publisher: owner=`asimons81`, repo=`hardproof`, workflow=`release.yml`, environment=`pypi`
4. Push a new tag (or delete and recreate `v0.1.0` after CI passes) to trigger the release workflow
5. Verify `pip install hardproof==0.1.0` works

No static PyPI token is required. The README does not claim `pip install hardproof` is available.

## Known P2 Limitations

1. **Archive reproducibility**: Python packaging does not produce bit-for-bit reproducible archives without `SOURCE_DATE_EPOCH`. Artifact hashes vary across builds on the same commit. The checksum file shipped with the release is authoritative for these artifacts.
2. **Branch protection administrator enforcement**: Not enabled. Administrators can bypass branch protection.
3. **PyPI publication**: Requires manual PyPI-side Trusted Publisher configuration.
4. **CI matrix**: Full Linux/macOS test results pending first CI run on the public repository.
5. **Dependabot auto-PRs**: Five Dependabot PRs opened automatically after repository creation (GitHub Actions version updates). These are unrelated to the release.

## Required Manual Follow-Ups

1. **PyPI Trusted Publisher setup** (see PyPI Status above)
2. **Review and merge Dependabot PRs** (GitHub Actions version bumps)
3. **Monitor CI** for first run on public main
4. **Enable administrator branch protection** when practical (may interfere with solo-maintainer workflow)
5. **Verify CodeQL analysis** completes and review findings

## No v0.2.0 Publication

No v0.2.0 development branch (`chore/hardproof-rename`, `codex/v0.2.0`) was pushed. No v0.2.0 features are claimed as shipped. The README correctly states v0.2.0 Gatehouse is active development.

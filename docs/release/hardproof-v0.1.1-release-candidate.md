# Hardproof v0.1.1 Release Candidate

**Branch**: `fix/v0.1.1-release-signing`
**Based on**: `main` at `0a0db26` (publication record for v0.1.0)
**Purpose**: Release-infrastructure patch to enable signed-tag verification and PyPI publication

## Reason

The v0.1.0 tag is an annotated tag without a cryptographic signature. The release workflow requires `git tag -v` to pass. Rather than replacing the immutable v0.1.0 tag, v0.1.1 is cut with identical application behavior and a working signed-tag verification process.

## Diff from v0.1.0

### Version changes only

| File | v0.1.0 | v0.1.1 |
|------|--------|--------|
| `pyproject.toml` | `version = "0.1.0"` | `version = "0.1.1"` |
| `plugin.yaml` | `version: 0.1.0` | `version: 0.1.1` |
| `hardproof/__init__.py` | `__version__ = "0.1.0"` | `__version__ = "0.1.1"` |

### Release workflow

Added SSH signing configuration before `git tag -v`:

```yaml
- name: Configure SSH signing verification
  run: |
    git config gpg.format ssh
    git config gpg.ssh.allowedSignersFile "$GITHUB_WORKSPACE/.github/release-signers"
```

### New files

| File | Purpose |
|------|---------|
| `.github/release-signers` | Allowed signers file (public key) |
| `docs/security/release-signing.md` | Signing policy |
| `docs/release/v0.1.1-release-recovery-plan.md` | Recovery plan |
| `docs/release/v0.1.1-release-candidate.md` | This document |
| `CHANGELOG.md` | v0.1.1 entry |
| `scripts/validate_signing_config.py` | CI policy validation |

### Documentation updates

- `SECURITY.md`: Added release verification section
- `CONTRIBUTING.md`: Added release tag section

### No application changes

Zero changes to: package code, plugin code, migrations, tests, skills, tools, hooks, services, storage, policy engine, configuration, or commands.

## Signing backend

| Attribute | Value |
|-----------|-------|
| Backend | SSH (Ed25519) |
| Git requirement | 2.34+ |
| Key type | ssh-ed25519 |
| Fingerprint | SHA256:dH1TlK+IE0sRzSrdlhVMwk/sPqJRaeSNO825IlKsBCY |
| Signer identity | Tony Simons <asimons81@gmail.com> |
| Allowed signers file | `.github/release-signers` |
| Public key | `AAAAC3NzaC1lZDI1NTE5AAAAIFa2lFHXvOxh+E13Z/sQWvm4lIl9fdxcAX3cqB5/2dJQ` |

## Verification commands

```bash
# Configure
git config gpg.format ssh
git config gpg.ssh.allowedSignersFile .github/release-signers

# Verify
git tag -v v0.1.1
```

## Test results

See Phase 7 verification below. Expected baseline: 217 tests passing.

## Release risks

| Risk | Mitigation |
|------|------------|
| Tag signing fails locally | SSH key exists and is verified working |
| `git tag -v` fails in CI | Allowed-signers file is committed; trusted signer identity matches |
| PyPI Trusted Publishing not configured | Verified during v0.1.0 publication; publisher is active |
| Accidental v0.2.0 code inclusion | Branch is based on `main` at `0a0db26`, not any dev branch |

## Expected artifact names

- `hardproof-0.1.1-py3-none-any.whl`
- `hardproof-0.1.1.tar.gz`
- `hardproof.cdx.json`
- `SHA256SUMS`

## PyPI Trusted Publisher configuration

| Field | Value |
|-------|-------|
| PyPI project | hardproof |
| GitHub owner | asimons81 |
| GitHub repository | hardproof |
| Workflow | release.yml |
| Environment | pypi |

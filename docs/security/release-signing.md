# Hardproof Release Signing

## Policy

Every public Hardproof release tag MUST be cryptographically signed. Unsigned tags are rejected by the release workflow. Published tags are never moved, deleted, or force-pushed.

## Signing backend

Hardproof uses **SSH signing** (Ed25519) via Git's native `gpg.format = ssh` support (requires Git 2.34+).

## Approved signers

Current approved release signers:

| Identity | Key type | Fingerprint |
|----------|----------|-------------|
| asimons81@gmail.com (Tony Simons) | ssh-ed25519 | SHA256:dH1TlK+IE0sRzSrdlhVMwk/sPqJRaeSNO825IlKsBCY |

The public key is stored in `.github/release-signers` in Git allowed-signers format.

## Verifying a tag locally

```bash
git config gpg.format ssh
git config gpg.ssh.allowedSignersFile .github/release-signers
git tag -v v0.1.1
```

Expected output includes `Good "git" signature for asimons81@gmail.com with ED25519 key`.

## Why published tags are never moved

Moving a published tag breaks every downstream reference. Checksums, provenance attestations, PyPI hashes, and cached clones all depend on the tag resolving to the same commit forever. If a release has an error, cut a new patch version -- never replace the old tag.

## Signer rotation

To add a new release signer:

1. The existing approved signer verifies the new public key out of band
2. Add the new key to `.github/release-signers`
3. Add the key to the signer's GitHub account as a signing key
4. Open a PR with the allowed-signers update
5. Merge after review by an existing maintainer
6. The new signer can now sign release tags

## Key rotation

To rotate a signer's key:

1. Generate a new key pair
2. Add the new public key to `.github/release-signers`
3. Open a PR
4. After merge, sign a test tag with the new key and verify in CI
5. Remove the old key from `.github/release-signers`
6. Remove the old key from GitHub account signing keys

Old keys remain valid for verifying historical tags even after removal from the allowed-signers file. Keep the old allowed-signers entry in an archived reference for verification purposes.

## Lost-key procedure

If a signer loses their private key but has a backup: restore from backup, verify with the existing public key, and continue.

If a signer loses their private key with no backup:

1. Generate a new key pair
2. Add the new public key to `.github/release-signers`
3. Remove the old key from `.github/release-signers`
4. The old key can no longer sign new releases
5. Historical tags signed by the old key remain verifiable (the public key must be kept in an archive for verification)

## Compromised-key procedure

If a signing key is compromised:

1. IMMEDIATELY remove the public key from `.github/release-signers`
2. Remove the key from all GitHub account signing key registrations
3. Audit all tags signed by the compromised key
4. Verify that no unauthorized tags were created
5. Generate a new key pair
6. Add the new public key to `.github/release-signers`
7. Issue a security advisory if unauthorized releases are found
8. All previously-signed tags remain valid if they can be verified against known-good commits

## CI enforcement

The release workflow (`.github/workflows/release.yml`) enforces:

1. SSH signing backend configured before verification
2. `git tag -v` passes against `.github/release-signers`
3. The tagged commit is an ancestor of `origin/main`
4. Tag version matches `pyproject.toml`, `plugin.yaml`, and `hardproof.__version__`
5. Publishing uses PyPI Trusted Publishing (OIDC), never a static token
6. The workflow triggers only on `v*` tags

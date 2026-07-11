# Changelog

All notable changes to Hardproof are documented here.

## [0.2.0] - 2026-07-11

### Added

- Gatehouse policy traces, strict project rules, scoped human waivers, configurable state-failure
  behavior, stable approval keys, and deterministic advisory risk suggestions.
- Bounded monotonic stage-graph configuration with deterministic diagnostics.
- Versioned data-only Python, Node, Rust, and Go policy packs.
- Configuration explanation, database status/dry-run migration, and richer doctor diagnostics.

### Changed

- Released v0.2.0 Gatehouse on GitHub and PyPI with schema migration 002.

## [0.1.1] - 2026-07-11

### Release infrastructure

- **Release signing**: Tags are now cryptographically signed using SSH (Ed25519). The release workflow verifies signatures against `.github/release-signers` before publishing.
- **First PyPI release**: v0.1.1 is the first Hardproof version published to PyPI via Trusted Publishing.

### Changes

- Bump version from 0.1.0 to 0.1.1 (pyproject.toml, plugin.yaml, hardproof/__init__.py)
- Add SSH signing verification to release workflow (`.github/workflows/release.yml`)
- Add `.github/release-signers` with approved public signing key
- Add `docs/security/release-signing.md` with signing policy
- Update `SECURITY.md` with release verification instructions
- Update `CONTRIBUTING.md` with tag-signing requirements

### Application behavior

No application behavior changes. v0.1.1 is identical to v0.1.0 in all runtime code, tests, migrations, skills, tools, and hooks.

### Notes

- v0.1.0 remains available on GitHub as the original public alpha
- PyPI distribution begins at v0.1.1
- The v0.1.0 tag is unsigned by design and will not be retroactively signed

## [0.1.0] - 2026-07-11

Initial public alpha release. See the [v0.1.0 GitHub release](https://github.com/asimons81/hardproof/releases/tag/v0.1.0).

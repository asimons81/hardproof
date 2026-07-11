# Hardproof v0.2.0 Release Candidate

Status: Complete locally; not tagged or published

The candidate contains all Gatehouse outcomes and no Workcells functionality. Local evidence:
369 tests pass; total coverage exceeds 90%; the critical aggregate exceeds 95% and each named
policy/transition/migration/evidence module meets its release threshold; Ruff, strict mypy,
build, Twine, wheel/sdist installs, public-v0.1.1 upgrade, migration integrity, policy packs, stage
graphs, six-tool contracts, command registration, package data, secret/local-only contracts, and
the focused security review pass. The dependency-only audit reports no known vulnerabilities after
using current packaging tools; auditing the unrelated developer/Hermes environment is not release
evidence.

Artifacts are `hardproof-0.2.0-py3-none-any.whl`, `hardproof-0.2.0.tar.gz`,
`hardproof.cdx.json`, and `SHA256SUMS`. Independent Linux/macOS CI and publication authority remain
external gates. The SBOM is reproducible and scoped to the runtime dependency manifest.

## Artifact SHA-256

- `hardproof-0.2.0-py3-none-any.whl`: `b812a2bdbf6b11c784852921a973683eb913658966a0c9030fcdb5c139048f4c`
- `hardproof-0.2.0.tar.gz`: `acaae9bfc33e43b25accfdb53bbd602905afadd33f07077c7752897c4258b56c`
- `hardproof.cdx.json`: `67e8b0d44f819b424cb7cc9e76acb52f18abd8be2e1d11824f0ce0951201344e`

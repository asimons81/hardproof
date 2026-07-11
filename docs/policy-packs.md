# Built-in Policy Packs

Hardproof v0.2.0 includes versioned, data-only packs for Python, Node, Rust, and Go. Packs
classify known test, lint, type-check, build, generate, install, and publish commands. They never
execute commands, import project code, fetch remote data, or evaluate configuration as code.

Select packs explicitly under `policy.packs`, or leave the list empty for deterministic local
detection from files such as `pyproject.toml`, `package.json`, `Cargo.toml`, and `go.mod`.
`hermes hardproof config explain` reports active pack keys, version `1.0`, and matched indicators.

Precedence remains immutable safety, project deny, project approval, core stage policy, project
allow, selected pack, and default. Publication and installation commands remain elevated; project
configuration cannot weaken immutable force-push or completion/evidence requirements. Command
chains and `env`, shell, PowerShell, and `cmd` wrappers are normalized before classification, and
common Windows `.exe` command forms are recognized.

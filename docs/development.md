# Development

Crucible requires Python 3.11 or newer and PyYAML 6.x. Runtime code otherwise favors the standard library.

Create an isolated environment, install `.[dev]`, and run the checks in `docs/testing.md`. Keep Windows path behavior native; do not assume POSIX separators, executable names, or shell semantics. Use temporary repositories for mutation and Git tests.

Add numbered forward-only SQL migrations. Never edit a released migration. Update package, plugin, and import versions together. Public API, policy, persistence, dependency, and compatibility changes require ADR review.

Do not add telemetry, hidden network traffic, hosted dependencies, private Hermes access, an ORM, or model-callable human approval creation.

# Decision Ledger

| Date | Decision | Record | Status |
| --- | --- | --- | --- |
| 2026-07-10 | Build as an original standalone Hermes plugin using only public APIs. | `docs/adr/0001-clean-room-implementation.md` | Accepted |
| 2026-07-10 | Pass bare skill names to `register_skill`; Hermes supplies the plugin namespace. | `docs/adr/0002-standalone-hermes-plugin.md` | Accepted |
| 2026-07-11 | Persist each project's protocol state in migrated SQLite with short-lived WAL connections. | `docs/adr/0003-project-local-sqlite.md` | Accepted |
| 2026-07-11 | Enforce stage-aware mutation with deterministic classification and Hermes approval escalation. | `docs/adr/0005-stage-aware-tool-policy.md` | Accepted |
| 2026-07-11 | Bind verification to HEAD, tracked diff bytes, and ignored-aware untracked content. | `docs/adr/0004-evidence-freshness.md` | Accepted |
| 2026-07-11 | Use one evaluator with ordered immutable traces, frozen rule keys, and a caller-supplied clock. | `docs/adr/0006-ordered-policy-traces.md` | Accepted |

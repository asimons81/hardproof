# Decision Ledger

| Date | Decision | Record | Status |
| --- | --- | --- | --- |
| 2026-07-10 | Build as an original standalone Hermes plugin using only public APIs. | `docs/adr/0001-clean-room-implementation.md` | Accepted |
| 2026-07-10 | Pass bare skill names to `register_skill`; Hermes supplies the plugin namespace. | `docs/adr/0002-standalone-hermes-plugin.md` | Accepted |
| 2026-07-11 | Persist each project's protocol state in migrated SQLite with short-lived WAL connections. | `docs/adr/0003-project-local-sqlite.md` | Accepted |

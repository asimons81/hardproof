# Hardproof v0.2.0 Compatibility

The current public `hardproof==0.1.1` wheel was installed from PyPI in a clean environment, created
a schema-v1 database, and was upgraded in place to the local v0.2.0 wheel. Migration 002 applied,
history remained `[1, 2]`, and SQLite integrity returned `ok`. Existing schema-v1 tables are not
rewritten. The six tools, `/hardproof`, `hermes hardproof`, entry point, plugin key, and opt-in model
remain stable. Uninstall does not remove project-local `.hardproof/` state.

Configuration schema v1 is accepted and migrated in memory; existing files are never rewritten
implicitly. Downgrade after schema migration is not claimed safe.

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from hardproof.storage.database import Database, DatabaseCorruptionError
from hardproof.storage.migrations import MigrationError, apply_migration_sql, migrate


def test_database_enables_required_pragmas(tmp_path: Path) -> None:
    database = Database(tmp_path / "state" / "hardproof.db")
    with database.connect() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000


def test_migration_is_idempotent_and_reopenable(tmp_path: Path) -> None:
    database = Database(tmp_path / "hardproof.db")
    assert migrate(database) == (1,)
    assert migrate(database) == ()
    with database.connect() as connection:
        assert [row[0] for row in connection.execute(
            "SELECT version FROM schema_migrations"
        ).fetchall()] == [1]


def test_interrupted_migration_rolls_back(tmp_path: Path) -> None:
    database = Database(tmp_path / "hardproof.db")
    with database.connect() as connection:
        with pytest.raises(sqlite3.OperationalError):
            apply_migration_sql(
                connection,
                99,
                "CREATE TABLE partial(value TEXT); INVALID SQL;",
            )
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'partial'"
        ).fetchone() is None


def test_incomplete_migration_is_rejected_before_execution(tmp_path: Path) -> None:
    database = Database(tmp_path / "hardproof.db")
    with database.connect() as connection, pytest.raises(
        MigrationError, match="incomplete SQL statement"
    ):
        apply_migration_sql(connection, 99, "CREATE TABLE unfinished(value TEXT)")
    with database.connect() as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'unfinished'"
        ).fetchone() is None


def test_unknown_newer_schema_refuses_write(tmp_path: Path) -> None:
    database = Database(tmp_path / "hardproof.db")
    migrate(database)
    with database.connect() as connection, connection:
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (999, '2026-01-01T00:00:00Z')"
        )
    with pytest.raises(MigrationError, match="newer schema"):
        migrate(database)


def test_foreign_keys_are_enforced(tmp_path: Path) -> None:
    database = Database(tmp_path / "hardproof.db")
    migrate(database)
    with database.connect() as connection, pytest.raises(sqlite3.IntegrityError), connection:
        connection.execute(
            "INSERT INTO events(run_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
            ("missing", "test", "{}", "2026-01-01T00:00:00Z"),
        )


def test_corrupt_database_is_never_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "hardproof.db"
    original = b"not a sqlite database"
    path.write_bytes(original)
    with pytest.raises(DatabaseCorruptionError, match="preserved"):
        with Database(path).connect():
            pass
    assert path.read_bytes() == original

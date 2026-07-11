"""Forward-only transactional schema migration runner."""

from __future__ import annotations

import sqlite3
from importlib import resources

from hardproof.domain.models import utc_now
from hardproof.storage.database import Database


LATEST_SCHEMA_VERSION = 1


class MigrationError(RuntimeError):
    """The database schema is unsupported or failed to migrate."""


def _statements(sql: str) -> tuple[str, ...]:
    statements: list[str] = []
    buffer = ""
    for character in sql:
        buffer += character
        if sqlite3.complete_statement(buffer):
            if buffer.strip():
                statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        raise MigrationError("migration ends with an incomplete SQL statement")
    return tuple(statements)


def apply_migration_sql(connection: sqlite3.Connection, version: int, sql: str) -> None:
    """Apply one migration atomically, including its ledger record."""
    connection.execute("BEGIN IMMEDIATE")
    try:
        for statement in _statements(sql):
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (version, utc_now()),
        )
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()


def _load(version: int) -> str:
    name = f"{version:03d}_initial.sql"
    return resources.files("hardproof.migrations").joinpath(name).read_text(encoding="utf-8")


def migrate(database: Database) -> tuple[int, ...]:
    """Apply every missing known migration and return applied versions."""
    with database.connect() as connection:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        current = 0
        if table_exists:
            row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
            current = int(row[0] or 0)
        if current > LATEST_SCHEMA_VERSION:
            raise MigrationError(
                f"database uses newer schema {current}; this build supports {LATEST_SCHEMA_VERSION}"
            )
        applied: list[int] = []
        for version in range(current + 1, LATEST_SCHEMA_VERSION + 1):
            apply_migration_sql(connection, version, _load(version))
            applied.append(version)
        return tuple(applied)

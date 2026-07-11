"""Short-lived, configured SQLite connections."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class DatabaseCorruptionError(RuntimeError):
    """The existing database cannot be read safely and was left untouched."""


class Database:
    """Connection factory; raw connections are never shared across operations."""

    def __init__(self, path: Path | str, *, busy_timeout_ms: int = 5_000) -> None:
        self.path = Path(path)
        self.busy_timeout_ms = busy_timeout_ms

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.path,
            timeout=self.busy_timeout_ms / 1_000,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms:d}")
            connection.execute("PRAGMA journal_mode = WAL")
            quick_check = connection.execute("PRAGMA quick_check").fetchone()
        except sqlite3.DatabaseError as exc:
            connection.close()
            raise DatabaseCorruptionError(
                f"database at {self.path} is unreadable; original file was preserved"
            ) from exc
        if quick_check is None or quick_check[0] != "ok":
            connection.close()
            raise DatabaseCorruptionError(
                f"database integrity check failed at {self.path}; no repair was attempted"
            )
        try:
            yield connection
        finally:
            connection.close()

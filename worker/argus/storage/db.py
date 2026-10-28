"""The SQLite database: WAL mode, one guarded writer connection, a fresh read-only connection per read."""

from __future__ import annotations

import re
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

MIGRATION_NAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")


def migrate(conn: sqlite3.Connection) -> int:
    """Apply migrations/NNN_*.sql newer than PRAGMA user_version, in order; return the resulting version."""
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    folder = resources.files("argus.storage") / "migrations"
    pending = sorted(
        (int(match.group(1)), entry)
        for entry in folder.iterdir()
        if (match := MIGRATION_NAME.match(entry.name)) and int(match.group(1)) > current
    )
    for number, entry in pending:
        conn.executescript(entry.read_text(encoding="utf-8"))
        conn.execute(f"PRAGMA user_version = {number}")
        current = number
    return current


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._writer = sqlite3.connect(self.path, check_same_thread=False)
        self._writer.row_factory = sqlite3.Row
        self._writer.execute("PRAGMA journal_mode=WAL")
        self._writer.execute("PRAGMA foreign_keys=ON")
        self._writer.execute("PRAGMA busy_timeout=5000")
        migrate(self._writer)

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        """The single writer: commits when the block ends, rolls back if it raises."""
        with self._lock:
            try:
                yield self._writer
                self._writer.commit()
            except BaseException:
                self._writer.rollback()
                raise

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        """A new read-only connection; in WAL mode it never waits for the writer."""
        conn = sqlite3.connect(f"{self.path.resolve().as_uri()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def close(self) -> None:
        with self._lock:
            self._writer.close()

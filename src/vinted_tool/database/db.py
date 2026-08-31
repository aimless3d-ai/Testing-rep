"""SQLite connection handling and migrations."""
from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

from vinted_tool.app.paths import db_path

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1
_SCHEMA_FILE = Path(__file__).with_name("schema.sql")


class Database:
    """Thin wrapper around :mod:`sqlite3` with a per-thread connection."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else db_path()
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._shared: sqlite3.Connection | None = None
        if str(self.path) == ":memory:":
            self._shared = self._new_connection()
        self.migrate()

    def _new_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), timeout=15, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    @property
    def conn(self) -> sqlite3.Connection:
        if self._shared is not None:
            return self._shared
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._new_connection()
            self._local.conn = conn
        return conn

    def migrate(self) -> None:
        conn = self.conn
        with conn:
            conn.executescript(_SCHEMA_FILE.read_text(encoding="utf-8"))
            row = conn.execute("SELECT version FROM schema_version").fetchone()
            if row is None:
                conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
            elif row["version"] < SCHEMA_VERSION:
                # Future migrations are applied here step by step.
                conn.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
        log.debug("Database ready at %s (schema v%s)", self.path, SCHEMA_VERSION)

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.conn:
            return self.conn.execute(sql, params)

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return list(self.conn.execute(sql, params).fetchall())

    def query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self.conn.execute(sql, params).fetchone()

    def close(self) -> None:
        for conn in filter(None, [self._shared, getattr(self._local, "conn", None)]):
            try:
                conn.close()
            except sqlite3.Error:  # pragma: no cover - best effort
                pass
        self._shared = None
        self._local = threading.local()

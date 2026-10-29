"""Durable SQLite storage for the Blind_Log QSO journal and form draft."""
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

QSO_FIELDS = (
    "call", "name", "city", "qth", "band", "mode", "freq",
    "rst_received", "rst_sent", "comment", "datetime",
)


class JournalDatabase:
    """SQLite-backed journal. Every write is committed in a transaction."""

    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._session() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS qsos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    position INTEGER NOT NULL UNIQUE,
                    call TEXT NOT NULL DEFAULT '',
                    name TEXT NOT NULL DEFAULT '',
                    city TEXT NOT NULL DEFAULT '',
                    qth TEXT NOT NULL DEFAULT '',
                    band TEXT NOT NULL DEFAULT '',
                    mode TEXT NOT NULL DEFAULT '',
                    freq TEXT NOT NULL DEFAULT '',
                    rst_received TEXT NOT NULL DEFAULT '',
                    rst_sent TEXT NOT NULL DEFAULT '',
                    comment TEXT NOT NULL DEFAULT '',
                    datetime TEXT NOT NULL DEFAULT ''
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_qsos_call_datetime ON qsos(call, datetime)")

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @contextmanager
    def _session(self):
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def get_all(self):
        with self._session() as connection:
            rows = connection.execute(
                "SELECT " + ", ".join(QSO_FIELDS) + " FROM qsos ORDER BY position"
            ).fetchall()
        return [{field: row[field] or "" for field in QSO_FIELDS} for row in rows]

    def replace_all(self, qsos):
        """Replace the journal atomically; a failed write preserves the old journal."""
        rows = [
            tuple(str(qso.get(field, "") or "") for field in QSO_FIELDS)
            for qso in qsos
        ]
        columns = ", ".join(QSO_FIELDS)
        placeholders = ", ".join("?" for _ in QSO_FIELDS)
        with self._session() as connection:
            connection.execute("DELETE FROM qsos")
            connection.executemany(
                f"INSERT INTO qsos (position, {columns}) VALUES (?, {placeholders})",
                [(position, *row) for position, row in enumerate(rows)],
            )

    def save_draft(self, path, draft):
        """Atomically replace the draft JSON so a crash cannot leave a partial file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(draft, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise

    def load_draft(self, path):
        path = Path(path)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        return data if isinstance(data, dict) and isinstance(data.get("fields"), dict) else None

    def clear_draft(self, path):
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass

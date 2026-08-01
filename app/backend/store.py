from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class Store:
    def __init__(self, path: Path):
        self.path = path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS transcripts (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    engine TEXT NOT NULL,
                    archived INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(transcripts)").fetchall()
            }
            if "archived" not in columns:
                connection.execute(
                    "ALTER TABLE transcripts ADD COLUMN archived INTEGER NOT NULL DEFAULT 0"
                )
            connection.commit()

    def add_transcript(self, text: str, duration_ms: int, engine: str) -> dict[str, Any]:
        item = {
            "id": str(uuid4()),
            "text": text,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": max(0, duration_ms),
            "engine": engine,
            "archived": False,
        }
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO transcripts(id, text, created_at, duration_ms, engine, archived)
                VALUES (:id, :text, :created_at, :duration_ms, :engine, :archived)
                """,
                item,
            )
            connection.commit()
        return item

    def list_transcripts(self, limit: int = 50, archived: bool = False) -> list[dict[str, Any]]:
        return self.list_transcripts_page(limit=limit, archived=archived)

    def list_transcripts_page(self, limit: int = 50, offset: int = 0, archived: bool = False) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT * FROM transcripts
                WHERE archived = ?
                ORDER BY created_at DESC
                LIMIT ?
                OFFSET ?
                """,
                (archived, limit, max(0, offset)),
            ).fetchall()
        return [self._transcript_dict(row) for row in rows]

    def count_transcripts(self, archived: bool = False) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM transcripts WHERE archived = ?", (archived,)
            ).fetchone()
        return int(row["count"])

    @staticmethod
    def _transcript_dict(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["archived"] = bool(item["archived"])
        return item

    def archive_transcript(self, transcript_id: str, archived: bool = True) -> bool:
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "UPDATE transcripts SET archived = ? WHERE id = ?",
                (archived, transcript_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def archive_transcripts(self, transcript_ids: list[str], archived: bool = True) -> list[str]:
        """Set archive state for the supplied transcript ids and return matches."""
        ids = list(dict.fromkeys(transcript_ids))
        if not ids:
            return []
        placeholders = ", ".join("?" for _ in ids)
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"SELECT id FROM transcripts WHERE id IN ({placeholders})", ids
            ).fetchall()
            matched = [row["id"] for row in rows]
            if matched:
                matched_placeholders = ", ".join("?" for _ in matched)
                connection.execute(
                    f"UPDATE transcripts SET archived = ? WHERE id IN ({matched_placeholders})",
                    [archived, *matched],
                )
                connection.commit()
        return matched

    def update_transcript_text(self, transcript_id: str, text: str) -> dict[str, Any] | None:
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Transcript text cannot be empty")

        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "UPDATE transcripts SET text = ? WHERE id = ?",
                (cleaned_text, transcript_id),
            )
            if cursor.rowcount == 0:
                connection.rollback()
                return None
            row = connection.execute(
                "SELECT * FROM transcripts WHERE id = ?",
                (transcript_id,),
            ).fetchone()
            connection.commit()

        return self._transcript_dict(row)

    def delete_transcript(self, transcript_id: str) -> bool:
        with closing(self._connect()) as connection:
            cursor = connection.execute("DELETE FROM transcripts WHERE id = ?", (transcript_id,))
            connection.commit()
            return cursor.rowcount > 0

    def delete_transcripts(self, transcript_ids: list[str]) -> list[str]:
        """Delete the supplied transcript ids and return the ids that existed."""
        ids = list(dict.fromkeys(transcript_ids))
        if not ids:
            return []
        placeholders = ", ".join("?" for _ in ids)
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"SELECT id FROM transcripts WHERE id IN ({placeholders})", ids
            ).fetchall()
            matched = [row["id"] for row in rows]
            if matched:
                matched_placeholders = ", ".join("?" for _ in matched)
                connection.execute(
                    f"DELETE FROM transcripts WHERE id IN ({matched_placeholders})", matched
                )
                connection.commit()
        return matched

    def clear_transcripts(self) -> int:
        with closing(self._connect()) as connection:
            cursor = connection.execute("DELETE FROM transcripts")
            connection.commit()
            return cursor.rowcount

    def settings(self) -> dict[str, Any]:
        values: dict[str, Any] = {
            "theme": "dark",
            "skin": "graphite",
            "https_only": False,
            "history_page_size": 25,
        }
        with closing(self._connect()) as connection:
            rows = connection.execute("SELECT key, value FROM settings").fetchall()
        for row in rows:
            try:
                values[row["key"]] = json.loads(row["value"])
            except json.JSONDecodeError:
                values[row["key"]] = row["value"]
        return values

    def update_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            for key, value in patch.items():
                connection.execute(
                    "INSERT INTO settings(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, json.dumps(value)),
                )
            connection.commit()
        return self.settings()

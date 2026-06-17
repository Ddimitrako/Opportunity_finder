from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from app.config import Settings
from app.models import BookmarkListResponse, BookmarkRecord, BookmarkStatusResponse, Opportunity


class BookmarkService:
    def __init__(self, settings: Settings):
        self.db_path = _resolve_db_path(Path(settings.bookmark_db_path))
        self._init_db()

    def list_bookmarks(self) -> BookmarkListResponse:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, opportunity_json, created_at, updated_at
                FROM bookmarks
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return BookmarkListResponse(bookmarks=[_row_to_bookmark(row) for row in rows])

    def status(self) -> BookmarkStatusResponse:
        with closing(self._connect()) as connection:
            count = int(connection.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0])
        return BookmarkStatusResponse(
            db_path=str(self.db_path),
            exists=self.db_path.exists(),
            bookmark_count=count,
        )

    def upsert_bookmark(self, opportunity: Opportunity) -> BookmarkRecord:
        now = datetime.utcnow().isoformat()
        payload = json.dumps(opportunity.model_dump(mode="json"), ensure_ascii=False)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO bookmarks (id, opportunity_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        opportunity_json = excluded.opportunity_json,
                        updated_at = excluded.updated_at
                    """,
                    (opportunity.id, payload, now, now),
                )
                row = connection.execute(
                    """
                    SELECT id, opportunity_json, created_at, updated_at
                    FROM bookmarks
                    WHERE id = ?
                    """,
                    (opportunity.id,),
                ).fetchone()
        return _row_to_bookmark(row)

    def delete_bookmark(self, bookmark_id: str) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS bookmarks (
                        id TEXT PRIMARY KEY,
                        opportunity_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )


def _row_to_bookmark(row: sqlite3.Row) -> BookmarkRecord:
    return BookmarkRecord(
        id=str(row["id"]),
        opportunity=Opportunity.model_validate(json.loads(str(row["opportunity_json"]))),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        updated_at=datetime.fromisoformat(str(row["updated_at"])),
    )


def _resolve_db_path(configured_path: Path) -> Path:
    if configured_path.is_absolute():
        return configured_path

    backend_dir = Path(__file__).resolve().parents[2]
    stable_path = backend_dir / configured_path
    cwd_path = Path.cwd() / configured_path

    if cwd_path.exists() and not stable_path.exists():
        stable_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cwd_path, stable_path)

    return stable_path

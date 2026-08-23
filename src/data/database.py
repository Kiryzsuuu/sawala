"""SQLite persistence layer.

Two tables:
  sessions      - one row per monitoring session
  snapshots     - one row per (session, participant, capture-interval) tick,
                  so the full timeline can be reconstructed / exported.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from src.data.models import ParticipantStatus
from src.utils.config import CONFIG, resolve_path
from src.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    participant_id TEXT NOT NULL,
    participant_name TEXT,
    timestamp TEXT NOT NULL,
    oncam INTEGER,
    oncam_duration_seconds REAL,
    is_real_person INTEGER,
    liveness_score REAL,
    avatar_flag INTEGER,
    holding_phone INTEGER,
    phone_confidence REAL,
    fatigue_detected INTEGER,
    ear_value REAL,
    fatigue_duration_seconds REAL,
    smiling INTEGER,
    smile_confidence REAL,
    dominant_emotion TEXT,
    flags TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_session ON snapshots(session_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_participant ON snapshots(session_id, participant_id);
"""


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = resolve_path(path or CONFIG.database.path)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        logger.info("Database ready at %s", self.path)

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        finally:
            cur.close()

    def start_session(self) -> str:
        session_id = str(uuid.uuid4())
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (session_id, started_at, active) VALUES (?, ?, 1)",
                (session_id, datetime.now(timezone.utc).isoformat()),
            )
        logger.info("Session started: %s", session_id)
        return session_id

    def stop_session(self, session_id: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE sessions SET active = 0, ended_at = ? WHERE session_id = ?",
                (datetime.now(timezone.utc).isoformat(), session_id),
            )
        logger.info("Session stopped: %s", session_id)

    def get_active_session(self) -> sqlite3.Row | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM sessions WHERE active = 1 ORDER BY started_at DESC LIMIT 1")
            return cur.fetchone()

    def insert_snapshot(self, session_id: str, status: ParticipantStatus) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO snapshots (
                    session_id, participant_id, participant_name, timestamp,
                    oncam, oncam_duration_seconds, is_real_person, liveness_score,
                    avatar_flag, holding_phone, phone_confidence, fatigue_detected,
                    ear_value, fatigue_duration_seconds, smiling, smile_confidence,
                    dominant_emotion, flags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    status.id,
                    status.name,
                    status.last_seen or datetime.now(timezone.utc).isoformat(),
                    int(status.oncam),
                    status.oncam_duration_seconds,
                    int(bool(status.is_real_person)),
                    status.liveness_score,
                    int(status.avatar_flag),
                    int(status.holding_phone),
                    status.phone_confidence,
                    int(status.fatigue_detected),
                    status.ear_value,
                    status.fatigue_duration_seconds,
                    int(status.smiling),
                    status.smile_confidence,
                    status.dominant_emotion,
                    json.dumps(status.flags),
                ),
            )

    def get_participants(self, session_id: str) -> list[dict]:
        """Latest known status per participant for a session."""
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT s.* FROM snapshots s
                INNER JOIN (
                    SELECT participant_id, MAX(id) AS max_id
                    FROM snapshots WHERE session_id = ?
                    GROUP BY participant_id
                ) latest ON s.participant_id = latest.participant_id AND s.id = latest.max_id
                """,
                (session_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_participant_history(self, session_id: str, participant_id: str) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM snapshots WHERE session_id = ? AND participant_id = ? ORDER BY id ASC",
                (session_id, participant_id),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_session_summary(self, session_id: str) -> list[dict]:
        """Aggregated per-participant stats for CSV/JSON export."""
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT
                    participant_id,
                    participant_name,
                    MAX(oncam_duration_seconds) AS oncam_duration_sec,
                    MAX(fatigue_duration_seconds) AS fatigue_duration_sec,
                    SUM(CASE WHEN holding_phone = 1 THEN 1 ELSE 0 END) AS phone_detected_count,
                    AVG(smile_confidence) AS avg_smile_score,
                    MAX(avatar_flag) AS avatar_detected,
                    COUNT(*) AS total_snapshots
                FROM snapshots
                WHERE session_id = ?
                GROUP BY participant_id, participant_name
                """,
                (session_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()

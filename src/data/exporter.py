"""CSV / JSON export for session summaries (section 9.2 format)."""
from __future__ import annotations

import csv
import io
import json

from src.data.database import Database


def _row_to_csv_dict(row: dict) -> dict:
    total = max(row.get("total_snapshots", 0) or 0, 1)
    oncam_sec = row.get("oncam_duration_sec") or 0.0
    return {
        "participant_id": row["participant_id"],
        "name": row["participant_name"],
        "oncam_duration_sec": round(oncam_sec, 1),
        "oncam_percent": f"{min(100.0, oncam_sec / (total * 3) * 100):.1f}%",
        "avatar_detected": bool(row.get("avatar_detected")),
        "phone_detected_count": row.get("phone_detected_count") or 0,
        "fatigue_duration_sec": round(row.get("fatigue_duration_sec") or 0.0, 1),
        "avg_smile_score": round(row.get("avg_smile_score") or 0.0, 2),
    }


def export_csv(db: Database, session_id: str) -> str:
    rows = [_row_to_csv_dict(r) for r in db.get_session_summary(session_id)]
    buf = io.StringIO()
    fieldnames = [
        "participant_id", "name", "oncam_duration_sec", "oncam_percent",
        "avatar_detected", "phone_detected_count", "fatigue_duration_sec", "avg_smile_score",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def export_json(db: Database, session_id: str) -> str:
    rows = [_row_to_csv_dict(r) for r in db.get_session_summary(session_id)]
    return json.dumps({"session_id": session_id, "participants": rows}, indent=2, ensure_ascii=False)

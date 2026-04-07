import sqlite3
import threading
import time
from typing import Dict, List, Optional

from multimodal.models import FusedEvent


class EventDatabase:
    """SQLite-backed event store indexed for timestamp, type, and confidence."""

    def __init__(self, db_path: str = "events.db") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    confidence REAL NOT NULL,
                    description TEXT NOT NULL,
                    signals_json TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_time ON events(start_time)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_events_conf ON events(confidence)")
            self._conn.commit()

    def add_event(self, event: FusedEvent) -> None:
        import json

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO events(event_type, start_time, end_time, confidence, description, signals_json)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_type,
                    event.start_time,
                    event.end_time,
                    event.confidence,
                    event.description,
                    json.dumps(event.contributing_signals),
                ),
            )
            self._conn.commit()

    def query_events(
        self,
        event_type: Optional[str] = None,
        min_confidence: float = 0.0,
        since_seconds: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict]:
        clauses = ["confidence >= ?"]
        params = [min_confidence]

        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)

        if since_seconds is not None:
            clauses.append("start_time >= ?")
            params.append(time.time() - since_seconds)

        where_sql = " AND ".join(clauses)
        sql = f"""
            SELECT event_type, start_time, end_time, confidence, description, signals_json
            FROM events
            WHERE {where_sql}
            ORDER BY start_time DESC
            LIMIT ?
        """
        params.append(limit)

        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "event_type": row["event_type"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "confidence": row["confidence"],
                    "description": row["description"],
                    "signals_json": row["signals_json"],
                }
            )
        return results

    def close(self) -> None:
        with self._lock:
            self._conn.close()

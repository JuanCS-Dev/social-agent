from typing import Optional, Any
import json
import os
import sqlite3
from datetime import datetime, timezone
from src.core.config import settings
from src.core.logger import log


class Storage:
    def __init__(self):
        # Extremely simple MVP extraction
        db_url = settings.database_url
        if db_url.startswith("sqlite+aiosqlite:///"):
            self.db_path = db_url.replace("sqlite+aiosqlite:///", "", 1)
        elif db_url.startswith("sqlite:///"):
            self.db_path = db_url.replace("sqlite:///", "", 1)
        else:
            self.db_path = db_url
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    async def init_db(self):
        """Initializes the SQLite tables for idempotency and events."""
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS idempotency (
                    key TEXT PRIMARY KEY,
                    platform TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT,
                    payload TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS dlq (
                    id TEXT PRIMARY KEY,
                    event_type TEXT,
                    payload TEXT,
                    error_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    platform TEXT,
                    action_type TEXT,
                    ok INTEGER,
                    policy_decision_id TEXT,
                    idempotency_key TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS trend_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    platform TEXT,
                    intent TEXT,
                    urgency TEXT,
                    language TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS daily_reflections (
                    reflection_day TEXT PRIMARY KEY,
                    payload TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS operator_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    platform TEXT,
                    action_type TEXT,
                    thread_ref TEXT,
                    content TEXT,
                    options TEXT,
                    status TEXT DEFAULT 'pending',
                    external_id TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.commit()
            log.info(f"Database initialized successfully at {self.db_path}.")

    async def check_and_set_idempotency(self, key: str, platform: str) -> bool:
        """Returns True if the key was saved (new action). False if it already exists."""
        try:
            with sqlite3.connect(self.db_path) as db:
                db.execute("INSERT INTO idempotency (key, platform) VALUES (?, ?)", (key, platform))
                db.commit()
                return True
        except sqlite3.IntegrityError:
            log.warning(f"Idempotency validation failed for key {key} on {platform}.")
            return False

    async def save_event(self, event_id: str, event_type: str, payload: dict[str, Any]):
        """Persists incoming events or webhook payloads."""
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO events (id, event_type, payload) VALUES (?, ?, ?)", (event_id, event_type, json.dumps(payload)))
            db.commit()

    async def save_to_dlq(self, event_id: str, event_type: str, payload: dict[str, Any], error_reason: str):
        """Persists failed events to Dead Letter Queue for later replay."""
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO dlq (id, event_type, payload, error_reason) VALUES (?, ?, ?, ?)", (event_id, event_type, json.dumps(payload), error_reason))
            db.commit()
            log.warning(f"Event {event_id} sent to DLQ. Reason: {error_reason}")

    async def fetch_next_event(self) -> Optional[dict[str, Any]]:
        """Fetches the oldest pending event from the database."""
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute("SELECT id, event_type, payload FROM events ORDER BY created_at ASC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "event_type": row[1], "payload": json.loads(row[2])}
        return None

    async def delete_event(self, event_id: str):
        """Removes a processed event from the queue."""
        with sqlite3.connect(self.db_path) as db:
            db.execute("DELETE FROM events WHERE id = ?", (event_id,))
            db.commit()

    async def save_action_log(
        self,
        event_id: str,
        platform: str,
        action_type: str,
        ok: bool,
        policy_decision_id: str,
        idempotency_key: str,
        error: str | None = None,
    ):
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """
                INSERT INTO action_logs (
                    event_id, platform, action_type, ok, policy_decision_id, idempotency_key, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    platform,
                    action_type,
                    1 if ok else 0,
                    policy_decision_id,
                    idempotency_key,
                    error,
                ),
            )
            db.commit()

    async def save_signal(
        self,
        event_id: str,
        platform: str,
        intent: str,
        urgency: str,
        language: str,
        metadata: dict[str, Any],
    ):
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """
                INSERT INTO trend_signals (
                    event_id, platform, intent, urgency, language, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, platform, intent, urgency, language, json.dumps(metadata)),
            )
            db.commit()

    async def get_recent_signals(self, hours: int = 24) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                """
                SELECT event_id, platform, intent, urgency, language, metadata, created_at
                FROM trend_signals
                WHERE created_at >= datetime('now', ?)
                ORDER BY created_at DESC
                """,
                (f"-{max(1, hours)} hours",),
            )
            rows = cursor.fetchall()

        signals: list[dict[str, Any]] = []
        for row in rows:
            signals.append(
                {
                    "event_id": row[0],
                    "platform": row[1],
                    "intent": row[2],
                    "urgency": row[3],
                    "language": row[4],
                    "metadata": json.loads(row[5]) if row[5] else {},
                    "created_at": row[6],
                }
            )
        return signals

    async def save_daily_reflection(self, payload: dict[str, Any]):
        reflection_day = datetime.now(timezone.utc).date().isoformat()
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """
                INSERT OR REPLACE INTO daily_reflections (reflection_day, payload, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (reflection_day, json.dumps(payload)),
            )
            db.commit()

    async def get_latest_reflection(self) -> Optional[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                """
                SELECT reflection_day, payload, created_at
                FROM daily_reflections
                ORDER BY reflection_day DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()

        if not row:
            return None
        return {
            "reflection_day": row[0],
            "payload": json.loads(row[1]) if row[1] else {},
            "created_at": row[2],
        }

    async def queue_operator_task(
        self,
        event_id: str,
        platform: str,
        action_type: str,
        content: str,
        thread_ref: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> int:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                """
                INSERT INTO operator_tasks (
                    event_id, platform, action_type, thread_ref, content, options, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    event_id,
                    platform,
                    action_type,
                    thread_ref,
                    content,
                    json.dumps(options or {}),
                ),
            )
            db.commit()
            last_id = cursor.lastrowid
            if last_id is None:
                raise RuntimeError("Failed to create operator task: missing row id.")
            return int(last_id)

    async def list_operator_tasks(
        self,
        platform: Optional[str] = "x",
        status: Optional[str] = "pending",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 200))
        where_parts: list[str] = []
        params: list[Any] = []
        if platform:
            where_parts.append("platform = ?")
            params.append(platform)
        if status:
            where_parts.append("status = ?")
            params.append(status)

        where_clause = ""
        if where_parts:
            where_clause = "WHERE " + " AND ".join(where_parts)

        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                f"""
                SELECT id, event_id, platform, action_type, thread_ref, content, options,
                       status, external_id, notes, created_at, updated_at
                FROM operator_tasks
                {where_clause}
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (*params, safe_limit),
            )
            rows = cursor.fetchall()

        tasks: list[dict[str, Any]] = []
        for row in rows:
            tasks.append(
                {
                    "id": int(row[0]),
                    "event_id": row[1],
                    "platform": row[2],
                    "action_type": row[3],
                    "thread_ref": row[4],
                    "content": row[5],
                    "options": json.loads(row[6]) if row[6] else {},
                    "status": row[7],
                    "external_id": row[8],
                    "notes": row[9],
                    "created_at": row[10],
                    "updated_at": row[11],
                }
            )
        return tasks

    async def update_operator_task(
        self,
        task_id: int,
        status: str,
        external_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                """
                UPDATE operator_tasks
                SET status = ?, external_id = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, external_id, notes, int(task_id)),
            )
            db.commit()
            return cursor.rowcount > 0

    async def get_operator_queue_stats(self) -> dict[str, int]:
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(
                """
                SELECT status, COUNT(*)
                FROM operator_tasks
                GROUP BY status
                """
            ).fetchall()

        stats = {
            "pending": 0,
            "done": 0,
            "cancelled": 0,
        }
        for row in rows:
            key = str(row[0] or "").strip().lower()
            if key in stats:
                stats[key] = int(row[1])
        return stats

    async def get_queue_stats(self) -> dict[str, int]:
        with sqlite3.connect(self.db_path) as db:
            pending_events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            dlq_events = db.execute("SELECT COUNT(*) FROM dlq").fetchone()[0]
            actions_last_hour = db.execute("SELECT COUNT(*) FROM action_logs WHERE created_at >= datetime('now', '-1 hour')").fetchone()[0]
            pending_operator_tasks = db.execute("SELECT COUNT(*) FROM operator_tasks WHERE status = 'pending'").fetchone()[0]
        return {
            "pending_events": int(pending_events),
            "dlq_events": int(dlq_events),
            "actions_last_hour": int(actions_last_hour),
            "pending_operator_tasks": int(pending_operator_tasks),
        }


# Singleton instance for simple DI
storage = Storage()

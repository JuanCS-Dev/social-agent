from typing import Optional, Any
import json
import os
import sqlite3
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
            db.execute('''
                CREATE TABLE IF NOT EXISTS idempotency (
                    key TEXT PRIMARY KEY,
                    platform TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            db.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT,
                    payload TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            db.execute('''
                CREATE TABLE IF NOT EXISTS dlq (
                    id TEXT PRIMARY KEY,
                    event_type TEXT,
                    payload TEXT,
                    error_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            db.commit()
            log.info(f"Database initialized successfully at {self.db_path}.")

    async def check_and_set_idempotency(self, key: str, platform: str) -> bool:
        """Returns True if the key was saved (new action). False if it already exists."""
        try:
            with sqlite3.connect(self.db_path) as db:
                db.execute(
                    'INSERT INTO idempotency (key, platform) VALUES (?, ?)', 
                    (key, platform)
                )
                db.commit()
                return True
        except sqlite3.IntegrityError:
            log.warning(f"Idempotency validation failed for key {key} on {platform}.")
            return False
            
    async def save_event(self, event_id: str, event_type: str, payload: dict[str, Any]):
        """Persists incoming events or webhook payloads."""
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                'INSERT INTO events (id, event_type, payload) VALUES (?, ?, ?)',
                (event_id, event_type, json.dumps(payload))
            )
            db.commit()

    async def save_to_dlq(self, event_id: str, event_type: str, payload: dict[str, Any], error_reason: str):
        """Persists failed events to Dead Letter Queue for later replay."""
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                'INSERT INTO dlq (id, event_type, payload, error_reason) VALUES (?, ?, ?, ?)',
                (event_id, event_type, json.dumps(payload), error_reason)
            )
            db.commit()
            log.warning(f"Event {event_id} sent to DLQ. Reason: {error_reason}")

    async def fetch_next_event(self) -> Optional[dict[str, Any]]:
        """Fetches the oldest pending event from the database."""
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute('SELECT id, event_type, payload FROM events ORDER BY created_at ASC LIMIT 1')
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "event_type": row[1],
                    "payload": json.loads(row[2])
                }
        return None

    async def delete_event(self, event_id: str):
        """Removes a processed event from the queue."""
        with sqlite3.connect(self.db_path) as db:
            db.execute('DELETE FROM events WHERE id = ?', (event_id,))
            db.commit()

# Singleton instance for simple DI
storage = Storage()

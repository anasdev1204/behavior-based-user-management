from __future__ import annotations
import sqlite3
from pathlib import Path
import logging

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT UNIQUE NOT NULL PRIMARY KEY,
  context TEXT,             
  duration REAL,
  label TEXT DEFAULT 'unlabeled'
);

CREATE TABLE IF NOT EXISTS keyboard_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  avg_cpm REAL,
  median_cpm REAL,
  avg_hold_time REAL,
  session_id TEXT NOT NULL,
  shortcut_count REAL,
  keystroke_count REAL,
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS mouse_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  avg_dx REAL, 
  avg_dy REAL,
  avg_scroll_distance TEXT,
  avg_click_interval REAL,
  clicks_per_minute REAL,
  session_id TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);
"""

class EventStore:
    """
    Stores events in SQLite database.
    """
    def __init__(self, db_path: str | Path, logger: logging.Logger, label: str):
        self.db_path = Path(db_path)
        self.logger: logging.Logger = logger
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.label = label


    def create_schema(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def upsert_session(self, session_id: str, **kwargs) -> None:
        self.conn.execute(
            """
            INSERT INTO sessions (session_id, context, duration, label)
            VALUES (:session_id, :context, :duration, :label)
            ON CONFLICT(session_id) DO UPDATE SET
              context=COALESCE(:context, context),
              duration=COALESCE(:duration, duration)
            """,
            {"session_id": session_id, **kwargs, "label": self.label},
        )
        self.conn.commit()
        self.logger.info(f"Upserted session {session_id}")

    def upsert_mouse_data(self, session_id: str, **kwargs) -> None:
        self.conn.execute(
            """
            INSERT INTO mouse_data (
                session_id, 
                avg_dx, 
                avg_dy, 
                avg_scroll_distance, 
                avg_click_interval, 
                clicks_per_minute
            )
            VALUES (:session_id, :avg_dx, :avg_dy, :avg_scroll_distance, :avg_click_interval, :clicks_per_minute)
            """,
            {"session_id": session_id, **kwargs},
        )
        self.conn.commit()
        self.logger.info(f"Upserted mouse_data {session_id}")

    def upsert_kb_data(self, session_id: str, **kwargs) -> None:
        self.conn.execute(
            """
            INSERT INTO keyboard_data (
                session_id, 
                avg_cpm, 
                median_cpm, 
                avg_hold_time,
                shortcut_count,
                keystroke_count
            )
            VALUES (:session_id, :avg_cpm, :median_cpm, :avg_hold_time, :shortcut_count, :keystroke_count)
            """,

            {"session_id": session_id, **kwargs},
        )
        self.conn.commit()
        self.logger.info(f"Upserted keyboard_data {session_id}")


    def close(self):
        self.conn.close()

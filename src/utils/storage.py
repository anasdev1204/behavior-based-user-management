from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT UNIQUE NOT NULL,
  context TEXT,             
  start_ts_ns INTEGER,
  end_ts_ns INTEGER
);

CREATE TABLE IF NOT EXISTS keyboard_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  avg_cpm REAL,
  median_cpm REAL,
  avg_hold_time REAL,
  session_id TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS key_stats (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  key_code TEXT NOT NULL,
  avg_hold_time REAL,
  no_of_uses INTEGER,
  is_shortcut INTEGER CHECK(is_shortcut IN (0,1)) NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS features (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_end_ns INTEGER NOT NULL,
  session_id TEXT NOT NULL,
  user_label TEXT,          
  feature_json TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_features_session_ts ON features(session_id, ts_end_ns);
"""

class EventStore:
    """
    Stores events in SQLite database.
    """
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def create_schema(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def upsert_session(self, session_id: str, **kwargs) -> None:
        self.conn.execute(
            """
            INSERT INTO sessions (session_id, context, start_ts_ns, end_ts_ns)
            VALUES (:session_id, :context, :start_ts_ns, :end_ts_ns)
            ON CONFLICT(session_id) DO UPDATE SET
              context=COALESCE(:context, context),
              start_ts_ns=COALESCE(:start_ts_ns, start_ts_ns),
              end_ts_ns=COALESCE(:end_ts_ns, end_ts_ns)
            """,
            {"session_id": session_id, **kwargs},
        )
        self.conn.commit()

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

    def upsert_kb_data(self, session_id: str, **kwargs) -> None:
        self.conn.execute(
            """
            INSERT INTO keyboard_data (
                session_id, 
                avg_cpm, 
                median_cpm, 
                avg_hold_time
            )
            VALUES (:session_id, :avg_cpm, :median_cpm, :avg_hold_time)
            """,

            {"session_id": session_id, **kwargs},
        )
        self.conn.commit()

    def upsert_key_stats(self, session_id: str, keys: dict, shortcuts: dict) -> None:
        """
        Insert per-key or per-shortcut aggregated stats.
        stats = { "a": {"avg_hold_time": 0.15, "no_of_uses": 12}, ... }
        """
        key_rows = [
            (session_id, key, val["avg_hold_time"], val["no_of_uses"], False)
            for key, val in keys.items()
        ]
        shortcut_rows = [
            (session_id, key, val["avg_hold_time"], val["no_of_uses"], False)
            for key, val in shortcuts.items()
        ]

        rows = key_rows + shortcut_rows
        print(rows)
        self.conn.executemany(
            """
            INSERT INTO key_stats (session_id, key_code, avg_hold_time, no_of_uses, is_shortcut)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

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
  user_label TEXT,          
  device_hash TEXT,
  os TEXT,
  context TEXT,             
  start_ts_ns INTEGER,
  end_ts_ns INTEGER
);

CREATE TABLE IF NOT EXISTS keystrokes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_ns INTEGER NOT NULL,
  key_code TEXT,            
  event_type TEXT CHECK(event_type IN ('down','up')) NOT NULL,
  hold_ms REAL,             
  window_hash TEXT,         
  session_id TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_keys_session_ts ON keystrokes(session_id, ts_ns);

CREATE TABLE IF NOT EXISTS mouse (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_ns INTEGER NOT NULL,
  x REAL, y REAL,           
  dx REAL, dy REAL,         
  event TEXT CHECK(event IN ('move','click','scroll','drag_start','drag_end')) NOT NULL,
  buttons TEXT,             
  session_id TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_mouse_session_ts ON mouse(session_id, ts_ns);

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
            INSERT INTO sessions (session_id, user_label, device_hash, os, context, start_ts_ns, end_ts_ns)
            VALUES (:session_id, :user_label, :device_hash, :os, :context, :start_ts_ns, :end_ts_ns)
            ON CONFLICT(session_id) DO UPDATE SET
              user_label=COALESCE(:user_label, user_label),
              device_hash=COALESCE(:device_hash, device_hash),
              os=COALESCE(:os, os),
              context=COALESCE(:context, context),
              start_ts_ns=COALESCE(:start_ts_ns, start_ts_ns),
              end_ts_ns=COALESCE(:end_ts_ns, end_ts_ns)
            """,
            {"session_id": session_id, **kwargs},
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

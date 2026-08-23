from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Reading


class HistoryRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY, captured_at TEXT NOT NULL, auction_id TEXT, auction_name TEXT, lot INTEGER, price_cents INTEGER, description TEXT, payload TEXT NOT NULL)")
            columns = {column[1] for column in conn.execute("PRAGMA table_info(readings)")}
            if "auction_id" not in columns:
                conn.execute("ALTER TABLE readings ADD COLUMN auction_id TEXT")
            if "auction_name" not in columns:
                conn.execute("ALTER TABLE readings ADD COLUMN auction_name TEXT")
            conn.commit()

    def add(self, reading: Reading) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO readings (captured_at, auction_id, auction_name, lot, price_cents, description, payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (reading.captured_at, reading.auction_id, reading.auction_name, reading.lot, reading.price_cents, reading.description, json.dumps(reading.as_dict(), ensure_ascii=False)),
            )
            conn.commit()

    def recent(self, auction_id: str | None = None, limit: int = 20) -> list[tuple[str, int | None, int | None, str]]:
        with sqlite3.connect(self.path) as conn:
            if auction_id:
                return conn.execute("SELECT captured_at, lot, price_cents, description FROM readings WHERE auction_id = ? ORDER BY id DESC LIMIT ?", (auction_id, limit)).fetchall()
            return conn.execute("SELECT captured_at, lot, price_cents, description FROM readings ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

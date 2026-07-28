"""Local history. Stays on the dev's machine.

Nothing in here is uploaded anywhere. When sponsored seats land (PLAN.md
§7a) the upward report is derived from the `mark` and `slag` columns only —
never `verdict`, never `packet`.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS marks (
    day        TEXT PRIMARY KEY,
    mark       INTEGER NOT NULL,
    slag       REAL,
    baron      TEXT NOT NULL,
    headline   TEXT,
    verdict    TEXT,
    demand     TEXT,
    packet     TEXT,
    created_at TEXT NOT NULL
);
"""


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def record(
    db_path: Path,
    day: str,
    mark: int,
    slag: float | None,
    baron: str,
    headline: str | None,
    verdict: str | None,
    demand: str | None,
    packet: str,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO marks (day, mark, slag, baron, headline, verdict, demand,
                               packet, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET
                mark=excluded.mark, slag=excluded.slag, baron=excluded.baron,
                headline=excluded.headline, verdict=excluded.verdict,
                demand=excluded.demand, packet=excluded.packet,
                created_at=excluded.created_at
            """,
            (
                day, mark, slag, baron, headline, verdict, demand, packet,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )


def history(db_path: Path, limit: int = 14, before: str | None = None) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        if before:
            rows = conn.execute(
                "SELECT * FROM marks WHERE day < ? ORDER BY day DESC LIMIT ?",
                (before, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM marks ORDER BY day DESC LIMIT ?", (limit,)
            ).fetchall()
    return rows


def latest(db_path: Path) -> sqlite3.Row | None:
    rows = history(db_path, limit=1)
    return rows[0] if rows else None


def best(db_path: Path) -> sqlite3.Row | None:
    with connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM marks ORDER BY mark DESC, day ASC LIMIT 1"
        ).fetchone()

"""The persistence layer, which is the only code here that can lose data.

Everything else in SERF produces a wrong number when it breaks. This
produces a lost diary. The migration in `connect()` runs silently on every
single call and had never once been executed against a real old-schema
database before these tests existed.
"""

from __future__ import annotations

import sqlite3

import pytest

from serf import store

# The schema exactly as it shipped before the register was added. This is
# what is sitting in every .serf/marks.db created on day one.
OLD_SCHEMA = """
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


@pytest.fixture
def db(tmp_path):
    return tmp_path / "state" / "marks.db"


@pytest.fixture
def legacy_db(tmp_path):
    """A database written by the pre-register version, with a real row in it."""
    path = tmp_path / "legacy" / "marks.db"
    path.parent.mkdir(parents=True)
    conn = sqlite3.connect(path)
    conn.executescript(OLD_SCHEMA)
    conn.execute(
        "INSERT INTO marks (day, mark, slag, baron, headline, verdict, demand,"
        " packet, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        ("2026-07-28", 8, 100.0, "carnegie", "First heat on the board",
         "A good first day.", "Put tests on observe.py.", "== THE MARK ==",
         "2026-07-28T21:30:00+00:00"),
    )
    conn.commit()
    conn.close()
    return path


def add(db, day, mark, *, slag=None, baron="carnegie", harshness=3,
        headline=None, verdict=None, demand=None, packet=""):
    store.record(db, day=day, mark=mark, slag=slag, baron=baron,
                 harshness=harshness, headline=headline, verdict=verdict,
                 demand=demand, packet=packet)


# --------------------------------------------------------------------------
# the migration

def test_migration_adds_the_register_column(legacy_db):
    with store.connect(legacy_db) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(marks)")}
    assert "harshness" in cols


def test_migration_does_not_destroy_the_existing_row(legacy_db):
    """The whole point. A migration that drops the diary is the worst bug here."""
    rows = store.history(legacy_db)
    assert len(rows) == 1
    row = rows[0]
    assert row["day"] == "2026-07-28"
    assert row["mark"] == 8
    assert row["slag"] == 100.0
    assert row["headline"] == "First heat on the board"
    assert row["verdict"] == "A good first day."
    assert row["packet"] == "== THE MARK =="


def test_migrated_row_reads_back_with_a_null_register(legacy_db):
    """Pre-register days have no register. That must be None, not 0."""
    assert store.history(legacy_db)[0]["harshness"] is None


def test_migration_is_idempotent(legacy_db):
    for _ in range(3):
        with store.connect(legacy_db):
            pass
    with store.connect(legacy_db) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(marks)")]
    assert cols.count("harshness") == 1


def test_can_write_a_new_row_into_a_migrated_database(legacy_db):
    add(legacy_db, "2026-07-29", 5, harshness=4)
    rows = store.history(legacy_db)
    assert [r["day"] for r in rows] == ["2026-07-29", "2026-07-28"]
    assert rows[0]["harshness"] == 4


def test_can_overwrite_a_pre_register_row(legacy_db):
    """Re-running the mark on a legacy day must fill the register in."""
    add(legacy_db, "2026-07-28", 8, harshness=3, headline="Re-run")
    rows = store.history(legacy_db)
    assert len(rows) == 1, "must update in place, not insert a duplicate"
    assert rows[0]["harshness"] == 3
    assert rows[0]["headline"] == "Re-run"


# --------------------------------------------------------------------------
# writing

def test_connect_creates_the_parent_directory(db):
    assert not db.parent.exists()
    with store.connect(db):
        pass
    assert db.exists()


def test_record_round_trips(db):
    add(db, "2026-07-29", 6, slag=41.5, harshness=4,
        headline="h", verdict="v", demand="d", packet="p")
    row = store.latest(db)
    assert (row["mark"], row["slag"], row["harshness"]) == (6, 41.5, 4)
    assert (row["headline"], row["verdict"], row["demand"], row["packet"]) == \
        ("h", "v", "d", "p")


def test_recording_the_same_day_twice_updates_in_place(db):
    """The mark is re-run daily. This path fires constantly."""
    add(db, "2026-07-29", 3, headline="morning")
    add(db, "2026-07-29", 7, headline="evening")
    rows = store.history(db)
    assert len(rows) == 1
    assert rows[0]["mark"] == 7
    assert rows[0]["headline"] == "evening"


def test_null_slag_survives_the_round_trip(db):
    """None means 'nothing to attribute'. It must never come back as 0."""
    add(db, "2026-07-29", 4, slag=None)
    assert store.latest(db)["slag"] is None


def test_verdict_text_survives_quotes_and_unicode(db):
    text = 'He said “slag” — and it\'s 100%\nacross\ttwo lines. 🔥'
    add(db, "2026-07-29", 1, verdict=text, packet=text)
    row = store.latest(db)
    assert row["verdict"] == text
    assert row["packet"] == text


# --------------------------------------------------------------------------
# reading

def test_history_is_newest_first(db):
    for day, mark in [("2026-07-27", 1), ("2026-07-29", 3), ("2026-07-28", 2)]:
        add(db, day, mark)
    assert [r["day"] for r in store.history(db)] == \
        ["2026-07-29", "2026-07-28", "2026-07-27"]


def test_history_respects_the_limit(db):
    for i in range(1, 6):
        add(db, f"2026-07-2{i}", i)
    assert len(store.history(db, limit=2)) == 2


def test_history_before_excludes_that_day_and_later(db):
    """`before` is how a mark sees its own past without seeing itself."""
    for day, mark in [("2026-07-27", 1), ("2026-07-28", 2), ("2026-07-29", 3)]:
        add(db, day, mark)
    days = [r["day"] for r in store.history(db, before="2026-07-28")]
    assert days == ["2026-07-27"]


def test_history_on_an_empty_database_is_empty(db):
    assert store.history(db) == []


def test_latest_returns_the_newest_day_not_the_last_written(db):
    add(db, "2026-07-29", 3)
    add(db, "2026-07-27", 9)   # written second, but older
    assert store.latest(db)["day"] == "2026-07-29"


def test_latest_on_an_empty_database_is_none(db):
    assert store.latest(db) is None


def test_best_returns_the_highest_mark(db):
    add(db, "2026-07-27", 4)
    add(db, "2026-07-28", 11)
    add(db, "2026-07-29", 6)
    assert store.best(db)["mark"] == 11


def test_best_breaks_ties_toward_the_earliest_day(db):
    """The first man to set the number holds it until someone beats it."""
    add(db, "2026-07-27", 8)
    add(db, "2026-07-29", 8)
    assert store.best(db)["day"] == "2026-07-27"


def test_best_on_an_empty_database_is_none(db):
    assert store.best(db) is None

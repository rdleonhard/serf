"""The joined path.

Every other test file proves one module in isolation. This one proves they
are actually wired to each other — that a register earned in escalation.py
reaches the prompt, that a backfill detected in report.py reaches the board,
that a failure in backends.py does not take the day's board down with it.

The model call is stubbed. Nothing here touches the network.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta

import pytest

from serf import backends, cli
from serf.config import CONFIG_RELPATH

REPLY = json.dumps({
    "headline": "One heat, and it holds",
    "verdict": "You landed one thing and it was the right thing.",
    "demand": "Put tests on the joined path.",
})


@pytest.fixture
def seat(repo, monkeypatch):
    """A bound seat in a real repo, with the model call stubbed out."""
    repo.write("src/a.py", "x = 1\ny = 2\nz = 3\n")
    repo.commit("first work")
    assert cli.main(["--repo", str(repo.path), "init"]) == 0

    captured: dict = {}

    def fake(cfg, system, user, schema):
        captured["system"] = system
        captured["user"] = user
        captured["cfg"] = cfg
        return backends.Reply(text=REPLY, model="stub", input_tokens=1,
                              output_tokens=1)

    monkeypatch.setattr(backends, "complete", fake)
    repo.captured = captured
    return repo


def run(seat, *args) -> int:
    return cli.main(["--repo", str(seat.path), *args])


def seed(seat, day: str, mark: int, *, harshness=2, slag=None, on_time=True,
         headline="seeded"):
    """Insert a mark directly, controlling when it was recorded.

    `store.record` stamps `now`, which would make every seeded past day look
    backfilled — and backfilled days are exactly what several of these tests
    need to distinguish from on-time ones.
    """
    d = date.fromisoformat(day)
    taken = d if on_time else d + timedelta(days=1)
    stamp = datetime(taken.year, taken.month, taken.day, 17).astimezone()
    conn = sqlite3.connect(seat.path / ".serf" / "marks.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS marks (
        day TEXT PRIMARY KEY, mark INTEGER NOT NULL, slag REAL,
        baron TEXT NOT NULL, harshness INTEGER, headline TEXT, verdict TEXT,
        demand TEXT, packet TEXT, created_at TEXT NOT NULL)""")
    conn.execute("INSERT OR REPLACE INTO marks VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (day, mark, slag, "carnegie", harshness, headline, "v", "d",
                  "p", stamp.isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# binding a seat

def test_init_binds_a_seat(repo):
    assert cli.main(["--repo", str(repo.path), "init"]) == 0
    assert (repo.path / CONFIG_RELPATH).exists()


def test_init_will_not_bind_twice(repo):
    cli.main(["--repo", str(repo.path), "init"])
    with pytest.raises(SystemExit):
        cli.main(["--repo", str(repo.path), "init"])


def test_init_refuses_somewhere_that_is_not_a_repository(tmp_path):
    with pytest.raises(SystemExit):
        cli.main(["--repo", str(tmp_path), "init"])


@pytest.mark.parametrize("cmd", ["mark", "board", "history", "week", "journal",
                                 "packet"])
def test_every_command_names_the_remedy_without_a_seat(repo, cmd, capsys):
    with pytest.raises(SystemExit):
        cli.main(["--repo", str(repo.path), cmd])
    assert "serf init" in capsys.readouterr().err


# --------------------------------------------------------------------------
# the mark, end to end

def test_mark_renders_the_verdict_and_records_it(seat, capsys):
    assert run(seat, "mark") == 0
    out = capsys.readouterr().out
    assert "One heat, and it holds" in out
    assert "Put tests on the joined path." in out

    capsys.readouterr()
    run(seat, "history")
    assert "One heat, and it holds" in capsys.readouterr().out


def test_dry_run_renders_but_records_nothing(seat, capsys):
    assert run(seat, "mark", "--dry-run") == 0
    assert "THE CHALK MARK" in capsys.readouterr().out
    capsys.readouterr()
    run(seat, "history")
    assert "no marks recorded yet" in capsys.readouterr().out


def test_dry_run_never_reaches_the_backend(seat):
    run(seat, "mark", "--dry-run")
    assert "system" not in seat.captured, "a dry run must not spend anything"


def test_a_backend_failure_does_not_take_the_board_down(seat, monkeypatch, capsys):
    """The day's numbers are computed locally. Losing the verdict is not
    losing the day."""
    def boom(*a, **k):
        raise backends.BackendError("venice is unreachable")
    monkeypatch.setattr(backends, "complete", boom)

    assert run(seat, "mark") == 0
    result = capsys.readouterr()
    assert "THE CHALK MARK" in result.out
    assert "venice is unreachable" in result.err


# --------------------------------------------------------------------------
# escalation actually reaches the prompt

def test_the_earned_register_reaches_the_baron(seat):
    """Three steady on-time days should raise the register — and the raise
    must arrive in the system prompt, not merely in the database."""
    today = date.today()
    for i, mark in [(3, 4), (2, 5), (1, 6)]:
        seed(seat, (today - timedelta(days=i)).isoformat(), mark, harshness=2)

    run(seat, "mark")
    system = seat.captured["system"]
    assert "Say the hard thing first" in system, "register 3 language missing"
    assert "Little cushioning" not in system, "still speaking at register 2"


def test_a_backfilled_day_does_not_earn_the_register(seat):
    today = date.today()
    seed(seat, (today - timedelta(days=3)).isoformat(), 4, harshness=2)
    seed(seat, (today - timedelta(days=2)).isoformat(), 5, harshness=2,
         on_time=False)
    seed(seat, (today - timedelta(days=1)).isoformat(), 6, harshness=2)

    run(seat, "mark")
    assert "Little cushioning" in seat.captured["system"], \
        "a day that was not lived must not buy a level"


def test_the_evidence_packet_is_what_reaches_the_model(seat):
    run(seat, "mark")
    assert "== THE MARK ==" in seat.captured["user"]
    assert "== GAMING CHECK ==" in seat.captured["user"]


# --------------------------------------------------------------------------
# report reaching the surface

def test_history_flags_a_backfilled_day(seat, capsys):
    seed(seat, "2026-07-29", 3, on_time=True)
    seed(seat, "2026-07-30", 1, on_time=False)
    run(seat, "history")
    out = capsys.readouterr().out
    assert "2026-07-30 ⟲" in out
    assert "2026-07-29 ⟲" not in out
    assert "the ritual did not" in out


def test_board_shows_the_register(seat, capsys):
    run(seat, "mark")
    capsys.readouterr()
    run(seat, "board")
    assert "register" in capsys.readouterr().out


def test_week_and_journal_read_the_same_history(seat, capsys):
    today = date.today()
    seed(seat, (today - timedelta(days=1)).isoformat(), 7, headline="yesterday")
    seed(seat, today.isoformat(), 2, headline="today")

    run(seat, "week")
    week_out = capsys.readouterr().out
    assert "heats           9 across 2 days" in week_out

    run(seat, "journal")
    assert "yesterday" in capsys.readouterr().out


def test_journal_writes_to_a_file(seat, tmp_path, capsys):
    seed(seat, "2026-07-28", 8, headline="First heat")
    out = tmp_path / "chalkmarks.md"
    run(seat, "journal", "-o", str(out))
    assert "First heat" in out.read_text()
    assert str(out) in capsys.readouterr().out


def test_packet_prints_without_spending_anything(seat, capsys):
    assert run(seat, "packet") == 0
    assert "== THE MARK ==" in capsys.readouterr().out
    assert "system" not in seat.captured

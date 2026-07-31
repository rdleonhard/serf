"""Getting the history back out, and telling the truth about the gaps."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from serf import report


def stamp_local(day: date, hour: int) -> str:
    """A created_at as store writes it: the instant, expressed in UTC.

    Derived from a LOCAL wall-clock time so the test means the same thing on
    any machine — which is the whole point of the bug it guards.
    """
    local = datetime(day.year, day.month, day.day, hour).astimezone()
    return local.astimezone(timezone.utc).isoformat(timespec="seconds")


def row(day: str, mark: int, *, slag=None, harshness=3, headline="h",
        verdict="v", demand="d", packet="p", created_at=None, baron="carnegie"):
    d = date.fromisoformat(day)
    return {
        "day": day, "mark": mark, "slag": slag, "baron": baron,
        "harshness": harshness, "headline": headline, "verdict": verdict,
        "demand": demand, "packet": packet,
        "created_at": created_at if created_at is not None else stamp_local(d, 17),
    }


# --------------------------------------------------------------------------
# backfill detection — the UTC/local trap

def test_an_evening_mark_is_not_backfilled():
    """The bug: 21:57 local is tomorrow in UTC, and day is a local date.

    Every mark taken after ~20:00 in a western timezone read as backfilled.
    """
    assert not report.was_backfilled(row("2026-07-29", 1,
                                         created_at=stamp_local(date(2026, 7, 29), 21)))


def test_a_late_night_mark_is_not_backfilled():
    assert not report.was_backfilled(row("2026-07-29", 1,
                                         created_at=stamp_local(date(2026, 7, 29), 23)))


def test_a_mark_taken_the_next_day_is_backfilled():
    assert report.was_backfilled(row("2026-07-29", 1,
                                     created_at=stamp_local(date(2026, 7, 30), 9)))


def test_a_missing_timestamp_is_not_treated_as_backfilled():
    """Absence of evidence is not evidence of a skipped ritual."""
    assert not report.was_backfilled(row("2026-07-29", 1, created_at=None))
    assert not report.was_backfilled(row("2026-07-29", 1, created_at="garbage"))


# --------------------------------------------------------------------------
# the journal

def test_journal_of_an_empty_board_says_so():
    assert "Nothing on the board yet" in report.journal([], "serf")


def test_journal_carries_the_verdict_and_the_demand():
    out = report.journal([row("2026-07-28", 8, headline="First heat",
                              verdict="A good first day.", demand="Put tests on it.")],
                         "serf")
    assert "First heat" in out
    assert "A good first day." in out
    assert "**Demand:** Put tests on it." in out


def test_journal_flags_backfilled_days_in_both_places():
    out = report.journal([row("2026-07-30", 1,
                              created_at=stamp_local(date(2026, 7, 31), 9))], "serf")
    assert "⟲" in out, "the summary table must mark it"
    assert "after the fact" in out, "the entry itself must say so"


def test_journal_does_not_let_a_headline_break_the_table():
    out = report.journal([row("2026-07-28", 8, headline="pipes | in | headlines")],
                         "serf")
    table = [ln for ln in out.splitlines() if ln.startswith("| 2026-07-28")][0]
    assert table.count("|") == 6, "a headline pipe would add a phantom column"


def test_packets_are_omitted_unless_asked_for():
    r = row("2026-07-28", 8, packet="== THE MARK ==")
    assert "== THE MARK ==" not in report.journal([r], "serf")
    assert "== THE MARK ==" in report.journal([r], "serf", include_packets=True)


# --------------------------------------------------------------------------
# the week

TODAY = date(2026, 7, 31)


def test_week_does_not_count_days_before_the_first_mark_as_missed():
    """The experiment cannot have been skipped before it began."""
    out = report.week([row("2026-07-30", 1)], TODAY)
    assert "MISSED" not in out


def test_week_does_not_count_today_as_missed():
    """At ten in the morning you have not yet failed to mark the day."""
    out = report.week([row("2026-07-29", 1), row("2026-07-30", 1)], TODAY)
    assert "MISSED" not in out


def test_week_reports_a_genuine_gap():
    out = report.week([row("2026-07-27", 5), row("2026-07-30", 1)], TODAY)
    assert "MISSED" in out
    assert "2" in out.split("MISSED")[1].split("\n")[0], "28th and 29th"


def test_week_says_so_when_the_ritual_held():
    rows = [row((TODAY - timedelta(days=i)).isoformat(), 3) for i in range(3)]
    out = report.week(rows, TODAY)
    assert "The ritual held" in out


def test_week_totals_only_the_days_in_range():
    rows = [row("2026-07-01", 99), row("2026-07-30", 2), row("2026-07-31", 3)]
    out = report.week(rows, TODAY)
    assert "heats           5 across 2 days" in out
    assert "99" not in out


def test_week_on_an_empty_board():
    assert "Nothing on the board this week" in report.week([], TODAY)

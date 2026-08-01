"""The slate holds coach material on a desk, all day, where anyone walking past
can read it.

So the tests that matter here are not about layout. They are about what is
allowed to leave the machine, and about the board never becoming a dependency
of the verdict.
"""

from __future__ import annotations

from datetime import date

from serf import slate
from serf.escalation import Register
from serf.metrics import DayStats, Gaming


def stats(mark=6, gaming=None, **kw):
    base = dict(mark=mark, disqualified=4, added=47, deleted=11, files=3,
                reverts=0, fixes=1, slag_pct=41.4, slag_complete=True,
                ci_failure_pct=None, gaming=gaming or Gaming(), commits=[])
    base.update(kw)
    return DayStats(**base)


class Verdict:
    headline = "Six heats and forty-one percent slag."
    verdict = "You are rebuilding what you laid down on Tuesday."
    demand = "Stop re-cutting Tuesday."


def payload(**kw):
    args = dict(day=date(2026, 8, 1), trunk="main", stats=stats(),
                verdict=Verdict(), baron="carnegie",
                prior=[("2026-07-31", 6), ("2026-07-30", 3)], best_mark=9,
                register=Register(3, "holding", changed=False, previous=3))
    args.update(kw)
    return slate.payload(**args)


# --- what may leave the machine -------------------------------------------

def test_the_evidence_packet_never_reaches_the_board():
    """`serf packet` is the user's audit surface, not display data."""
    assert "packet" not in payload()


def test_no_commit_subjects_leak_through_the_stats():
    """The board gets counts, never the commit list."""
    body = payload()
    assert "commits" not in body
    assert all(not isinstance(v, list) or k == "spark" for k, v in body.items())


def test_the_demand_is_not_sent():
    """Only headline + verdict are shown; the demand has nowhere to go and
    sending it would put unrendered prose on the wire for no reason."""
    assert "Stop re-cutting Tuesday." not in payload()["verdict"]


def test_verdict_is_truncated_to_what_the_band_can_show():
    body = payload(verdict=type("V", (), {"headline": "x" * 400,
                                          "verdict": "y" * 400, "demand": ""})())
    assert len(body["verdict"]) <= slate.VERDICT_CHARS


# --- the numbers ----------------------------------------------------------

def test_slag_is_rounded_not_truncated():
    assert payload()["slag"] == 41
    assert payload(stats=stats(slag_pct=41.6))["slag"] == 42


def test_missing_slag_stays_none_rather_than_becoming_zero():
    """Unknown and zero are different claims about the day."""
    assert payload(stats=stats(slag_pct=None))["slag"] is None


def test_caption_is_singular_on_a_one_heat_day():
    assert payload(stats=stats(mark=1))["caption"] == "HEAT ON THE BOARD"
    assert payload(stats=stats(mark=2))["caption"] == "HEATS ON THE BOARD"


def test_spark_runs_oldest_to_today_and_ends_on_today():
    body = payload(stats=stats(mark=6))
    assert body["spark"][-1] == 6
    assert body["spark"] == [3, 6, 6]


def test_zero_disqualified_is_not_shown_as_a_row():
    assert payload(stats=stats(disqualified=0))["uncounted"] is None


# --- the gaming check -----------------------------------------------------

def test_test_deletion_wins_over_every_other_finding():
    """It is the one the project says is never let go, at any register."""
    g = Gaming(padding=["a"], whitespace_only=["b"], test_deletion=["ddc2fd5 zeta"])
    assert payload(stats=stats(gaming=g))["flag"].startswith("Tests shrinking")


def test_a_clean_day_raises_no_flag():
    assert payload(stats=stats(gaming=Gaming()))["flag"] is None


# --- the board is an accessory, never a dependency ------------------------

def test_push_to_a_dead_address_reports_failure_instead_of_raising():
    """An unplugged slate must never fail a `serf mark` run."""
    ok, msg = slate.push("203.0.113.1", {"mark": 1}, timeout=1)
    assert ok is False
    assert msg


# --- the number and the verdict must agree --------------------------------

def test_headline_and_verdict_do_not_run_together():
    """Headlines carry no terminal punctuation, so a bare join produced
    '...but thin One commit on the board'."""
    v = type("V", (), {"headline": "One heat, whole and honest — but thin",
                       "verdict": "One commit on the board.", "demand": ""})()
    assert "thin. One commit" in payload(verdict=v)["verdict"]


def test_punctuated_headline_is_not_double_stopped():
    v = type("V", (), {"headline": "Six heats and forty-one percent slag.",
                       "verdict": "You are rebuilding.", "demand": ""})()
    assert ".. " not in payload(verdict=v)["verdict"]


def test_a_headline_alone_still_renders():
    v = type("V", (), {"headline": "Nothing landed", "verdict": "", "demand": ""})()
    assert payload(verdict=v)["verdict"] == "Nothing landed"

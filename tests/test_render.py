"""The board is the only thing most people will ever read.

A number rendered wrongly is a number lied about, whatever the arithmetic
behind it did.
"""

from __future__ import annotations

from datetime import date

from serf import render
from serf.escalation import Register
from serf.metrics import DayStats, Gaming


def stats(mark=3):
    return DayStats(mark=mark, disqualified=0, added=10, deleted=0, files=1,
                    reverts=0, fixes=0, slag_pct=None, slag_complete=True,
                    ci_failure_pct=None, gaming=Gaming(), commits=[])


def board(register):
    return render.board(day=date(2026, 7, 31), trunk="main", stats=stats(),
                        verdict=None, baron_name="Andrew Carnegie", prior=[],
                        best_mark=8, register=register)


def test_a_demotion_does_not_render_as_a_promotion():
    """The bug: every change showed ↑, including easing back."""
    out = board(Register(2, "easing back", changed=True, previous=3))
    assert "register 2↓" in out
    assert "↑" not in out


def test_a_promotion_renders_as_one():
    assert "register 4↑" in board(Register(4, "earned it", changed=True, previous=3))


def test_an_unchanged_register_gets_no_arrow():
    out = board(Register(3, "holding", changed=False, previous=3))
    assert "register 3" in out
    assert "↑" not in out and "↓" not in out


def test_a_changed_register_is_called_out_with_its_reason():
    out = board(Register(2, "2 days since the last mark", changed=True, previous=3))
    assert "REGISTER → 2" in out
    assert "2 days since the last mark" in out

"""The register has to be earned, and it has to be defensible.

A dial that drifts upward on its own would just be a machine that gets
meaner over time, which is the failure mode the whole design is trying to
avoid.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from serf.escalation import Day, effective

TODAY = date(2026, 8, 10)


def days(*rows: tuple[int, int, float | None, int]) -> list[Day]:
    """(days_ago, mark, slag, harshness), newest first."""
    return [Day(TODAY - timedelta(days=d), m, s, h) for d, m, s, h in rows]


def test_first_day_uses_the_base(cfg=None):
    r = effective(3, [], TODAY)
    assert r.level == 3
    assert r.changed is False


def test_three_steady_days_of_rising_marks_earn_a_level():
    r = effective(3, days((1, 6, 20.0, 3), (2, 5, 25.0, 3), (3, 4, 30.0, 3)), TODAY)
    assert r.level == 4
    assert r.changed is True


def test_flat_marks_with_flat_slag_still_earn_it():
    """Holding the line is a result. It does not have to be a climb."""
    r = effective(3, days((1, 5, 20.0, 3), (2, 5, 20.0, 3), (3, 5, 20.0, 3)), TODAY)
    assert r.level == 4


def test_a_falling_mark_blocks_escalation():
    r = effective(3, days((1, 3, 20.0, 3), (2, 5, 20.0, 3), (3, 4, 20.0, 3)), TODAY)
    assert r.level == 3
    assert r.changed is False


def test_rising_slag_blocks_escalation_even_when_marks_rise():
    """Output climbing while rework climbs is motion, not production."""
    r = effective(3, days((1, 9, 60.0, 3), (2, 6, 30.0, 3), (3, 4, 10.0, 3)), TODAY)
    assert r.level == 3


def test_missing_slag_does_not_block_escalation():
    r = effective(3, days((1, 6, None, 3), (2, 5, 20.0, 3), (3, 4, None, 3)), TODAY)
    assert r.level == 4


def test_two_days_away_eases_the_register():
    r = effective(3, days((2, 6, 10.0, 4)), TODAY)
    assert r.level == 3
    assert r.changed is True
    assert "since the last mark" in r.reason


def test_one_day_away_is_not_a_gap():
    """Yesterday's mark is the normal case, not absence."""
    r = effective(3, days((1, 6, 10.0, 4), (2, 5, 10.0, 4)), TODAY)
    assert r.level == 4
    assert r.changed is False


def test_easing_stops_at_the_floor():
    r = effective(1, days((9, 2, None, 1)), TODAY)
    assert r.level == 1
    assert r.changed is False


def test_escalation_stops_at_the_ceiling():
    r = effective(5, days((1, 9, 5.0, 5), (2, 8, 5.0, 5), (3, 7, 5.0, 5)), TODAY)
    assert r.level == 5
    assert r.changed is False


def test_cannot_climb_two_days_running():
    """After a raise the level is fresh, so the three-day clock restarts."""
    just_raised = days((1, 8, 10.0, 4), (2, 7, 10.0, 3), (3, 6, 10.0, 3))
    r = effective(3, just_raised, TODAY)
    assert r.level == 4, "must hold the new level for three days before the next"
    assert r.changed is False


def test_two_days_of_history_is_not_enough():
    r = effective(3, days((1, 6, 10.0, 3), (2, 5, 10.0, 3)), TODAY)
    assert r.level == 3
    assert r.changed is False


@pytest.mark.parametrize("base,expected", [(0, 1), (9, 5), (-4, 1)])
def test_base_is_clamped_into_range(base, expected):
    assert effective(base, [], TODAY).level == expected

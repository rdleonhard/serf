"""Earned escalation.

The register is not a preference the dev sets once. It is something the
baron grants as evidence accumulates that it can be taken — and withdraws
when he stops showing up, because there is no point shouting into a room
nobody is in.

Pure function over recorded history. No I/O, so the rule is testable in
isolation and can be argued about on its merits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

MIN_LEVEL = 1
MAX_LEVEL = 5

HOLD_DAYS = 3   # days you must hold a level before earning the next
AWAY_DAYS = 2   # gap that pulls the register back down


@dataclass(frozen=True)
class Register:
    level: int
    reason: str
    changed: bool


@dataclass(frozen=True)
class Day:
    """One recorded day, newest first when in a list."""

    day: date
    mark: int
    slag: float | None
    harshness: int
    recorded_on: date | None = None   # when the mark was actually taken

    @property
    def on_time(self) -> bool:
        """False when the mark was backfilled after the day it judges.

        This is what stops `serf mark --date` being a retroactive register
        repair tool. Backfilling records the work honestly; it does not
        un-miss the ritual, and the register tracks the ritual.
        """
        return self.recorded_on is None or self.recorded_on <= self.day


def _non_decreasing_marks(days: list[Day]) -> bool:
    """days is newest-first, so each newer mark must be >= the older one."""
    return all(days[i].mark >= days[i + 1].mark for i in range(len(days) - 1))


def _slag_not_worse(days: list[Day]) -> bool:
    """Rework must not be trending up. Missing figures are simply skipped."""
    for i in range(len(days) - 1):
        newer, older = days[i].slag, days[i + 1].slag
        if newer is None or older is None:
            continue
        if newer > older:
            return False
    return True


def effective(base: int, history: list[Day], today: date) -> Register:
    """Decide the register for today.

    `base` is where the dev started. `history` is newest-first and holds
    only days that were actually recorded.
    """
    base = max(MIN_LEVEL, min(MAX_LEVEL, base))
    if not history:
        return Register(base, "first day on the board", changed=False)

    current = history[0].harshness or base

    # Measure absence from the last day that was marked ON that day. A day
    # backfilled later is work recorded, not a day shown up for.
    on_time = [d.day for d in history if d.on_time]
    gap = (today - max(on_time)).days if on_time else AWAY_DAYS

    # He stopped showing up. Ease off rather than escalate into an empty room.
    if gap >= AWAY_DAYS and current > MIN_LEVEL:
        return Register(
            current - 1,
            f"{gap} days since the last mark — easing the register back",
            changed=True,
        )

    recent = history[:HOLD_DAYS]
    if len(recent) < HOLD_DAYS:
        return Register(current, "not enough history to move the register", False)

    # You must sit at a level for three recorded days before earning the next.
    steady = len({d.harshness for d in recent}) == 1
    if (
        steady
        and all(d.on_time for d in recent)
        and current < MAX_LEVEL
        and _non_decreasing_marks(recent)
        and _slag_not_worse(recent)
    ):
        return Register(
            current + 1,
            f"{HOLD_DAYS} days holding or rising with rework in hand — earned it",
            changed=True,
        )

    return Register(current, "holding", changed=False)

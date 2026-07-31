"""Getting the history back out.

`marks.db` accumulates the only record of what the barons actually said.
Left in sqlite it is unreadable and unquotable; these turn it into
something a person can read and a book can cite.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .render import sparkline


def _as_date(value: str) -> date:
    return date.fromisoformat(value)


def recorded_on(row) -> date | None:
    """The LOCAL day the mark was actually taken.

    `created_at` is stored in UTC but `day` is a local calendar date, so the
    two are not directly comparable: a mark taken at 21:57 EDT is stamped
    01:57 the next day in UTC and would read as backfilled. Convert to the
    local zone before taking the date. This also repairs rows written before
    the bug was found, since they carry their offset.
    """
    stamp = row["created_at"]
    if not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp).astimezone().date()
    except ValueError:
        return None


def was_backfilled(row) -> bool:
    """True when a mark was recorded after the day it judges.

    Worth surfacing everywhere: a backfilled mark is still honest work, but a
    run of them means the daily ritual was not actually daily, and any trend
    drawn through them says less than it appears to.
    """
    taken = recorded_on(row)
    return bool(taken and taken > _as_date(row["day"]))


# --------------------------------------------------------------------------
# the journal — everything, for the book

def journal(rows, repo_name: str, include_packets: bool = False) -> str:
    """Full history, oldest first, as markdown."""
    rows = sorted(rows, key=lambda r: r["day"])
    out: list[str] = []
    add = out.append

    add(f"# The Chalk Marks — {repo_name}")
    add("")
    if not rows:
        add("_Nothing on the board yet._")
        return "\n".join(out)

    add(f"_{len(rows)} marks, {rows[0]['day']} to {rows[-1]['day']}._")
    add("")
    add("| day | mark | slag | register | verdict |")
    add("|---|---:|---:|---:|---|")
    for r in rows:
        slag = f"{r['slag']:.0f}%" if r["slag"] is not None else "—"
        reg = r["harshness"] or "—"
        late = " ⟲" if was_backfilled(r) else ""
        add(f"| {r['day']}{late} | {r['mark']} | {slag} | {reg} | "
            f"{(r['headline'] or '').replace('|', '/')} |")
    add("")
    if any(was_backfilled(r) for r in rows):
        add("⟲ recorded after the day it judges.")
        add("")
    add("---")
    add("")

    for r in rows:
        slag = f"{r['slag']:.0f}%" if r["slag"] is not None else "—"
        add(f"## {r['day']} · Mark {r['mark']} · slag {slag} · register "
            f"{r['harshness'] or '—'}")
        if was_backfilled(r):
            add("")
            add(f"*Recorded {recorded_on(r)}, after the fact.*")
        add("")
        if r["headline"]:
            add(f"> **{r['headline']}**")
            add(f"> — {(r['baron'] or '').title()}")
            add("")
        if r["verdict"]:
            add(r["verdict"])
            add("")
        if r["demand"]:
            add(f"**Demand:** {r['demand']}")
            add("")
        if include_packets and r["packet"]:
            add("<details><summary>evidence packet</summary>")
            add("")
            add("```")
            add(r["packet"])
            add("```")
            add("")
            add("</details>")
            add("")

    return "\n".join(out)


# --------------------------------------------------------------------------
# the week — is the shop still running

def week(rows, today: date, days: int = 7) -> str:
    """A short reckoning over the last `days` calendar days."""
    window = [r for r in rows
              if today - timedelta(days=days - 1) <= _as_date(r["day"]) <= today]
    window.sort(key=lambda r: r["day"])

    out: list[str] = []
    add = out.append
    start = today - timedelta(days=days - 1)
    add("")
    add(f"  THE WEEK  ·  {start:%a %d %b} to {today:%a %d %b}")
    add("  " + "─" * 60)
    add("")

    if not window:
        add("  Nothing on the board this week.")
        add("")
        return "\n".join(out)

    by_day = {_as_date(r["day"]): r for r in window}
    covered = [start + timedelta(days=i) for i in range(days)]

    # A day is only missed if it fell inside the experiment and is over.
    # Days before the first mark were never owed, and today is not yet late.
    began = min(_as_date(r["day"]) for r in rows)
    missed = [d for d in covered if d not in by_day and began <= d < today]

    marks = [r["mark"] for r in window]
    add("  " + sparkline([by_day[d]["mark"] if d in by_day else 0 for d in covered]))
    add("  " + " ".join(f"{d:%a}"[:2] for d in covered))
    add("")

    best = max(window, key=lambda r: r["mark"])
    slags = [r["slag"] for r in window if r["slag"] is not None]
    backfilled = [r for r in window if was_backfilled(r)]

    add(f"  heats           {sum(marks)} across {len(window)} "
        f"{'day' if len(window) == 1 else 'days'}")
    add(f"  best day        {best['mark']} on {best['day']}")
    if slags:
        add(f"  slag            {sum(slags) / len(slags):.0f}% mean")
    registers = [r["harshness"] for r in window if r["harshness"]]
    if registers:
        lo, hi = min(registers), max(registers)
        add(f"  register        {lo}" + (f" → {hi}" if lo != hi else ""))

    add("")
    if missed:
        add(f"  MISSED          {len(missed)}: "
            + ", ".join(f"{d:%a %d}" for d in missed))
    if backfilled:
        add(f"  BACKFILLED      {len(backfilled)}: "
            + ", ".join(r["day"] for r in backfilled))
    if not missed and not backfilled:
        add("  every day marked, on the day. The ritual held.")
    add("")
    return "\n".join(out)

"""The Chalk Mark — one number, on a board, in the terminal."""

from __future__ import annotations

import os
import shutil
import textwrap
from datetime import date

from .metrics import DayStats
from .verdict import Verdict

_FONT = {
    "0": ["███", "█ █", "█ █", "█ █", "███"],
    "1": ["  █", "  █", "  █", "  █", "  █"],
    "2": ["███", "  █", "███", "█  ", "███"],
    "3": ["███", "  █", "███", "  █", "███"],
    "4": ["█ █", "█ █", "███", "  █", "  █"],
    "5": ["███", "█  ", "███", "  █", "███"],
    "6": ["███", "█  ", "███", "█ █", "███"],
    "7": ["███", "  █", "  █", "  █", "  █"],
    "8": ["███", "█ █", "███", "█ █", "███"],
    "9": ["███", "█ █", "███", "  █", "███"],
}

_SPARK = "▁▂▃▄▅▆▇█"


def _color() -> bool:
    return os.environ.get("NO_COLOR") is None and os.isatty(1)


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _color() else text


def bold(t: str) -> str:
    return _c(t, "1")


def dim(t: str) -> str:
    return _c(t, "2")


def big(n: int) -> list[str]:
    glyphs = [_FONT[d] for d in str(n)]
    return ["  ".join(g[row] for g in glyphs) for row in range(5)]


def sparkline(values: list[int]) -> str:
    if not values:
        return ""
    hi = max(values)
    if hi == 0:
        return _SPARK[0] * len(values)
    return "".join(_SPARK[min(len(_SPARK) - 1, round(v / hi * (len(_SPARK) - 1)))]
                   for v in values)


def board(
    day: date,
    trunk: str,
    stats: DayStats,
    verdict: Verdict | None,
    baron_name: str,
    prior: list[tuple[str, int]],
    best_mark: int | None,
    register=None,
) -> str:
    width = min(shutil.get_terminal_size((80, 24)).columns, 76)
    out: list[str] = []
    add = out.append

    header = f"THE CHALK MARK  ·  {day:%a %d %b}  ·  {trunk}"
    add("")
    add(bold(f"  {header}"))
    add(dim("  " + "─" * (width - 4)))
    add("")

    for line in big(stats.mark):
        add("    " + bold(line))
    add("")
    add(dim(f"    {'heat' if stats.mark == 1 else 'heats'} on the board"))
    add("")

    facts = []
    if prior:
        facts.append(f"yesterday {prior[0][1]}")
    if best_mark is not None:
        facts.append(f"best {best_mark}")
    if stats.slag_pct is not None:
        approx = "" if stats.slag_complete else "~"
        facts.append(f"slag {approx}{stats.slag_pct:.0f}%")
    if stats.ci_failure_pct is not None:
        facts.append(f"ci fail {stats.ci_failure_pct:.0f}%")
    facts.append(f"+{stats.added}/-{stats.deleted}")
    if stats.disqualified:
        facts.append(f"{stats.disqualified} didn't count")
    if register is not None:
        arrow = "" if not register.changed else ("↑" if register.level > 1 else "")
        facts.append(f"register {register.level}{arrow}")
    add("  " + dim("  ·  ".join(facts)))

    if prior:
        series = [m for _, m in reversed(prior)] + [stats.mark]
        add("  " + dim(sparkline(series) + "   (oldest → today)"))
    add("")

    if register is not None and register.changed:
        add("  " + bold(f"REGISTER → {register.level}") + dim(f"  ({register.reason})"))
        add("")

    if stats.gaming.any:
        add("  " + bold("⚑ GAMING CHECK"))
        for label, items in (
            ("padding", stats.gaming.padding),
            ("whitespace-only", stats.gaming.whitespace_only),
            ("tests shrinking while code grows", stats.gaming.test_deletion),
        ):
            for item in items:
                add(f"    {label}: {item}")
        add("")

    if verdict is None:
        add(dim("  (no verdict — run `serf mark` to have the baron read the diff)"))
        add("")
        return "\n".join(out)

    add("  " + bold(f"“{verdict.headline}”"))
    add(dim(f"  — {baron_name}"))
    add("")
    for para in verdict.verdict.split("\n"):
        para = para.strip()
        if not para:
            add("")
            continue
        add(textwrap.fill(para, width=width, initial_indent="  ",
                          subsequent_indent="  "))
    add("")
    add(textwrap.fill(f"TOMORROW: {verdict.demand}", width=width,
                      initial_indent="  ", subsequent_indent="            "))
    add("")
    add(dim(
        f"  {verdict.model} · in {verdict.input_tokens} "
        f"(cached {verdict.cached_tokens}) · out {verdict.output_tokens}"
    ))
    add("")
    return "\n".join(out)

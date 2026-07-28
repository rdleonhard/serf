"""The Mark, the slag, and the gaming detector.

Schwab chalked the day shift's heat count on the mill floor and the night
shift rubbed it out and wrote a bigger number. That is the whole design:
one integer, visible, compared against your own past self — not against
the man at the next desk (PLAN.md §3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Config
from .observe import Commit, Observation


@dataclass
class Gaming:
    """Ways the number can be inflated without the work being done."""

    padding: list[str] = field(default_factory=list)
    whitespace_only: list[str] = field(default_factory=list)
    test_deletion: list[str] = field(default_factory=list)

    @property
    def any(self) -> bool:
        return bool(self.padding or self.whitespace_only or self.test_deletion)


@dataclass
class DayStats:
    mark: int               # heats: commits that count
    disqualified: int       # commits that did not
    added: int
    deleted: int
    files: int
    reverts: int
    fixes: int
    slag_pct: float | None  # % of deleted lines that were <window days old
    slag_complete: bool     # False when the churn cap bit and slag is a sample
    ci_failure_pct: float | None
    gaming: Gaming
    commits: list[Commit]

    @property
    def net(self) -> int:
        return self.added - self.deleted


def _qualifies(c: Commit, cfg: Config) -> bool:
    if c.is_revert:
        return False
    if c.whitespace_only:
        return False
    if c.touched <= cfg.padding_max_lines and len(c.files) <= 1:
        return False
    return True


def _detect_gaming(commits: list[Commit], cfg: Config) -> Gaming:
    g = Gaming()
    for c in commits:
        short = f"{c.sha[:8]} {c.subject}"
        # A revert is honest work undone, not an inflated number. It already
        # fails to count toward the Mark; don't also accuse him of padding.
        if c.is_revert:
            continue
        if c.whitespace_only:
            g.whitespace_only.append(short)
        elif c.touched <= cfg.padding_max_lines and len(c.files) <= 1:
            g.padding.append(short)

        # Tests shrinking while production code grows is the one signal
        # SERF is never allowed to let go of.
        test_net = sum(f.added - f.deleted for f in c.files if f.is_test)
        prod_net = sum(f.added - f.deleted for f in c.files if not f.is_test)
        if test_net < 0 and prod_net > 0:
            g.test_deletion.append(f"{short}  (tests {test_net:+d}, code {prod_net:+d})")
    return g


def summarize(obs: Observation, cfg: Config) -> DayStats:
    commits = obs.commits
    qualifying = [c for c in commits if _qualifies(c, cfg)]

    considered = sum(c.deleted_considered for c in commits)
    churned = sum(c.churned_lines for c in commits)
    slag = (100.0 * churned / considered) if considered else None

    files_total = sum(c.deletion_files_total for c in commits)
    files_done = sum(c.deletion_files_attributed for c in commits)

    ci_rate = obs.ci_failure_rate
    return DayStats(
        mark=len(qualifying),
        disqualified=len(commits) - len(qualifying),
        added=sum(c.added for c in commits),
        deleted=sum(c.deleted for c in commits),
        files=len({f.path for c in commits for f in c.files}),
        reverts=sum(1 for c in commits if c.is_revert),
        fixes=sum(1 for c in commits if c.is_fix),
        slag_pct=slag,
        slag_complete=(files_done == files_total),
        ci_failure_pct=(ci_rate * 100.0) if ci_rate is not None else None,
        gaming=_detect_gaming(commits, cfg),
        commits=commits,
    )


def evidence_packet(stats: DayStats, obs: Observation, cfg: Config,
                    history: list[tuple[str, int]]) -> str:
    """The facts SERF is allowed to speak from.

    Every quantitative claim in the verdict has to be answerable from this
    text — that is the anti-Goodhart rule from PLAN.md §3 made mechanical.
    """
    lines: list[str] = []
    add = lines.append

    add(f"BRANCH: {obs.trunk}")
    add(f"WINDOW: {obs.since:%Y-%m-%d %H:%M} to {obs.until:%Y-%m-%d %H:%M}")
    add("")
    add("== THE MARK ==")
    add(f"heats (qualifying commits): {stats.mark}")
    add(f"commits that did not count: {stats.disqualified}")
    add(f"lines: +{stats.added} -{stats.deleted} (net {stats.net:+d}) across {stats.files} files")
    add(f"reverts: {stats.reverts}   fix-shaped commits: {stats.fixes}")
    if stats.slag_pct is None:
        add("slag (rework): no deleted lines to attribute")
    else:
        add(
            f"slag (rework): {stats.slag_pct:.0f}% of deleted lines were written "
            f"in the last {cfg.churn_window_days} days"
        )
        if not stats.slag_complete:
            add(
                "  NOTE: that figure is a SAMPLE. Some commits changed more files "
                f"than the churn cap ({cfg.churn_max_files}), so not every deleted "
                "line was attributed. Treat the slag number as approximate and say "
                "so if you rely on it."
            )
    if stats.ci_failure_pct is None:
        add("CI: no data (gh unavailable or unauthenticated)")
    else:
        add(f"CI: {stats.ci_failure_pct:.0f}% of recent runs on {obs.trunk} did not pass")

    add("")
    add("== SELF vs SELF (most recent first) ==")
    if history:
        for day, mark in history:
            add(f"{day}: {mark}")
    else:
        add("no prior marks recorded — this is the first day on the board")

    add("")
    add("== COMMITS ==")
    if not stats.commits:
        add("(none)")
    for c in stats.commits:
        flags = []
        if c.is_revert:
            flags.append("REVERT")
        if c.whitespace_only:
            flags.append("WHITESPACE-ONLY")
        if not _qualifies(c, cfg):
            flags.append("DID NOT COUNT")
        tag = f"  [{', '.join(flags)}]" if flags else ""
        add(f"- {c.sha[:8]} +{c.added}/-{c.deleted} {c.subject}{tag}")
        for f in c.files[:12]:
            add(f"    {f.path}  +{f.added}/-{f.deleted}")
        if len(c.files) > 12:
            add(f"    ... and {len(c.files) - 12} more files")

    add("")
    add("== GAMING CHECK ==")
    if not stats.gaming.any:
        add("nothing flagged")
    else:
        for label, items in (
            ("commit padding", stats.gaming.padding),
            ("whitespace-only commits", stats.gaming.whitespace_only),
            ("tests shrinking while code grows", stats.gaming.test_deletion),
        ):
            for item in items:
                add(f"{label}: {item}")

    return "\n".join(lines)

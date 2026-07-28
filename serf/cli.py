"""serf — bind a baron to a repo and take your marks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

from . import config as cfgmod
from . import metrics, observe, render, store, verdict as verdictmod
from .barons import WORKS


def _die(msg: str) -> None:
    print(f"serf: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _window(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    end = datetime.now() if day == date.today() else start + timedelta(days=1)
    return start, end


def _load(args: argparse.Namespace) -> cfgmod.Config:
    try:
        return cfgmod.load(Path(args.repo).resolve())
    except cfgmod.ConfigError as exc:
        _die(str(exc))
        raise  # unreachable, keeps type checkers happy


# --------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    probe = cfgmod.Config(repo=repo)
    if not observe.is_repo(probe):
        _die(f"{repo} is not a git repository")

    try:
        path = cfgmod.write_default(repo)
    except cfgmod.ConfigError as exc:
        _die(str(exc))
        return 1

    # Guess the trunk so the first run works without editing anything.
    head = subprocess.run(
        ["git", "-C", str(repo), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        capture_output=True, text=True,
    ).stdout.strip()
    trunk = head.rsplit("/", 1)[-1] if head else ""
    if not trunk:
        for candidate in ("main", "master"):
            if observe._rev_exists(probe, candidate):
                trunk = candidate
                break
    if trunk and trunk != "main":
        path.write_text(path.read_text().replace('trunk = "main"', f'trunk = "{trunk}"'))

    print(f"seat bound at {path}")
    print(f"  baron: carnegie   trunk: {trunk or 'main (unverified)'}")
    print("\nRun `serf mark` at the end of the day.")
    return 0


def cmd_packet(args: argparse.Namespace) -> int:
    cfg = _load(args)
    day = date.fromisoformat(args.date) if args.date else date.today()
    since, until = _window(day)
    obs = observe.collect(cfg, since, until)
    stats = metrics.summarize(obs, cfg)
    hist = [(r["day"], r["mark"]) for r in
            store.history(cfg.db_path, 7, before=day.isoformat())]
    print(metrics.evidence_packet(stats, obs, cfg, hist))
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    cfg = _load(args)
    day = date.fromisoformat(args.date) if args.date else date.today()
    since, until = _window(day)

    try:
        obs = observe.collect(cfg, since, until)
    except observe.GitError as exc:
        _die(str(exc))
        return 1

    stats = metrics.summarize(obs, cfg)
    hist = [(r["day"], r["mark"]) for r in
            store.history(cfg.db_path, 7, before=day.isoformat())]
    packet = metrics.evidence_packet(stats, obs, cfg, hist)

    v = None
    if not args.dry_run:
        try:
            v = verdictmod.render(cfg, packet)
        except verdictmod.VerdictError as exc:
            print(f"serf: {exc}", file=sys.stderr)
            print("serf: showing the board without a verdict.\n", file=sys.stderr)

    best_row = store.best(cfg.db_path)
    best_mark = max(best_row["mark"], stats.mark) if best_row else stats.mark

    print(render.board(
        day=day,
        trunk=cfg.trunk,
        stats=stats,
        verdict=v,
        baron_name=WORKS[cfg.baron].name,
        prior=hist,
        best_mark=best_mark,
    ))

    if not args.dry_run:
        store.record(
            cfg.db_path,
            day=day.isoformat(),
            mark=stats.mark,
            slag=stats.slag_pct,
            baron=cfg.baron,
            headline=v.headline if v else None,
            verdict=v.verdict if v else None,
            demand=v.demand if v else None,
            packet=packet,
        )
    return 0


def cmd_board(args: argparse.Namespace) -> int:
    cfg = _load(args)
    row = store.latest(cfg.db_path)
    if row is None:
        _die("nothing on the board yet — run `serf mark`")
        return 1

    day = date.fromisoformat(row["day"])
    since, until = _window(day)
    obs = observe.collect(cfg, since, until)
    stats = metrics.summarize(obs, cfg)

    v = None
    if row["verdict"]:
        v = verdictmod.Verdict(
            headline=row["headline"], verdict=row["verdict"], demand=row["demand"],
            baron=row["baron"], model="(recorded)",
        )
    hist = [(r["day"], r["mark"]) for r in
            store.history(cfg.db_path, 7, before=row["day"])]
    best_row = store.best(cfg.db_path)

    print(render.board(
        day=day, trunk=cfg.trunk, stats=stats, verdict=v,
        baron_name=WORKS[row["baron"]].name, prior=hist,
        best_mark=best_row["mark"] if best_row else None,
    ))
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    cfg = _load(args)
    rows = store.history(cfg.db_path, args.limit)
    if not rows:
        print("no marks recorded yet")
        return 0
    print(f"{'day':<12} {'mark':>5} {'slag':>6}  headline")
    for r in reversed(rows):
        slag = f"{r['slag']:.0f}%" if r["slag"] is not None else "  —"
        print(f"{r['day']:<12} {r['mark']:>5} {slag:>6}  {r['headline'] or ''}")
    return 0


# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="serf", description=__doc__)
    p.add_argument("--repo", default=".", help="repository to read (default: cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="bind a seat to this repo").set_defaults(fn=cmd_init)

    m = sub.add_parser("mark", help="compute today's mark and get the verdict")
    m.add_argument("--date", help="YYYY-MM-DD (default: today)")
    m.add_argument("--dry-run", action="store_true",
                   help="compute and render, but make no model call and record nothing")
    m.set_defaults(fn=cmd_mark)

    b = sub.add_parser("board", help="re-render the last recorded mark")
    b.set_defaults(fn=cmd_board)

    h = sub.add_parser("history", help="list recorded marks")
    h.add_argument("-n", "--limit", type=int, default=14)
    h.set_defaults(fn=cmd_history)

    k = sub.add_parser("packet", help="print the evidence packet and exit")
    k.add_argument("--date", help="YYYY-MM-DD (default: today)")
    k.set_defaults(fn=cmd_packet)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

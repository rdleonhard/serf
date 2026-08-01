"""serf — bind a baron to a repo and take your marks."""

from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

from . import config as cfgmod
from . import escalation, metrics, observe, render, report, slate, store
from . import verdict as verdictmod
from .barons import WORKS


def _die(msg: str) -> None:
    print(f"serf: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _window(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    end = datetime.now() if day == date.today() else start + timedelta(days=1)
    return start, end


def _register(cfg: cfgmod.Config, rows, day: date) -> escalation.Register:
    """What register has actually been earned as of today."""
    past = [
        escalation.Day(
            day=date.fromisoformat(r["day"]),
            mark=r["mark"],
            slag=r["slag"],
            harshness=r["harshness"] or cfg.harshness,
            recorded_on=report.recorded_on(r),
        )
        for r in rows
    ]
    return escalation.effective(cfg.harshness, past, day)


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
    rows = store.history(cfg.db_path, 7, before=day.isoformat())
    hist = [(r["day"], r["mark"]) for r in rows]
    packet = metrics.evidence_packet(stats, obs, cfg, hist)

    # The register is earned from history, not read from config. cfg.harshness
    # is only the starting point.
    reg = _register(cfg, rows, day)
    run_cfg = dataclasses.replace(cfg, harshness=reg.level)

    v = None
    if not args.dry_run:
        try:
            v = verdictmod.render(run_cfg, packet)
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
        register=reg,
    ))

    if not args.dry_run:
        store.record(
            cfg.db_path,
            day=day.isoformat(),
            mark=stats.mark,
            slag=stats.slag_pct,
            baron=cfg.baron,
            harshness=reg.level,
            headline=v.headline if v else None,
            verdict=v.verdict if v else None,
            demand=v.demand if v else None,
            packet=packet,
        )
        # Put it on the glass if a slate is configured. Best-effort by design:
        # an unplugged board must never fail a mark run.
        ip = slate.resolve_ip(getattr(args, "ip", None))
        if ip and not getattr(args, "no_slate", False):
            row = store.latest(cfg.db_path)
            ok, msg = slate.push(ip, _slate_payload(cfg, row))
            print(f"slate {ip}: {'on the glass' if ok else 'unreachable — ' + msg}",
                  file=sys.stderr)
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
    prior_rows = store.history(cfg.db_path, 7, before=row["day"])
    hist = [(r["day"], r["mark"]) for r in prior_rows]
    best_row = store.best(cfg.db_path)

    print(render.board(
        day=day, trunk=cfg.trunk, stats=stats, verdict=v,
        baron_name=WORKS[row["baron"]].name, prior=hist,
        best_mark=best_row["mark"] if best_row else None,
        register=_register(cfg, prior_rows, day),
    ))
    return 0


def _slate_payload(cfg, row):
    """Rebuild the payload for a recorded row.

    The store keeps the mark, the slag and the verdict; the +/- lines,
    disqualified count and gaming check are not stored, so they are recomputed
    from git the way cmd_board does.

    But the MARK ITSELF is taken from the record, not the recompute. A day's
    window keeps accepting commits after the verdict is written, so recomputing
    it drifts: the board would show 3 next to a verdict that says "one heat,
    whole and honest". The number on the glass has to be the number the baron
    actually judged.
    """
    day = date.fromisoformat(row["day"])
    since, until = _window(day)
    stats = metrics.summarize(observe.collect(cfg, since, until), cfg)
    stats = dataclasses.replace(stats, mark=row["mark"], slag_pct=row["slag"])

    v = None
    if row["verdict"]:
        v = verdictmod.Verdict(
            headline=row["headline"], verdict=row["verdict"], demand=row["demand"],
            baron=row["baron"], model="(recorded)",
        )
    prior_rows = store.history(cfg.db_path, 7, before=row["day"])
    best_row = store.best(cfg.db_path)
    return slate.payload(
        day=day,
        trunk=cfg.trunk,
        stats=stats,
        verdict=v,
        baron=row["baron"],
        prior=[(r["day"], r["mark"]) for r in prior_rows],
        best_mark=best_row["mark"] if best_row else None,
        register=_register(cfg, prior_rows, day),
    )


def cmd_slate(args: argparse.Namespace) -> int:
    cfg = _load(args)
    row = store.latest(cfg.db_path)
    if row is None:
        _die("nothing on the board yet — run `serf mark`")
        return 1

    body = _slate_payload(cfg, row)

    if args.dry_run:
        print(json.dumps(body, indent=2))
        return 0

    ip = slate.resolve_ip(args.ip)
    if not ip:
        _die("no slate address — pass --ip or write one to ~/.slate_ip")
        return 1

    ok, msg = slate.push(ip, body)
    if not ok:
        print(f"serf: slate at {ip} did not answer: {msg}", file=sys.stderr)
        return 1
    print(f"slate {ip}: mark {body['mark']} for {body['day']}"
          + ("  [FLAGGED]" if body["flag"] else ""))
    return 0


def cmd_journal(args: argparse.Namespace) -> int:
    cfg = _load(args)
    rows = store.history(cfg.db_path, limit=10_000)
    text = report.journal(rows, cfg.repo.name, include_packets=args.packets)
    if args.out:
        out = Path(args.out)
        out.write_text(text)
        print(f"{len(rows)} marks written to {out}")
    else:
        print(text)
    return 0


def cmd_week(args: argparse.Namespace) -> int:
    cfg = _load(args)
    rows = store.history(cfg.db_path, limit=10_000)
    print(report.week(rows, date.today(), days=args.days))
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    cfg = _load(args)
    rows = store.history(cfg.db_path, args.limit)
    if not rows:
        print("no marks recorded yet")
        return 0
    print(f"{'day':<12} {'mark':>5} {'slag':>6} {'reg':>4}  headline")
    for r in reversed(rows):
        slag = f"{r['slag']:.0f}%" if r["slag"] is not None else "  —"
        reg = str(r["harshness"]) if r["harshness"] else "—"
        late = " ⟲" if report.was_backfilled(r) else "  "
        print(f"{r['day']}{late}  {r['mark']:>5} {slag:>6} {reg:>4}  "
              f"{r['headline'] or ''}")
    if any(report.was_backfilled(r) for r in rows):
        print("\n⟲ recorded after the day it judges — the work counted, "
              "the ritual did not.")
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
    m.add_argument("--ip", help="slate address (default: ~/.slate_ip)")
    m.add_argument("--no-slate", action="store_true",
                   help="do not push the result to the slate")
    m.set_defaults(fn=cmd_mark)

    b = sub.add_parser("board", help="re-render the last recorded mark")
    b.set_defaults(fn=cmd_board)

    h = sub.add_parser("history", help="list recorded marks")
    h.add_argument("-n", "--limit", type=int, default=14)
    h.set_defaults(fn=cmd_history)

    j = sub.add_parser("journal", help="export every mark as markdown, for the book")
    j.add_argument("-o", "--out", help="write to a file instead of stdout")
    j.add_argument("--packets", action="store_true",
                   help="include the full evidence packet for each day")
    j.set_defaults(fn=cmd_journal)

    w = sub.add_parser("week", help="the week's reckoning: trend, best day, what slipped")
    w.add_argument("--days", type=int, default=7)
    w.set_defaults(fn=cmd_week)

    sl = sub.add_parser("slate", help="push the last recorded mark to the slate")
    sl.add_argument("--ip", help="board address (default: ~/.slate_ip)")
    sl.add_argument("--dry-run", action="store_true",
                    help="print the payload; send nothing")
    sl.set_defaults(fn=cmd_slate)

    k = sub.add_parser("packet", help="print the evidence packet and exit")
    k.add_argument("--date", help="YYYY-MM-DD (default: today)")
    k.set_defaults(fn=cmd_packet)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

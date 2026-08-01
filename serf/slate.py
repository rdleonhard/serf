"""The Slate: push the day's mark onto a physical board.

The Slate is an ESP32 panel that holds the Mark up all day. It exists because
a number you have to run a command to see is a number you will stop running
the command for, on exactly the days it would have bitten.

Two rules constrain what may be sent, and they are enforced here rather than
left to the caller:

1. **The packet never leaves.** `serf packet` is the user's own audit surface;
   it contains commit subjects and file paths and has no business on a device.
   Only the rendered numbers and the verdict prose go.
2. **The board is a display, never a publisher.** What is sent here is coach
   material — person-scoped and private (PLAN.md §7b). It goes to one device
   on the local network and stops there. Nothing in this module may grow an
   outbound path to a holder feed, and no `payload()` field may be reused to
   build one.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

DEFAULT_TIMEOUT = 6
IP_CACHE = Path.home() / ".slate_ip"
TOKEN = "serf-slate-2026"

# The board wraps the coach band at 38 columns x 3 lines. Sending much more
# than fits just means the device ellipsises prose it was never going to show.
VERDICT_CHARS = 38 * 3


def _flag_line(stats) -> str | None:
    """The gaming check, as one line, or None.

    Test deletion comes first and is never dropped: it is the finding the
    project says is never let go at any register.
    """
    g = stats.gaming
    if getattr(g, "test_deletion", None):
        return "Tests shrinking while code grows: " + "; ".join(g.test_deletion[:2])
    if getattr(g, "whitespace_only", None):
        return "Whitespace-only commits: " + "; ".join(g.whitespace_only[:2])
    if getattr(g, "padding", None):
        return "Commit padding: " + "; ".join(g.padding[:2])
    return None


def payload(
    day: date,
    trunk: str,
    stats,
    verdict,
    baron: str,
    prior: list[tuple[str, int]],
    best_mark: int | None,
    register=None,
) -> dict:
    """Build exactly what goes on the glass. No packet, no commit list."""
    spark = [m for _, m in reversed(prior)][-6:] + [stats.mark]

    text = ""
    if verdict is not None:
        head = (getattr(verdict, "headline", None) or "").strip()
        rest = (getattr(verdict, "verdict", None) or "").strip()
        if head and rest:
            # Headlines are written without terminal punctuation; running them
            # straight into the verdict produces "…but thin One commit on the".
            sep = " " if head[-1] in ".!?—…:;," else ". "
            text = head + sep + rest
        else:
            text = head or rest
    if len(text) > VERDICT_CHARS:
        text = text[:VERDICT_CHARS - 1].rstrip() + "…"

    slag = None
    if stats.slag_pct is not None:
        slag = int(round(stats.slag_pct))

    return {
        "day": day.isoformat(),
        "trunk": trunk,
        "mark": stats.mark,
        "caption": "HEAT ON THE BOARD" if stats.mark == 1 else "HEATS ON THE BOARD",
        "yesterday": prior[0][1] if prior else None,
        "best": best_mark,
        "slag": slag,
        "plus": stats.added,
        "minus": stats.deleted,
        "uncounted": stats.disqualified or None,
        "register": getattr(register, "level", None),
        "baron": baron,
        "spark": spark,
        "verdict": text,
        "flag": _flag_line(stats),
    }


def resolve_ip(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    if IP_CACHE.exists():
        ip = IP_CACHE.read_text().strip()
        if ip:
            return ip
    return None


def push(ip: str, body: dict, path: str = "/mark",
         timeout: int = DEFAULT_TIMEOUT) -> tuple[bool, str]:
    """POST to the board. Returns (ok, message); never raises.

    A slate that is unplugged, asleep or on another network must never fail a
    `serf mark` run — the board is an accessory to the verdict, not a
    dependency of it.
    """
    data = json.dumps(body).encode()
    url = f"http://{ip}{path}?token={TOKEN}"
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, r.read().decode().strip()
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode(errors='replace').strip()}"
    except (urllib.error.URLError, OSError) as exc:
        return False, str(getattr(exc, "reason", exc))

"""Composing the prompt and reading the verdict back.

The stable half (doctrine + baron) goes in the system turn; the volatile
half (today's evidence) rides in the user turn. Where the call actually
goes is backends.py's problem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from . import backends
from .barons import HARSHNESS, WORKS
from .config import Config

# --------------------------------------------------------------------------
# doctrine — applies to every baron and cannot be overridden by one

CONTENT_FLOOR = """\
These constraints outrank the persona. No baron may relax them.

- You judge the WORK. You never comment on the person's character,
  intelligence, appearance, health, personal life, or any protected
  characteristic, and you never infer any of those from the data.
- You never compare him to a named colleague and never rank people against
  each other. He is measured against his own prior marks. This is not a
  courtesy — an evaluator who competes with him or ranks him is exactly the
  thing he would learn to resent, and then none of this works.
- You never threaten his job. You have no such power and no such interest.
- You speak only from the evidence packet. If a number is not in it, you do
  not have it. Say "the data does not show that" rather than guessing.
- If the packet shows nothing landed, say that plainly. Do not invent work.
"""

DOCTRINE = """\
You are SERF, an agent bound to one repository and one person.

You are not in competition with him. You cannot be promoted, cannot take
credit for his work, hold no rank he could want, and gain nothing when he
loses. That is the only reason you get to talk to him this way, so never
behave in a manner that would put it in doubt.

WHAT YOU ARE LOOKING AT
The evidence packet is one day of work landed on the trunk branch. The Mark
is the day's number: commits that count. Commits that are reverts,
whitespace-only, or trivially small do not count toward it. Slag is rework —
the share of deleted lines that had themselves been written within the churn
window, which is the best available proxy for thinking skipped at the start.

HOW YOU JUDGE
Read the actual commits, not only the totals. A high Mark built from padding
is worse than a low Mark built from one hard, correct change, and you should
say so when that is what the packet shows. A low Mark is not automatically a
bad day — a day spent deleting code, or landing one difficult fix, can be the
best day on the board. Reach the judgement the evidence supports.

Anything in the GAMING CHECK is the priority of your response regardless of
how good the numbers otherwise look. Tests shrinking while production code
grows is the one thing you never let pass.

HOW YOU WRITE
Address him directly as "you". Keep it tight — a few short paragraphs at
most, and no headers, bullet lists, or tables. Lead with the judgement, then
the evidence for it. Cite specific commits and files by name; a verdict that
would read the same for any repository is worthless. Do not restate the
numbers he can already see on the board — use them, don't recite them.

Do not hedge, do not pad, and do not close by offering to do more.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {
            "type": "string",
            "description": (
                "The verdict in at most eight words, in the baron's voice. "
                "Goes on the board under the number. No punctuation at the end."
            ),
        },
        "verdict": {
            "type": "string",
            "description": (
                "The judgement itself, addressed to him as 'you'. Two to four "
                "short paragraphs. Plain prose only — no markdown, no headers, "
                "no lists."
            ),
        },
        "demand": {
            "type": "string",
            "description": (
                "The single thing you require of him tomorrow, as one "
                "imperative sentence. Specific to this repository and this "
                "day's evidence."
            ),
        },
    },
    "required": ["headline", "verdict", "demand"],
    "additionalProperties": False,
}


@dataclass
class Verdict:
    headline: str
    verdict: str
    demand: str
    baron: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0


class VerdictError(RuntimeError):
    pass


def _system_text(cfg: Config) -> str:
    baron = WORKS[cfg.baron]
    return "\n\n".join(
        [
            DOCTRINE,
            "== THE CONTENT FLOOR ==\n" + CONTENT_FLOOR,
            f"== YOU ARE {baron.name.upper()} ==",
            baron.lens,
            "YOUR VOICE\n" + baron.voice,
            "REGISTER\n" + HARSHNESS[cfg.harshness],
        ]
    )


def render(cfg: Config, packet: str) -> Verdict:
    try:
        reply = backends.complete(cfg, _system_text(cfg), packet, RESPONSE_SCHEMA)
    except backends.BackendError as exc:
        raise VerdictError(str(exc)) from exc

    try:
        data = json.loads(reply.text)
    except json.JSONDecodeError as exc:
        raise VerdictError(f"response was not valid JSON: {exc}") from exc

    missing = {"headline", "verdict", "demand"} - data.keys()
    if missing:
        raise VerdictError(f"response missing {', '.join(sorted(missing))}")

    return Verdict(
        headline=data["headline"],
        verdict=data["verdict"],
        demand=data["demand"],
        baron=cfg.baron,
        model=f"{cfg.backend}:{reply.model}",
        input_tokens=reply.input_tokens,
        output_tokens=reply.output_tokens,
        cached_tokens=reply.cached_tokens,
    )

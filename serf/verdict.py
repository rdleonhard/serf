"""The model call.

The stable half of the prompt (doctrine + baron) is sent as cached system
blocks; the volatile half (today's evidence) rides in the user turn. That
split is the whole caching design — see the prompt-caching prefix rule.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import anthropic

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


_NO_CREDS = (
    "no usable credentials. Export ANTHROPIC_API_KEY, or run `ant auth login` "
    "and confirm with `ant auth status`."
)


def _system_blocks(cfg: Config) -> list[dict]:
    baron = WORKS[cfg.baron]
    text = "\n\n".join(
        [
            DOCTRINE,
            "== THE CONTENT FLOOR ==\n" + CONTENT_FLOOR,
            f"== YOU ARE {baron.name.upper()} ==",
            baron.lens,
            "YOUR VOICE\n" + baron.voice,
            "REGISTER\n" + HARSHNESS[cfg.harshness],
        ]
    )
    # One block, one breakpoint. This prefix is byte-stable across days, which
    # is what makes it cacheable — keep every volatile value out of it.
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def render(cfg: Config, packet: str) -> Verdict:
    try:
        client = anthropic.Anthropic()
    except Exception as exc:  # noqa: BLE001 - surfaced verbatim to the user
        raise VerdictError(f"could not construct the Anthropic client: {exc}") from exc

    try:
        response = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            system=_system_blocks(cfg),
            output_config={
                "effort": cfg.effort,
                "format": {"type": "json_schema", "schema": RESPONSE_SCHEMA},
            },
            messages=[{"role": "user", "content": packet}],
        )
    except anthropic.AuthenticationError as exc:
        raise VerdictError(_NO_CREDS + f"\n  ({exc})") from exc
    except anthropic.RateLimitError as exc:
        raise VerdictError(f"rate limited — try again shortly. ({exc})") from exc
    except anthropic.APIStatusError as exc:
        raise VerdictError(f"API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise VerdictError(f"could not reach the API: {exc}") from exc
    except TypeError as exc:
        # The SDK raises a bare TypeError, not AuthenticationError, when no
        # credential can be resolved at all.
        if "authentication method" in str(exc):
            raise VerdictError(_NO_CREDS) from exc
        raise VerdictError(f"bad request: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - never traceback over a day's board
        raise VerdictError(f"unexpected failure calling the model: {exc}") from exc

    # Always before touching content: a refusal returns 200 with empty or
    # partial content, and indexing content[0] would blow up here.
    if response.stop_reason == "refusal":
        detail = getattr(response.stop_details, "explanation", None) or "no explanation"
        raise VerdictError(f"the model declined to answer ({detail})")

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise VerdictError(f"empty response (stop_reason={response.stop_reason})")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise VerdictError(f"response was not valid JSON: {exc}") from exc

    usage = response.usage
    return Verdict(
        headline=data["headline"],
        verdict=data["verdict"],
        demand=data["demand"],
        baron=cfg.baron,
        model=response.model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cached_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
    )

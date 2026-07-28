"""Where the verdict is actually generated.

Two backends, same model. `venice` is the default and the one the design
argues for: SERF is supposed to run on rented compute it does not own
(MECHANISM.md). Calling Anthropic directly would make that document a
description of something the code doesn't do.

`anthropic` is kept for A/B and for anyone without Venice credit.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

VENICE_URL = "https://api.venice.ai/api/v1/chat/completions"


@dataclass
class Reply:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0


class BackendError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# credentials

def venice_key(cfg) -> str:
    """Env first, then a key file. The key is never written into the repo."""
    key = os.environ.get("VENICE_API_KEY")
    if key:
        return key.strip()

    ref = getattr(cfg, "venice_key_file", "") or ""
    if not ref:
        raise BackendError(
            "no Venice credential. Export VENICE_API_KEY, or set "
            "venice_key_file in .serf/config.toml to a file holding the key."
        )

    path = Path(ref).expanduser()
    if not path.exists():
        raise BackendError(f"venice_key_file does not exist: {path}")

    raw = path.read_text().strip()
    if path.suffix == ".json" or raw.startswith("{"):
        try:
            blob = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BackendError(f"{path} is not valid JSON: {exc}") from exc
        field = getattr(cfg, "venice_key_field", "venice_key")
        if field not in blob:
            raise BackendError(f"{path} has no {field!r} field")
        return str(blob[field]).strip()
    return raw


# --------------------------------------------------------------------------
# venice (OpenAI-compatible)

def _venice(cfg, system: str, user: str, schema: dict) -> Reply:
    import httpx

    body = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_completion_tokens": cfg.max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "verdict", "strict": True, "schema": schema},
        },
        # Venice prepends its own system prompt unless told not to. It would
        # sit above the doctrine and the content floor, so it must be off.
        "venice_parameters": {"include_venice_system_prompt": False},
    }
    if cfg.effort:
        body["reasoning_effort"] = cfg.effort

    try:
        r = httpx.post(
            VENICE_URL,
            headers={
                "Authorization": f"Bearer {venice_key(cfg)}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=300,
        )
    except httpx.HTTPError as exc:
        raise BackendError(f"could not reach Venice: {exc}") from exc

    if r.status_code == 401:
        raise BackendError("Venice rejected the credential (401).")
    if r.status_code == 429:
        raise BackendError("Venice rate limit or insufficient credit (429).")
    if r.status_code != 200:
        raise BackendError(f"Venice HTTP {r.status_code}: {r.text[:300]}")

    payload = r.json()
    choices = payload.get("choices") or []
    if not choices:
        raise BackendError(f"Venice returned no choices: {str(payload)[:200]}")

    choice = choices[0]
    finish = choice.get("finish_reason")
    text = (choice.get("message") or {}).get("content") or ""
    if finish == "length":
        raise BackendError(
            f"the verdict was cut off at max_tokens={cfg.max_tokens}. Raise it."
        )
    if not text.strip():
        raise BackendError(f"Venice returned empty content (finish_reason={finish})")

    usage = payload.get("usage") or {}
    return Reply(
        text=text,
        model=payload.get("model", cfg.model),
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
    )


# --------------------------------------------------------------------------
# anthropic (direct)

_NO_ANTHROPIC_CREDS = (
    "no Anthropic credential. Export ANTHROPIC_API_KEY, or run `ant auth login`. "
    "(Or set backend = \"venice\" in .serf/config.toml.)"
)


def _anthropic(cfg, system: str, user: str, schema: dict) -> Reply:
    import anthropic

    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            # One block, one breakpoint. This prefix is byte-stable across
            # days, which is what makes it cacheable.
            system=[{"type": "text", "text": system,
                     "cache_control": {"type": "ephemeral"}}],
            output_config={
                "effort": cfg.effort,
                "format": {"type": "json_schema", "schema": schema},
            },
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.AuthenticationError as exc:
        raise BackendError(_NO_ANTHROPIC_CREDS + f"\n  ({exc})") from exc
    except anthropic.RateLimitError as exc:
        raise BackendError(f"rate limited — try again shortly. ({exc})") from exc
    except anthropic.APIStatusError as exc:
        raise BackendError(f"API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise BackendError(f"could not reach the API: {exc}") from exc
    except TypeError as exc:
        if "authentication method" in str(exc):
            raise BackendError(_NO_ANTHROPIC_CREDS) from exc
        raise BackendError(f"bad request: {exc}") from exc

    # Always before touching content: a refusal returns 200 with empty or
    # partial content, and indexing content[0] would blow up here.
    if response.stop_reason == "refusal":
        detail = getattr(response.stop_details, "explanation", None) or "no explanation"
        raise BackendError(f"the model declined to answer ({detail})")

    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise BackendError(f"empty response (stop_reason={response.stop_reason})")

    u = response.usage
    return Reply(
        text=text,
        model=response.model,
        input_tokens=u.input_tokens,
        output_tokens=u.output_tokens,
        cached_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
    )


BACKENDS = {"venice": _venice, "anthropic": _anthropic}


def complete(cfg, system: str, user: str, schema: dict) -> Reply:
    fn = BACKENDS.get(cfg.backend)
    if fn is None:
        raise BackendError(
            f"unknown backend {cfg.backend!r}; pick one of {', '.join(BACKENDS)}"
        )
    try:
        return fn(cfg, system, user, schema)
    except BackendError:
        raise
    except Exception as exc:  # noqa: BLE001 - never traceback over a day's board
        raise BackendError(f"unexpected failure calling {cfg.backend}: {exc}") from exc

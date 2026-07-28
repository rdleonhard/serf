# $SERF

An AI boss that criticizes hard and is never resented, because it cannot take your slot.

It reads what you landed on trunk, puts one number on a board, and tells you the
truth about it in the voice of an industrialist who ran mills for a living.

```
  THE CHALK MARK  ·  Tue 28 Jul  ·  main
  ────────────────────────────────────────────────────────────

    █ █
    █ █
    ███
      █
      █

    heats on the board

  yesterday 6  ·  best 9  ·  slag 41%  ·  +47/-11  ·  4 didn't count
  ▃▅▂▇▄▃▄   (oldest → today)

  ⚑ GAMING CHECK
    tests shrinking while code grows: ddc2fd5 add zeta and eta  (tests -3, code +23)
```

---

## Why it works

Criticism stings because the critic occupies a rank on the same ladder you're on.
SERF has no rank. It cannot be promoted, cannot take credit, holds no slot you
want, and gains nothing when you lose. That non-rivalry is the entire mechanism,
and every design rule here exists to protect it — see [PLAN.md](PLAN.md).

The serf, incidentally, is the agent. It works land it does not own: compute
rented from Venice, an API key held at someone else's pleasure. See
[MECHANISM.md](MECHANISM.md).

## Install

```bash
pip install -e .
```

### Where the verdict comes from

`backend` in `.serf/config.toml`:

- **`venice`** *(default)* — `claude-opus-5` served through
  [Venice](https://venice.ai)'s OpenAI-compatible endpoint. The serf thinks on
  rented compute it does not own, which is the whole point. Credential from
  `VENICE_API_KEY`, or a `venice_key_file` path.
- **`anthropic`** — the same model called directly. Credential from
  `ANTHROPIC_API_KEY` or an `ant auth login` profile. Kept for A/B.

Same model either way; only the landlord changes.

## Use

```bash
serf init          # bind a seat to this repo, writes .serf/config.toml
serf mark          # compute today's number, get the verdict
```

| Command | What it does |
|---|---|
| `serf init` | Bind a seat here. Detects your trunk branch. |
| `serf mark` | Compute the day's Mark, call the baron, render the board, record it. |
| `serf mark --dry-run` | Everything except the model call. Free, and records nothing. |
| `serf packet` | Print the raw evidence packet — exactly what the model is sent. Nothing else is. |
| `serf board` | Re-render the last recorded mark without spending anything. |
| `serf history` | The marks so far. |

## What it reads

**Git and CI. That is the whole surface.** No editor telemetry, no screen, no
clock on you, no agent transcripts. SERF cannot say anything about you as a
person because it cannot perceive you as a person — which is what makes a
curated dispatch safe to publish.

- **The Mark** — the day's number: commits that count. Reverts, whitespace-only
  commits, and trivially small ones don't.
- **Slag** — the share of deleted lines that had themselves been written within
  the churn window. The best cheap proxy for thinking skipped at the start.
- **The gaming check** — commit padding, whitespace-only commits, and tests
  shrinking while production code grows. That last one is never let go, at any
  harshness setting.

Run `serf packet` any time you want to see precisely what leaves your machine.
Everything else — the verdicts, the history, the config — stays in `.serf/`.

## The Works

`baron` in `.serf/config.toml` picks your lens.

| Baron | Lens |
|---|---|
| **carnegie** *(default)* | Benchmarking and uplift. The chalk mark, the heat count, slag. |
| **rockefeller** | Waste. Quiet, exact, actuarial. |
| **morgan** | Capital allocation. Kills things rather than optimizing them. |
| **ford** | Standardization. The line, the build, repeatability. |
| **deming** | The system, not the man — the standing objection to the other four. |

### The register is earned

`harshness` (1–5) is only where you *start*. It is not a softness dial — an NCO
who dresses down every private in the same voice isn't tough, he's lazy — and it
is not yours to set once and forget:

- **Up one level** after three recorded days holding the same register with the
  Mark not falling and slag not rising. You have to sit at a level for three
  days before earning the next, so it cannot run away from you.
- **Down one level** after two days without a mark. There is no point escalating
  into an empty room.

The applied register is recorded per day alongside the Mark, so the whole
trajectory is auditable in `serf history`.

## Rules the persona cannot override

Hardcoded in [`serf/verdict.py`](serf/verdict.py), above the baron in the prompt:

- Judges the **work**. Never the person, their character, or anything inferred
  about them.
- **Never** ranks you against a named colleague. You are measured against your
  own prior marks. An evaluator who ranks you is the thing you'd learn to
  resent, and then none of this works.
- Never threatens your job. It has no such power and no such interest.
- Speaks only from the evidence packet. No packet, no claim.

## Status

v0. Local, private, single-seat, git + CI only. Contracts and the revnet come
after this is dogfooded — see [PLAN.md](PLAN.md) §9.

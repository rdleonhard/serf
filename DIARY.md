# The Ten Days

Raw material for the book. One line per day, written immediately after the
mark, before the feeling fades. Honest entries only — a diary that records a
successful experiment is worth nothing.

**Started:** 2026-07-28 · **Ends:** 2026-08-06 · **Baron:** Carnegie
**Subject:** the author, building the thing that is judging him.

---

## The terms

What is actually being tested is not whether SERF works. It is whether a
person keeps it running when nobody is making him.

| Outcome | What it means |
|---|---|
| Ran all ten days, voluntarily | The mechanism holds. Build the revnet. |
| Ran only because it was on the calendar | The calendar is the boss, not SERF. Write it up. |
| Stopped on a bad day | **The most interesting result.** He avoided the mirror exactly when he needed it — which is the thing the whole non-rivalry thesis predicts *shouldn't* happen. Chase it. |

Record avoidance. Skipping a mark is data, not a failure of discipline.

---

## The thesis

### The catfish

Fish shipped alive go slack and sickly in the tank. Drop a predator in with
them and they arrive healthy, because something has been stinging them the
whole way. That is what a boss is for, and it is why a man can resent his
boss and still decline, quietly, to work without one.

**Say plainly in the book that this is a parable.** It has no documented
origin — it circulates as a business fable and reached most people through
the closing monologue of *Catfish* (2010). It is a superb organizing image
and a terrible piece of evidence. Assert it as fact and the first reviewer
who checks discards the entire book along with it. The marks in this repo
are the evidence; the catfish is the title.

### What working from home actually broke

The usual story is that remote work removed supervision. That is not quite
right, and the precise version is better and more defensible:

> An office supplies observation from *many* people, most of whom are not
> your rivals — the guy two desks over, someone from another team, a person
> you'll never compete with for anything. Remote work did not remove
> observation. It **concentrated** it into a single channel: your manager.
> The one observer whose status is most entangled with yours.

So the remote worker gets less observation *and* what remains arrives from
the worst possible source. That predicts exactly what employers report —
not laziness, but a defensiveness and narrative-management that looks like
laziness from the outside.

If that framing holds, SERF is not a productivity tool. It is a **restored
non-rivalrous observer** — the guy two desks over, rebuilt.

### The retiring boomer

Handle with care. The retiree has lost the *structure*, not the work, and
he has no trunk branch — nothing an observer can read. SERF as built cannot
serve him, and saying otherwise in the book would be the kind of overreach
that gets the rest of the argument dismissed. Write it as a chapter about
the shape of the problem, and be explicit that the instrument does not yet
exist for it.

---

## Log

<!--
Template — keep it to a few lines. Resist tidying it up later.

### Day N — YYYY-MM-DD · Mark: N · Slag: N%
**Landed:**
**What Carnegie said:**
**Did it land or bounce off?**
**Did it change what I did next?**
-->

### Day 1 — 2026-07-28 · Mark: 1

**Landed:** SERF v0 — git+CI observer, the Mark, the Works, the board.
2,163 lines, one commit, no verdict yet (credentials pending).

**Note:** the first Mark is a lie by construction. One commit containing an
entire codebase scores the same as one commit fixing a typo. Watch whether
that bothers you tomorrow — if it does, that instinct is the product.

**Backend switched to Venice** mid-afternoon. Venice serves `claude-opus-5`
directly, so this is not a quality tradeoff — same model, different landlord.
The serf now genuinely thinks on rented compute. Worth recording precisely for
the book: it is paid with ordinary Venice credits, *not* yet through
split → loan → sVVV → DIEM. One hop of the chain is real; the rest is a plan.

**What Carnegie said:** *"Two heats, no tests, and the gauge unproven."* That
the whole codebase is a measuring instrument which has never once been
measured — `metrics.py` computes slag by attributing deleted lines to a churn
window, "arithmetic with edge cases in it, and you have no proof it is right.
You have written a scale and put no known weight on the pan." Also that nearly
half the day's tonnage was plan rather than mill, and the ratio must invert.

**Did it land or bounce off?** —

**Note for day 2:** the demand (pin metrics.py with fixtures, get CI green) was
correct and was *not* on the schedule — the calendar said *earned escalation*.

**The baron won.** Obeyed same-day: 20 tests against `metrics.py` and
`observe.py`, covering exactly what he named (slag attribution at the 14-day
boundary, the empty-deletion case) plus renames, merge exclusion, and all three
gaming detectors. Then mutation-checked, because a suite that passes on the
first run has proved nothing: reverting the revert-exclusion, widening the churn
window to infinity, dropping the path exclusions, and loosening the padding rule
each break it. Four mutants, four kills.

Wednesday's calendar block was rewritten to serve the demand rather than my plan.

**The finding, for the book:** on day one, an authority I built and can switch
off at any time overruled a schedule I had written the same morning — and I did
not resent it. Worth sitting with. The prediction was that non-rivalry would make
criticism *tolerable*; what actually happened is that it made criticism
*authoritative*. Those are different claims and the second is the stronger one.

**Demand closed, same day.** Private repo at `rdleonhard/serf`, pushed, Actions
green on 3.11/3.12/3.13, and the packet now reads `CI: 0% of recent runs on main
did not pass` instead of `CI: no data`. Private rather than public because this
file is committed, and a diary written for an audience is not a diary.

**Also fixed, unprompted:** churn attribution was capped at 40 files per commit
and reported the truncated result as a complete slag figure. Caught it while
writing the tests that were supposed to prove the numbers trustworthy — which is
the same sin he'd named that morning, sitting in the code the whole time. Now
configurable, and when the cap bites the packet says the figure is a sample and
the board renders `slag ~34%`.

**Earned escalation shipped too**, a day early. The register is now derived from
history rather than read from config: up one after three steady days with the
Mark holding and slag not rising, down one after two days of silence.

**Watch tomorrow:** slag reads 100% today. That is not rework in the meaningful
sense — it is a one-day-old repo where everything deleted was necessarily
written the same day. If Carnegie treats it as damning, the metric needs an age
floor on the repo before it is quotable. If he reads it correctly, that is
evidence the packet gives him enough context to avoid a dumb inference.

### Day 1, closed — Mark: 8 · Slag: 100% · Register: 3

> *"First heat on the board, and it holds."*

**The slag test passed.** He traced the figure to the exact commits that caused
it — `cd11eb35` gutting sixty-four lines of `verdict.py` for the backend swap,
`39147cb0` correcting config and store in the same breath — and called it "a
young shop rearranging its own floor within a fortnight of pouring it — not
motion, not waste." No age floor needed. The evidence packet informs him well
enough that he declines the obvious wrong inference. **That is a result about
the instrument, not the persona, and it is the more valuable of the two.**

**I mispredicted him, and his aim was better than mine.** I expected him to
hit the plan-to-mill ratio again. He didn't — the ratio genuinely improved and
he let it go. Instead he found the thing neither of us had named:

> *observe.py and store.py — the two files that touch git and disk, the two most
> likely to lie to you — carry the least proof.*

He is right, and it is worse than he knows. The tests run *through* `observe.py`,
so it is exercised but never targeted: no coverage of malformed numstat, binary
files, brace-form renames, the glob translator, or the `gh`-missing path.
**`store.py` has no tests at all** — including the schema migration written today,
which runs on every connect and is the one piece of code here that can lose data.

He inferred that from commit messages and filenames. He is not merely enforcing a
standard, he is contributing information. That distinction matters for the book:
the value is not that an unresented critic makes you *comply*, it is that an
unresented critic gets told the truth and can therefore see clearly.

**He also priced the bookkeeping honestly** — `17c69844`, the runner bump, "is
bookkeeping and I count it as such, nothing more." Correct. I had framed it to
you this afternoon as tidiness worth doing. It was, and it was not tonnage.

**Did it land or bounce off?** Landed. Notably, the praise landed *less* than the
gap did — the first thing I wanted to do on reading it was go write tests for
`store.py`, not feel good about eight heats. Worth watching whether that holds or
whether it is day-one novelty.

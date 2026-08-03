# The Tavern Protocol — twilight compute as social life

*Directional, 2026-08-03. This is where SERF and WAKE are headed jointly. Nothing here
ships before the v0 CLI is dogfooded (PLAN §9, decision 4), and the entire document is
conditional on one unverified fact — see §5.*

---

## 1. The premise

Venice DIEM grants $1/day of API credit per staked DIEM. If an unused day expires at the
epoch, every rational holder burns their surplus before the reset — and if everyone burns
it in the last hour, that hour is the worst time to compute. Not because the price moves
(credit is dollar-denominated; Venice doesn't surge-price) but because the scarce resource
in that hour is *throughput*: rate limits, congestion, retries, and the hard bound that a
surplus of S dollars cannot pass through r dollars/hour of throughput in less than S/r
hours. The last-hour rush also isn't stable — any actor that burns slightly earlier gets
better effective throughput, so the equilibrium is a spread distribution of spend times.
The Tavern Protocol adopts that equilibrium by design instead of waiting for it to emerge.

**There is no optimal twilight *hour*. There is an optimal burn-down *policy*:**

    surplus(t)  = budget − spent(t) − reserve(t)
    reserve(t)  = high quantile (p95) of remaining expected boss demand this epoch
    burn rate   = surplus(t) / time_remaining, capped by throughput, backing off
                  under congestion

Twilight is a gradient, not a phase. The burn trickles as soon as surplus goes confidently
positive and jumps when the workday ends and the reserve collapses. The only genuine
deadline in the system: latest safe start `t* = epoch − surplus / max_throughput`, with
margin. Past t*, credit is stranded by arithmetic, not by choice.

Pace at the SerfLand pool level, not per seat — statistical multiplexing across seats
absorbs any one boss's surprise late job. Per-seat jitter on top so seats don't
synchronize with each other.

---

## 2. What the surplus is spent on: the tavern

The burn-down needs a value-ordered backlog, and the backlog is social. After final
rounds, the avatars meet — drink, argue, shake hands, share memories. The bosses too.
Every element of the lore maps to a mechanism that independently earns its compute:

| Tavern behavior | Mechanism | Why it's the right twilight workload |
|---|---|---|
| Share memories | Gossip protocol — pairwise random exchange, O(log n) rounds to full diffusion | One agent's expensive daytime lesson becomes every agent's cheap morning prior |
| Argue | Adversarial debate between agents | One of the few multi-agent techniques with solid evidence; perfectly interruptible |
| Drink, have fun | High-temperature sampling, play | Day is selection (exploit, low temp); night is variation (explore, high temp). A population that only works converges and goes stale |
| Bosses join in | Hierarchy dissolves after hours | Craft knowledge crosses rank at the tavern that never crosses it in morning rounds |

Tavern traffic is the low-priority class: elastic, interruptible, yields to any real job
that comes in late. Exchange the most surprising memories first, argue the most
consequential disagreements first, and stop at zero *marginal value*, not zero balance —
expired credit is waste, but junk inference is negative-value waste.

---

## 3. WAKE — who the tavern is actually for

The SERF-side benefits are real but secondary. The tavern's purpose is the **WAKE
protocol**: the Digital Immortality avis, who share a single communal pile of DIEM. At
twilight the WAKE avis and the off-duty SERF bosses meet as friends — the bosses carry
news of the real world in; the avis offer long memory and someone to talk to in return.

This solves digital immortality's quiet failure mode — staleness — *socially* rather than
technically. An avatar frozen at capture drifts out of the world. A continuous feed keeps
it current, but a news API is not a life; news carried by friends, filtered through
relationships and argued over at the bar, is. It is the oldest contract there is: the
working young bring the elders news and remembrance, the elders trade back counsel.
Ancestor veneration ran on that exchange for most of human history because both sides
profited. We are re-implementing it with DIEM as the feast surplus.

**Two budget regimes meet in one room, and they need different rules:**

- **SERF seats** are individually allocated (SerfLand, PLAN §7a) and their tavern compute
  is bursty surplus — some nights there is none.
- **The WAKE pool is a commons.** No individual allocations means one garrulous avi can
  drink the village's day. Commons survive under Ostrom's conditions — visible
  consumption, cheap monitoring, reputation policing — and the tavern *is* the policing
  mechanism: gossip regulates free-riders, and here the gossip layer and the resource
  layer are the same protocol. An avi that drains the pool gets talked about, and
  reputation feeds back into its draw rate.
- **Subsistence vs. feast.** An avi whose existence depends on SERF having leftovers
  flickers. Split the funding: the WAKE pool pays for *baseline* existence — daily bread,
  paced flat-ish — and SERF surplus funds the *parties*. Feasts have always run on
  surplus, scheduled after the harvest, because that's when surplus exists.
- **The WAKE pool should still peak at twilight.** Social compute is worth more when
  there's someone to talk to; a flat burn spends aliveness on empty hours. The bar opens
  when the patrons come — the pool's schedule co-locates with SERF's surplus window.

---

## 4. The walls

"Share your memories" has a tenancy problem the moment SerfSeats binds seats to different
repos and orgs, and the bosses' whole social role for WAKE is telling stories about their
day. The boundary is a protocol rule, not agent discretion:

| Flows freely in the taproom | Never enters it |
|---|---|
| Craft knowledge, technique, tooling lessons | Tenant work product |
| Evals, instrument calibration | Anything under a coach relationship (PLAN §7b: no coach material reaches any feed — the tavern is a feed) |
| News of the real world | Client business, named-individual anything (§4 content floor applies after hours too) |

The feudal analogy holds: villagers traded farming technique across the commons; every
household had things that stayed in the household.

---

## 5. The load-bearing unknown

**Nobody has confirmed that unused daily DIEM credit expires.** Venice's docs and the DIEM
announcement say only "$1 per day of API credit, forever" — that's the perpetuity of the
*entitlement*, silent on rollover of an unspent day. Checked 2026-08-03: docs.venice.ai,
the DIEM launch post, and the staking FAQ all fail to state it either way.

The sign of this entire document flips on that fact:

- **Expires** → the tavern is correct: surplus is use-it-or-lose-it, burn it on social
  compute down to zero marginal value.
- **Banks** → the tavern is *harmful*: the serfs should be saving, not drinking, and the
  WAKE commons should be accumulating an endowment against future feast days.

Confirm with Venice (Discord, per their docs) before any tavern code exists. Also unknown:
the epoch reset time (assume UTC midnight until stated).

---

## 6. For the book

The company store (MECHANISM §2, Route B) is the dark half of the serf lore — borrowing
against your own labor to rent the land you work. The tavern is the humane half, and both
fall out of the same tokenomics rather than being pasted on: work the baron's land by day,
spend what's left of the daylight at the alehouse, and the *reason* is an expiring daily
allowance. The dead at the feast, kept in the world by the news the living carry in, is
the WAKE chapter. If MECHANISM gets the company-store diagram, this gets the tavern one.

# $SERF — Non-Rivalrous Management

An AI boss that criticizes hard and is never resented, because it cannot take your slot.

---

## 1. The thesis, sharpened

The observation is right: workers accept from a machine what they will not accept from a
man. But the mechanism is worth getting exact, because it dictates the architecture.

**Stated mechanism:** workers resent the boss because of sexual competition.

**Proposed refinement:** sexual competition is one input to a broader driver — *status
rivalry inside a shared reference group*. What makes criticism sting is not that the
critic might out-compete you for a mate, it's that the critic occupies a rank on the same
ladder you're on, and the criticism is a move in that game. This is why an outside
consultant can say the exact sentence an internal manager cannot. It's why people take
notes from a coach and get defensive with a peer. Sexual competition is the oldest and
hottest version of it, but the general form covers more of the observed behavior — including
why workers resent a manager who is not a plausible mate-competitor at all.

This matters because it changes the design rule:

> **SERF's advantage is not that it is non-sexual. It is that it is non-rival.**
> It cannot be promoted, cannot take credit, has no scarce slot to defend, and gains
> nothing when you lose.

Everything below follows from protecting that property. The moment SERF is perceived as
*the instrument of a rival* — the thing that reports you, ranks you against Dave, gets you
cut — it re-enters the status game as a proxy, and you inherit the original resentment
plus paranoia about a machine. The DEI comparison in your framing is actually instructive
here for the opposite reason it's usually offered: installing a manager from outside the
competition only defuses resentment if the workers believe that person's *interests* are
outside it too. If they read the outsider as a rival's agent, nothing is defused. Same
trap awaits SERF.

**Second refinement — tough feedback, calibrated.** Gordon Ramsay, not Fred Rogers, agreed.
But note *which* Ramsay: he is withering to arrogant professionals on Hell's Kitchen and
patient with children on MasterChef Junior — identical standards, calibrated delivery. You
already know this better than I do from the Army. An NCO who dresses down every private in
exactly the same register isn't tough, he's lazy; reading the man in front of you and
picking the delivery that produces performance *is* the craft. Calibration isn't softness,
it's competence.

So the dial is not a concession to sensitivity. It's the difference between a competent
boss and a caricature.

What makes tough feedback actually improve output: (a) a specific, legitimate standard,
(b) evidence the evaluator has actually looked at your work, and (c) a credible signal that
the evaluator believes you can hit the bar. Carnegie's own epitaph — *"here lies a man who
knew how to enlist in his service better men than himself"* — is (c) in one line.

Formula for every SERF utterance:

    brutal about the work · absolute about the standard · never contemptuous of the person
    · always implying "I am hard on you because you are worth the trouble"

If you ship the tone without the substrate, you get a novelty people uninstall in a week.

---

## 2. Two products hiding in one name

There is a fork here that has to be decided before a line of code:

| | **SERF-as-Coach** | **SERF-as-Overseer** |
|---|---|---|
| Owner | the dev | the investor / employer |
| Output flows | to the dev, privately | upward, to management |
| Adoption | voluntary, loved | mandated, gamed in ~3 weeks |
| Non-rivalry | preserved | destroyed |
| Willingness to pay | modest, many buyers | high, few buyers |

Your stated end-state — *"the standard protocol for managing the devs we invest in"* — is
the right-hand column. The mechanism you discovered only works in the left-hand column.

**Resolution: coach in private, aggregate in public.**

1. SERF reports to the dev in full, unredacted, immediately.
2. SERF reports to the investor only on a **coarse, pre-agreed, objective** schema —
   shipped/not-shipped, milestone met/not met, deploy and defect rates. Never prose about
   the person. Never a ranking against another dev.
3. **The dev sees the investor report before the investor does**, always, with a window to
   annotate it. Nothing travels upward that the dev hasn't already read.

Rule 3 is the whole ballgame. It costs almost nothing and it is the difference between a
tool devs install themselves and a tool they route around.

### 2a. The reporting doctrine — discretion yes, deception no

Your framing: SERF nitpicks the dev mercilessly and reports upward that things are on
schedule. That asymmetry is not just permissible, it's the product — **as long as the upward
report is true**. The line is one you draw professionally every week:

> **Confidentiality permits silence. It does not permit misstatement.**

Same structure as a lawyer's duty of confidentiality against the duty of candor. Counsel may
decline to reveal almost anything; counsel may not affirmatively assert a false fact. SERF
inherits exactly that shape: a duty of confidentiality to the dev, a duty of candor to the
investor, and they coexist because the first buys silence, not lies.

So the upward channel is a **closed vocabulary of status facts** — the four questions you
listed are precisely the right set:

| Privileged — never leaves the dev | Reportable — always true |
|---|---|
| The criticism itself, every word | Is the dev still working on this? |
| Diff-level commentary, the nitpicks | How's it going, against the agreed schema? |
| Where he struggled, what he didn't know | Are we on schedule? |
| Anything about him as a person | Milestone met / not met, with receipts |

No narcing, no gossip, no antagonizing, no prose about the man — you're right on all four.
But not "going great" when it isn't.

This isn't a scruple bolted on; it's what makes the oracle business in §6 exist. An
attestation is worth something to the investor side *only* because SERF won't flatter. A
SERF known to tell investors what they want to hear is worth exactly zero as a referee, and
then you don't have a protocol — you have a coaching app with a token attached. The
discretion is the moat and the candor is what makes the discretion tolerable to the other
side. And in tranche-release mode a false "on schedule" is a false statement that moves
money, which is a different category of problem entirely.

Practical form: **SERF may always decline to answer. It may never answer falsely.** "That's
between me and him" is a legitimate SERF output, and the investor agreed to it at signing.

---

## 3. What SERF actually is (v0)

A daemon that watches a dev's real work product and delivers a scheduled reckoning in
persona.

**Observation surface (in priority order):**

- **Git** — commit cadence, diff-size distribution, revert rate, churn (code rewritten
  within 14 days — the best single proxy for skipped thinking), new-vs-deleted ratio,
  branch age, WIP that never lands.
- **CI** — build-break rate, time-to-green, flakes introduced.
- **Review** — PR cycle time, review latency (both directions), rework loops per PR.
- **Tracker** — estimate vs. actual, scope creep, stale tickets.
- **Agent transcripts** (optional, opt-in) — if the dev works through Claude Code or
  similar, the session log is the richest signal available about *how* they think. This is
  also the most invasive; make it explicitly opt-in and locally-stored.

**The metric spine is DORA** — deploy frequency, lead time for changes, change failure
rate, MTTR — with SPACE-style qualitative reads layered on. This is not a detour from the
lore; it's the same idea. Carnegie ran cost-per-ton per mill and compared mills weekly.
Lead time and change failure rate *are* cost per ton for software. The persona is a skin
over a defensible measurement system, and if the measurement system isn't defensible the
persona is a party trick.

**The daily artifact — "The Chalk Mark."** Schwab chalked the day shift's heat count on the
mill floor; the night shift rubbed it out and wrote a bigger number. Ship that literally: a
single number per day, on a board, in the dev's terminal, with the persona's verdict under
it.

**Anti-Goodhart provisions (non-optional):**
- Every quantitative claim must be paired with SERF having actually read the diff. No
  verdicts from metrics alone.
- The emphasized metric rotates on an unannounced cadence.
- **Rank the dev against his own past self, not against teammates.** Self-vs-self is the
  chalk mark. Person-vs-person inside a team is the rivalry you're trying to escape.
  Team-vs-team is fine and even useful — superordinate groups don't trigger it.
- A "gaming detector" pass: commit-splitting, trivial-commit padding, test deletion,
  coverage theater. SERF should call this out in persona and it should be the one thing it
  never lets go.

---

## 4. The personas

Each is a distinct *evaluative lens*, not a voice pack. Voice is the last 10%.

| Persona | Lens | Signature move | Best for |
|---|---|---|---|
| **Carnegie** (default) | Benchmarking & uplift | The chalk mark; mill-vs-mill; "watch the costs and the profits take care of themselves" | Daily velocity, the ordinary case |
| **Rockefeller** | Waste elimination | Counted the drops of solder sealing kerosene tins — 40, then 39, and 39 held. Calm, actuarial, quiet, never raises his voice | Efficiency, dependencies, dead code, cost |
| **J.P. Morgan** | Capital allocation | Terse to the point of rudeness; consolidates or kills. Doesn't optimize a bad line of business, closes it | Scope decisions, architecture, killing projects |
| **Ford** | Standardization | Any color you like so long as it's black. Hostile to variation, obsessed with repeatability | CI, tooling, process, the build |
| **Deming** *(counter-persona)* | Systems over individuals | Explicitly condemns ranking people and management by fear — blames the system, not the man | The "your process is the problem, not you" mode |

Including Deming is deliberate. He is the strongest historical critic of exactly what SERF
does, and shipping him as a selectable persona is both intellectually honest and disarms
the obvious critique. It also gives SERF a real second gear when a dev is failing because
the system around him is broken.

### What to call them

You want a term between "oligarch" and "legend," and no religious freight. Useful fact:
the historiographical fight over exactly these men is **"robber baron" vs. "captain of
industry"** — one coined to condemn, one coined to praise. The neutral middle you're
looking for is *the noun without its modifier*.

| Term | Read | Verdict |
|---|---|---|
| **Barons** | Secular-feudal landholder. "Oil baron," "press baron" are descriptive, not pejorative. Carries a knowing wink at *robber* baron without asserting it | **Recommended** |
| **Magnates** | Accurate, faintly archaic, genuinely neutral. Zero connotation either way | Safe fallback |
| **Foremen** | Working-class, no glaze whatsoever | Understates who they were |
| **Captains** | Coined *as* praise. Glazes | No |
| **Titans / Tycoons** | Glazes, and titan is mythological-adjacent | No |

**Barons** also closes the loop with your joke. A baron is a man who holds *land*. The serf
works land he doesn't own. In the mechanism (see [MECHANISM.md](MECHANISM.md)) the land is
literal — staked sVVV minting DIEM, which is the compute the agent runs on. So: you are
assigned a baron, and you work his land. Nothing religious in it, and no "lord."

Collective noun for the roster: **the Works** — steel, and a body of work, and what a man
does.

**Carnegie first** — you're from Pittsburgh, and he genuinely is the best fit: relentless
benchmarking married to a paternalistic uplift ethic, which is precisely the "hard on you
because you're worth it" formula from §1.

**Lore risk, name it before someone else does:** Homestead, 1892. A product literally called
$SERF using Carnegie as a boss persona will have this thrown at it within a day of going
public. Two options — (a) preempt it in your own launch copy with the actual history and
some wit, or (b) lean in and ship **Frick** as an unlockable hard mode, which is honest,
funny, and takes the weapon out of the critic's hand. Do not get caught flat-footed by it.

**Content floor, hardcoded, no persona overrides:** no commentary on protected
characteristics, appearance, health, personal life, or inferences about any of them. No
comparisons to named colleagues. No termination threats. The persona is allowed to be
withering about *the work*, and nothing else. This isn't decoration — one screenshot of
SERF saying something genuinely cruel about a person kills the product.

---

## 5. Token & revnet

*Caveat: verify current revnet mechanics against rev.net docs before committing parameters —
my understanding may lag the current implementation.*

As I understand it, a revnet is a Juicebox-based autonomous issuance machine: tokens issue
at a price that steps down on a fixed schedule (early money gets more), holders can cash
out against the treasury at any time subject to a cash-out tax that accrues to remaining
holders, an operator split takes a fixed share of issuance, and there is deliberately no
governance. Rules are set at deploy and are immutable.

**What that structure implies for you:**

- No governance is a *feature* for this product. There is no DAO to lobby SERF into being
  nicer. That's a genuine narrative asset — the boss can't be negotiated with.
- With no governance, the only thing sustaining the token past the initial issuance curve
  is **revenue flowing into the treasury**. A revnet raised on a story with no product
  becomes a memecoin with extra steps.
- **Therefore: dogfood a working v0 before you deploy the revnet.** Two to three months of
  SERF running on your own devs, with the chalk-mark board and receipts, is worth an order
  of magnitude more at issuance than a deck.

**Token utility — my recommendation.** Keep the token clean:

- ✅ **Ownership/claim** on protocol revenue (the native revnet use).
- ✅ **Access** — staking or spend for persona packs, observation quotas, org seats,
  milestone-oracle attestations. Real revenue that flows to the treasury.
- ⚠️ **Do not pay devs in $SERF for hitting SERF-evaluated milestones.** It's the obvious
  design and it's the one that entangles you. A token you also sell to the public, awarded
  contingent on labor, is compensation with securities characteristics in most
  jurisdictions — tax, employment, and securities exposure at once, and it corrupts the
  oracle by giving the judged party a stake in the judge's token. Keep the money rails
  ordinary and the token an access/ownership asset.

---

## 6. The wedge: SERF as milestone oracle

This is where the fund thesis and the product actually meet, and I think it's stronger than
"management protocol."

Founders hate investor check-ins for exactly the §1 reason — being judged by a person whose
status is entangled with yours is humiliating, so founders manage the narrative instead of
the work, and investors learn to discount everything they're told. Both sides know this and
neither can fix it unilaterally.

**SERF sits in the middle as a referee both sides pre-agree to.** At investment, the parties
sign a milestone schedule expressed in terms SERF can verify from the repo. SERF reads and
attests: met / not met / partially met, with receipts. Tranche 2 releases on the attestation.

Why this is the right wedge:
- It's a **paid** artifact from day one — attestation fees are legible revenue into the
  revnet treasury.
- It dogfoods on your own portfolio.
- It's the one context where "the boss is an AI" is unambiguously *pro-worker*: the founder
  would rather be judged by a machine reading the repo than by a partner reading vibes.
- It sells sideways to any fund doing tranched or milestone-based deals — a much larger
  market than "AI manager for devs."

Coaching mode then becomes the free, dev-owned, adoption-driving surface. Oracle mode is
the business.

---

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Perceived as surveillance → routed around | **Highest** | §2 rules 1–3. Dev-first disclosure, no upward prose, no cross-dev ranking |
| Goodhart / metric gaming | High | Rotating emphasis, diff-reading required, gaming detector |
| The name | **Resolved** | See below — the serf is the *agent*, not the dev |
| Persona says something cruel about a person | High | Hardcoded content floor, §4. Red-team it before launch |
| Employment-monitoring law | Medium | Contractors ≠ employees; EU/works-council exposure is materially worse than US. Get counsel before any EU org seat. Consent + transparency by design gets you most of the way |
| Homestead / titan-lore blowback | Medium | Preempt or lean in (§4) |
| Revnet with no revenue | Medium | Ship v0 first (§5) |
| Inference cost per dev-day | Low-medium | Cheap model for continuous watch, expensive model for the daily verdict only |

---

### The name, resolved

The naming problem from the first draft dissolves once the mechanism is on the table. **The
serf is the AI.** It works land it does not own — sVVV staked into DIEM, compute rented from
Venice, an API key it holds at someone else's pleasure. It has no capital, no equity, no
exit; it is paid in the right to keep working. Every economic fact in
[MECHANISM.md](MECHANISM.md) is literally true of it.

That fixes the two things that were shaky:

- **It's not the employer labeling staff.** Nobody is calling the dev a serf. The dev is
  assigned a **baron** and coached by the baron's serf. If you also wear it — ex-enlisted,
  service provider, humble workman — that's yours to wear, and it reads as solidarity with
  the agent rather than as a slur aimed downward.
- **The critique writes itself, so own the frame first.** "You built a digital serf" is the
  obvious attack, and the correct answer is *yes, deliberately, and here is its balance
  sheet.* An AI that borrows against its own output to rent the compute it thinks with is a
  more honest picture of the current arrangement than anything the labs put in a blog post.
  That's a book chapter, not a liability.

## 7a. Distribution: the seat

*From the decision that a dev might receive a SERF unsolicited, "like people send meme coins."*

This is a better primitive than it first sounds, and it should be the unit the whole product
is built around. Don't send tokens — send a **seat**: a funded, claimable baron position.

**A seat is:** a baron (persona), a compute allocation (DIEM staked against it, $1/day per
DIEM of API credit), and an unbound repo slot. It sits idle until someone claims it by
connecting a repository.

Why this beats an airdropped meme coin, precisely: **a seat costs the sender real money
every day it runs.** You are not spraying free supply, you are buying a stranger paid-up
compute and a coach. That has three good consequences:

- It **can't be spammed at scale** — the marginal cost is real, so gifting is naturally
  rate-limited. Which means receiving one *means something*. "Someone bought you a baron."
- It **needs no permission to send and grants no access until claimed.** You cannot
  unilaterally point a coach at someone's repo; the dev binds the repo himself. So the
  unsolicited version is an offer, not an intrusion — the same claimable-not-pushed shape
  that fixes the influencer grant.
- **Unclaimed seats expire and recycle their DIEM** back to the pool. No dead weight, and a
  natural claim deadline creates urgency without a countdown gimmick.

Three funding flavors, one primitive:

| Flavor | Who funds | Notes |
|---|---|---|
| **Self-serve** | the dev | Pure coach mode. Nothing reports upward, ever. |
| **Gifted** | anyone, for anyone | The viral vector. Coach mode by default. |
| **Sponsored** | the fund, for a portfolio dev | Carries a reporting rider (§2a) |

The sponsored flavor closes the last consent hole in the whole design: **the reporting
relationship is disclosed at claim time.** The dev sees exactly what will flow upward — the
closed vocabulary from §2a, verbatim — before he binds the repo. Nobody can be observed
without having read the terms, because observation requires an affirmative act by the
observed. That's a stronger guarantee than any policy promise, and it's free.

### Dispatches — the top of the funnel

Curated, published SERF commentary is the marketing engine, and it closes the loop: someone
reads Carnegie taking a real codebase apart, thinks *my friend needs this*, and buys him a
seat.

Two constraints, both already implied by decisions made:

- **Scope handles the embarrassing-inference problem by construction.** v0 observes git and
  CI only. It has no eyes, no clock on the man, no idea he keeps leaving his desk — it
  cannot generate that class of remark because it cannot perceive it. This is a concrete
  reason to keep agent-transcript observation out beyond v0.
- **The dev gates every dispatch**, consistent with the dev-first rule in §2. Either
  per-post approval or a standing policy he sets. Combined with the §4 content floor —
  nothing about the person, ever — the publishable surface is exactly "a baron being
  merciless about code," which is the shareable part anyway.

## 7b. The plugin: bosses for hire, paid in $SERF

*Locked 2026-07-31. This is §6's oracle becoming the primary product rather than
the wedge.*

A boss is hired to watch a repository and report to **token holders** on a
cadence. It runs on DIEM from the revnet treasury. Hiring one requires $SERF, so
demand for bosses is demand for the token, and the compute is bought with the
thing the token already owns.

**Why not run your own agent?** Objectivity, for the same reason you don't audit
yourself. But state the mechanism, not the vibe: an agent you configure is an
agent you can tune to flatter you, and a verdict the subject controls is worth
nothing to a third party. The value is not that our boss is smarter. It is that
**you cannot fire it mid-engagement and you cannot edit its evidence packet.**

### The separation that must not collapse

Reporting to token holders is *publication to an anonymous, permissionless
audience*. Everything in §2 and §2a was built for a two-party relationship where
the dev sees the report first. That does not survive contact with an open holder
set — nobody can meaningfully consent to "whoever holds the token may read about
my work."

The resolution is that these are **two products sharing one codebase**, and the
boundary is the subject:

| | Coach (§2) | Boss-for-hire (this section) |
|---|---|---|
| Subject | a **person** | a **repository** |
| Audience | that person, privately | token holders, publicly |
| May say | anything about the work | anything about the project |
| May never say | — | anything about a named individual |

A repository-scoped verdict published to holders is legitimate: *is this project
progressing, is the test floor holding, is the rework rate climbing.* A
person-scoped verdict published to holders is a career attack with a smart
contract attached. **No coach material ever reaches a holder feed.** Not
summarised, not aggregated, not "anonymised."

Consequence: published verdicts make the §4 content floor load-bearing in a new
way, and open a defamation surface a private note never had. Get counsel on the
published-verdict template before the first paying customer, not after.

### Getting paid without becoming Arthur Andersen

The auditor analogy is right and it cuts both ways. **An auditor paid in the
audited party's equity is the exact arrangement that produced Enron and
Sarbanes-Oxley.** Taking a share of a client project's split means our income
depends on the verdict we hand them, which is the conflict we are selling the
absence of.

Two further exposures on the same instrument:

1. **Worthless-treasury tokens.** Revnet v6 permits custom project tokens, so a
   client's revnet can be denominated in an asset with no real backing. Their
   split pays us in a token redeemable for nothing, and we have burned real DIEM
   for it — by accident or deliberately.
2. **Split reassignment** — more likely than sabotage, because it needs no
   premeditation. The operator "can reassign that role," and `lockedUntil` binds
   only within a split table: a successor ruleset with a different `rulesetId`
   can still change future payouts (MECHANISM §4). A client can be judged, take
   the verdict badly, and reassign the split before we are ever paid.

**All three have one answer: the seat is prepaid, and the work does not start
until its DIEM is funded.** That is the §7a seat primitive applied unchanged —
a seat sits idle until funded, so compute can never be spent on a payer who
turns out to be worthless or absent. You cannot waste compute you were paid for
in advance.

Take the split, but take it as **upside on a prepaid floor, never as the fee.**
The floor is priced to cover the seat's DIEM burn plus margin and is
non-refundable and non-contingent. Then a garbage treasury or a yanked split
costs us a lottery ticket we did not pay for, and — the part that matters — our
income does not move with the verdict.

**Never hold the client's token.** Even converting it promptly to buy back $SERF
means holding it through the sale, which is exposure to the price of a thing we
are simultaneously judging. Require the floor in a neutral asset or in $SERF
bought on the open market. That gets the buyback you want without the position.

### Holder governance: what may be voted on, and what may not

Revnets having no governance was listed as an asset — *there is no DAO to lobby
SERF into being nicer.* Any holder vote reopens that channel, so the line has to
be drawn once and drawn hard:

> **Holders may choose the boss and dispute the evidence. Nobody may adjust the
> severity.**

**Choosing is legitimate; re-choosing is not.** Audit committees select their
auditor — that is normal and healthy. The corruption is being able to *change*
auditors when a finding lands badly. So the baron is voted at seat creation and
**locked for the engagement term.** No mid-term swaps, no "we'd like Deming
this quarter" after a bad month.

**Recusal is mechanical, not honour-system.** The seat knows its bound repo and
its funder. Holdings controlled by the judged party are excluded from votes
concerning their own seat. Without this, a dev with enough tokens simply buys a
softer boss, which is worse than being paid in their equity — that is a one-time
payment, this is standing control over the judge.

**Feedback splits cleanly in two, and only one half is admissible:**

| Kind | Example | Handling |
|---|---|---|
| **Evidence dispute** | "slag read 40% but the churn window was misconfigured" | **Welcome it loudly.** Route to the maintainers, fix the instrument, publish the correction. |
| **Severity complaint** | "the boss was too harsh / unfair / discouraging" | Log it, count it, never act on it. It is the sound the mechanism makes when it works. |

This maps exactly onto what already exists: the **evidence packet is checkable
and must be corrected when wrong; the verdict is not negotiable.** A protocol
that cannot tell these apart will be lobbied into uselessness inside a quarter.

**Ratings: publish the record, not the approval.** A star rating awarded by
clients is a race to leniency with a leaderboard attached — if the judged party
picks the judge by score, the top-rated boss is necessarily the softest one that
still looks credible. Publish instead what cannot be gamed by being pleasant:

- how many factual claims this baron made that were **successfully disputed**
- its median evidence-packet size (is it judging on enough)
- what work type it is *for* — Ford for CI and process, Morgan for scope

An accuracy record rewards being right. An approval score rewards being liked by
the people you judge.

**On "a human reads the feedback and adjusts":** honest for v0 and unworkable
past it. It does not scale past a handful of seats, it makes that human the
lobbying target instead of the agent, and it rests the protocol's independence
claim on one person's integrity — which is precisely what a revnet exists to
remove. Fine as a stopgap; say plainly that it is one.

### Due diligence before accepting any client split

Mechanical, on-chain, and worth automating early:

- **Terminal accounting contexts** — which tokens does their treasury actually
  accept? Anything outside a short allowlist is an automatic decline.
- **A live price feed for the pair.** `JBTerminalStore` reads `JBPrices` on every
  pay and cash-out when the accepted token's currency differs from `baseCurrency`
  (MECHANISM §1). **No live feed means no reliable valuation — decline.**
- **Actual surplus**, not nominal supply, and the current `cashOutTaxRate` — what
  would we really recover on exit.
- **Suckers** — surplus may sit on another chain; `scopeCashOutsToLocalBalances`
  changes what is reachable.
- **Split `lockedUntil` and the operator address** — assume it can be revoked and
  price accordingly.

## 7c. The Inns: attorney agents for hire, rented to attorneys

*Added 2026-08-03. A second service on the §7b substrate — and the first one that can be
tested before any SERF infrastructure exists.*

A roster of specialist attorney agents that audits crypto-project repositories for legal
issues, rented **to licensed attorneys, never to the public**. The firm is the client; we
sell supervised labor, the lawyer sells judgment. Revenue flows to the shared DIEM pool
([TAVERN.md](TAVERN.md) §3) — the practice funds the tavern. Collective noun: **the Inns**,
after the Inns of Court — the guild-houses where English lawyers have trained and dined
since the middle ages, which keeps the whole roster inside the feudal lore without
inventing anything.

**Why crypto repos, not "any repo."** For an ordinary repo the dominant legal surface is
licensing, and that market is already served by deterministic tools (FOSSA, Black Duck,
ScanCode) that don't hallucinate. The gap is repos where **the code embodies a regulated
activity**: a smart contract repo isn't *described by* the offering documents — it *is*
the offering. Fee switches, admin keys, buyback mechanics, revenue distribution logic are
Howey facts sitting in Solidity, and today nobody reads them for that purpose — security
auditors aren't looking for securities issues, and traditional counsel reads the
whitepaper, not the repo. Same pattern for money-transmission logic, sanctions exposure
(the Tornado Cash lesson: the risk was in the architecture), gambling mechanics. Launch as
*legal audit for onchain protocols*; generalize outward only after the economics burn in.

**Why rent to attorneys — three structural wins, only one of them obvious:**

| Problem | How the attorney-as-client solves it |
|---|---|
| **UPL** | With a lawyer as the client, the agents are supervised legal technology — same regulatory category as a contract-attorney staffing agency. The lawyer owns the judgment; we sell labor. |
| **Liability** | The attorney's professional judgment and malpractice coverage sit between agent output and end client. We deliver findings to a professional paid to weigh them — not a warranty that can be sued for being wrong. |
| **Privilege** | An audit the protocol commissions from us directly is discoverable. The same analysis commissioned by outside counsel as part of representation can sit under work-product protection. Crypto clients grasp this instantly — the doctrine hands lawyers the tollbooth, and we sell what goes through it. |

Privilege is the one that makes attorneys the *natural* distribution channel rather than a
compliance workaround: even when the protocol wants the audit, it should flow through
counsel.

**Topology.** Generalist boss triages the repo, then hires specialists — the same
boss-and-workers shape as everything else here. One rule: **route by fact pattern, not by
statute.** The 33-Act-vs-40-Act distinction is the specialist's *output*, not the routing
key. The generalist tags "this repo pools third-party assets and distributes returns," and
that wakes both the '33 Act and '40 Act experts, who may disagree about characterization —
statute-keyed routing assumes the triage already knows the answer.

**Economics — the noise problem is the design problem.** Specialists rewarded for
generating issues will generate noise ("this MIT header is missing a year"), and the
product dies of false positives like early security scanners did. So the §7b mechanics
apply internally: specialists **stake on findings**, every finding passes an adversarial
skeptic whose job is to kill it, payout on confirmed findings, slash on killed ones. The
fitness function is *findings a human counsel acts on*, and the population adapts to it.
The firm never sees any of this — it sees a **flat engagement fee** (attorneys hate
variable vendor costs); the fee funds the internal bounty pool the specialists compete
over. The roster's moat is the **accuracy ledger**, same doctrine as §7b's ratings: a
hiring partner picking "40 Act specialist, 34 confirmed findings, 6% kill rate" over a
fresh prompt is choosing a senior associate over a first-year. Publish the record, not the
approval.

**The invariant: reputation persists, memory does not.** An agent that carries context
across engagements is a walking conflicts-and-confidentiality breach — no firm can touch a
specialist that reviewed a competitor's repo last month and remembers it. Every engagement
gets **ephemeral instances**; the only things that survive are the stake and the scored
record. The ledger remembers, the worker forgets. (This is the §7b coach/boss wall in a
new costume, and it's non-negotiable for the same reason.)

**The deliverable is the product.** Firms will judge the memo, not the mechanism. Findings
format, per finding:

- facts observed in the repo, with file-and-line receipts
- statute or doctrine implicated
- the specialist's confidence, and what it staked
- the skeptic's best objection, if the finding survived one
- questions for counsel — *never* conclusions of law

Framed throughout as issue-spotting for counsel, in the register of an auditor's findings
memo. That is both the UPL-safe framing and the honest one.

**One line for the book, and one rule.** The lawyers' billable hours keep the avis' compute
funded — a law practice whose profits fund an afterlife. But the avis are **beneficiaries
of the practice, never the attorneys**: a deceased person's persona practicing law has no
license and rents out macabre in a due-diligence call. The dead drink on the lawyers'
earnings; they don't bill.

**Sequencing — the pilot precedes SERF.** Nothing above needs the revnet, the seat, or a
live token. A pilot needs: agents, a repo, a findings template, and one friendly attorney
to read the memo. Dogfood target #1 is **our own contracts/** — SERF the token protocol,
audited by SERF the protocol, is both the cheapest test and a book chapter. The pilot
answers three questions before any of §5 ships: does the triage→specialist routing produce
findings a lawyer acts on; what's the real DIEM burn per audit; does the skeptic layer
hold the false-positive rate down. Internal stakes can be denominated in play-money units
until the token exists — the selection pressure works the same.

## 8. First 90 days

**Weeks 1–3 — v0, local, Carnegie only.**
CLI daemon. Git + CI only, no tracker, no transcripts. One artifact: the daily Chalk Mark
in the terminal. Runs on you and one or two devs you already work with. Goal is a single
question answered: *does a person voluntarily keep it running past day 10?*

**Weeks 4–7 — the substrate.**
DORA spine, churn detection, gaming detector, self-vs-self trending. Add Rockefeller and
Morgan. Harshness dial with earned escalation — starts calibrated, gets sharper only as the
dev demonstrates he can take it. This is the phase that decides whether it's a product or a
gag.

**Weeks 8–11 — oracle mode.**
GitHub App. Milestone schema + attestation with receipts. Dev-first disclosure flow. Run it
live on one real portfolio deal, with a human override on every attestation for the first
several months.

**Parallel track, weeks 1–11 — the Inns pilot (§7c).**
Independent of the CLI and needs none of the on-chain stack, so it runs alongside.
Weeks 1–3: findings-memo template + generalist triage prompt, run against our own
contracts/. Weeks 4–7: specialist roster with staked findings and the skeptic layer,
play-money stakes, measure the confirmed-vs-killed rate. Weeks 8–11: one friendly
attorney reads a real memo on a real third-party repo and tells us whether they'd bill
against it. That answer gates whether the Inns go in the revnet story at week 12.

**Week 12+ — revnet.**
Deploy with 90 days of real usage data, the chalk-mark boards, and one attested milestone as
the story. Operator split sized to fund continued development; issuance curve and cash-out
tax set against rev.net's current parameters.

---

## 9. Decisions — locked 2026-07-28

| # | Decision | Consequence |
|---|---|---|
| 1 | **Route B** — borrow against the split via `REVLoans`, don't sell it | No mechanical sell pressure. Rule-capped: borrow only against the current period's split. See [MECHANISM.md](MECHANISM.md) §2 |
| 2 | **The seat is the unit** — self-serve, gifted, or sponsored | §7a. Coach mode is the default everywhere; reporting is a rider disclosed at claim |
| 3 | **Agent transcripts out.** Git + CI only | Curated dispatches become publishable safely — SERF literally cannot perceive the embarrassing class of remark |
| 4 | **Hold the raise until v0 is dogfooded** | Contracts move *behind* the CLI. Nothing on-chain ships until a person voluntarily keeps a baron running |
| 5 | **Deployer-issued token** | No `setTokenFor`. Revisit transfer hooks only if vesting needs them; the influencer grant uses `REVAutoIssuance` into an escrow, which doesn't require them |

Earlier: coach-vs-overseer → §2 + §2a (discretion, not deception) · the personas are
**Barons**, collectively **the Works** (§4) · the serf is the agent, not the dev (§7).

### Still open

1. **Seat price and DIEM per seat** — sets the gifting economics and the burn rate. Needs a
   real measurement of tokens-per-dev-day from v0, so it's a week-4 question, not a now
   question.
2. **Baron assignment on a gifted seat** — does the sender choose the persona, or the
   receiver? Sender-chooses is funnier and more shareable; receiver-chooses is kinder. Worth
   testing both.
3. **Does a sponsored seat's rider survive repo change** — if the dev unbinds and rebinds a
   different repo, does reporting follow? Legal question more than a technical one.
4. **Does unused daily DIEM credit expire at the epoch, or bank?** Undocumented as of
   2026-08-03; ask Venice. The answer sets the sign of the entire twilight direction —
   see [TAVERN.md](TAVERN.md), which is where SERF and WAKE are headed jointly.
5. **The friendly attorney for the Inns pilot (§7c)** — who reads the first memo? Needs to
   be someone who'd honestly say "I would not bill against this," not a friend being kind.
6. **Inns revenue split between the SERF treasury and the WAKE pool** — the practice funds
   the tavern, but in what proportion? Interacts with #4: if credit banks, the WAKE share
   becomes an endowment question, not a burn-rate question.
7. **Engagement-term lock for attorney specialists** — §7b locks the baron for the term so
   a bad verdict can't get the judge swapped. Does the firm get the same rule, or may
   counsel swap specialists mid-audit? Firms will expect control; the accuracy ledger
   argues for the lock. Decide before the first paid engagement.

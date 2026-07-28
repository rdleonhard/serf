# $SERF — Revnet ⇄ Venice mechanism

*Verified against `rev-net/revnet-core-v6` and `Bananapus/nana-core-v6` @ HEAD, 2026-07-28.
File:line references are to those repos.*

---

## 1. Why there's no mechanism — the actual reason

You were right that it can't do what you described. The reason is more specific than
"missing feature," and it constrains the whole design:

**A revnet has no payouts. At all.**

`REVDeployer._makeLoanFundAccessLimits` hardcodes `payoutLimits: new JBCurrencyAmount[](0)`
(`src/REVDeployer.sol:299`) and only ever populates `surplusAllowances`, for loans. There is
no configuration surface that adds a payout limit later. Money paid into a revnet cannot
leave as a payout — ever. That's not an oversight, it's the guarantee that makes the token
backed.

Three consequences that kill the obvious designs:

1. **`JBSwapSplitHook` is unusable here.** It's a *payout* split hook — it swaps a payout's
   terminal token into another token. A revnet has no payouts, so it never fires. Don't
   build on it.
2. **The only split surface in a revnet is reserved tokens.** `REVStageConfig.splits` is
   wired to exactly one group — `JBSplitGroupIds.RESERVED_TOKENS`
   (`src/REVDeployer.sol:339`). So "the split" pays in **newly minted $SERF**, not in ETH or
   USDC. Your influencer split is a token grant, not a revenue share.
3. **`REVLoans.borrowFrom` is the only sanctioned way value leaves the treasury.** Burn
   $SERF as collateral, receive treasury funds. 10-year liquidation window
   (`LOAN_LIQUIDATION_DURATION = 3650 days`), a borrower-chosen prepaid fee, plus 1% to the
   $REV revnet (`REV_PREPAID_FEE_PERCENT`).

**What you *do* get** — the extension point you need is on the split itself. `JBSplit`
(`nana-core-v6/src/structs/JBSplit.sol`) carries:

- `hook` — an arbitrary `IJBSplitHook` that receives the split's tokens and can do anything
  with them. This is where your Venice pipeline lives.
- `lockedUntil` — with an important caveat, see §4.

And **custom tokens are confirmed**: `JBTokens.setTokenFor` (`nana-core-v6/src/JBTokens.sol:311`)
accepts a pre-existing ERC-20 if it has 18 decimals, the project has no token yet, and the
token isn't already bound to another project.

> **Decided:** ship the **deployer-issued** token, not a custom one. `setTokenFor` is a
> one-way door — once a project has a token it can never be replaced — so taking it only
> buys optionality you'd have to secure and audit up front. The influencer vesting uses
> `REVAutoIssuance` into an escrow contract (§4), which needs no transfer hooks at all, so
> the main reason to want a custom token doesn't apply.

---

## 2. Two routes from the split to DIEM

Venice mechanics, confirmed: stake VVV → sVVV; lock sVVV → mint DIEM at a rising Mint Rate
that climbs as DIEM supply approaches target and falls when DIEM is burned; each staked DIEM
= $1/day of API credit, perpetual, minimum 1/10 DIEM staked to draw credit. Locked sVVV
still earns 80% of standard yield, the other 20% to Venice. Emissions are on a declining
schedule (6M → 5M → 3M VVV/yr across 2026).

That last point matters: **locking sVVV to mint DIEM doesn't forfeit the yield, it taxes it
20%.** So the "emissions go to SERF" idea works and the lock is not exclusive with it. Good
— that was the part of your design most likely to have been impossible, and it isn't.

### Route A — sell the split

`SerfSplitHook` receives reserved $SERF → sells into the UniV4 pool → ETH → VVV → stake →
lock sVVV → mint DIEM → stake DIEM → API key to the agent.

- **Pro:** simple, never touches the treasury, no debt.
- **Con:** your own hook is a permanent, mechanical seller of your own token. It's visible
  on-chain, and holders will price it in. This is the version people will call a farm.

### Route B — borrow against the split ← **CHOSEN 2026-07-28**

`SerfSplitHook` receives reserved $SERF → `REVLoans.borrowFrom` with that $SERF as collateral
→ receives treasury funds → VVV → sVVV → DIEM → API key to the agent.

- **Pro:** no market sell pressure. The collateral is *burned*, not dumped into the pool.
  The outflow is the protocol's own sanctioned path. And it's reversible — repay out of
  protocol revenue (§3) and the collateral is reminted.
- **Con:** fees, a 10-year clock, and it draws on backing-per-token. Must be capped by rule,
  not by discretion — e.g. the hook may only borrow against the current period's split, never
  against accumulated position.
- **The lore is exact.** The serf borrows against his own labor to rent the land he works.
  That is the company store — Carnegie's and Pullman's actual practice — implemented as a
  native protocol mechanism rather than a metaphor. If the book needs one diagram, it's this
  one.

---

## 3. Profitability: the revenue loop already exists

You asked how the boss getting paid autonomously buys back revnet tokens. That primitive is
shipped: **`nana-buyback-hook-v6`**. It's a data hook that, on every `pay`, compares minting
new tokens through the terminal against swapping through a Uniswap V4 pool, and routes
through whichever is better for the project.

So:

    protocol revenue (attestation fees, org seats, persona packs)
        → SerfPaymaster
        → terminal.pay(revnetId)
        → buyback hook decides:
              market price cheap  → buys $SERF on UniV4      = autonomous buyback
              market price rich   → mints via terminal        = treasury grows, backing/token up

Either branch benefits holders. You don't have to build the buyback — you have to build the
paymaster that turns revenue into `pay()` calls, and attach the hook.

**Be clear-eyed about what "profitable" means here.** A revnet cannot distribute. There are
no dividends, because there are no payouts. Value reaches holders exactly two ways: the
cash-out floor rises as the treasury grows, and the cash-out tax transfers value from exiters
to stayers. That's the honest pitch and it's the book's thesis anyway — this is not a
cash-flow business wearing a token, it's a treasury that compounds.

---

## 4. The influencer allocation

You conflated two different locks. They're separate mechanisms:

- **`JBSplit.lockedUntil` locks the *configuration*, not the tokens.** It prevents the
  operator from reassigning that split. And per the struct's own docs, it's weaker than it
  looks: *"This lock is enforced only when rewriting the same split table. Queueing a
  successor ruleset with a different `rulesetId` can still replace future payout behavior."*
  So it is not an absolute guarantee to the recipient.
- **To make the recipient's tokens non-transferable**, the `beneficiary` must be a
  vesting/escrow contract, not their EOA. That's a contract you write.

**Better decomposition:** don't put the influencer on the ongoing split at all. Use
**`REVAutoIssuance`** (`src/structs/REVAutoIssuance.sol`) — a per-stage scheduled premint of
a fixed `count` to a `beneficiary` on a specific `chainId`, claimable once per stage, no
payment required. That gives the influencer a clean one-time allocation into a vesting
contract, and leaves the ongoing operator split entirely for funding compute. Two purposes,
two mechanisms, no interference.

**On the unsolicited-airdrop play** — you know this area better than I do, so just the flag:
sending tokens to someone who didn't ask is fine. The exposure is using their name or
likeness in marketing such that it implies endorsement — false association under Lanham
§43(a), plus right-of-publicity in the states that have it. Locking the grant makes it
marginally worse, since the recipient can't dump it to visibly repudiate you. Cheap
mitigation: make it **claimable, not pushed**, and never put the name in marketing copy.

---

## 5. What to build

**Sequencing:** none of this ships until the v0 CLI is dogfooded (PLAN §9, decision 4). The
contracts are the *second* build, not the first — the raise has nothing to accrete until
there's a product generating `pay()` calls.

| Contract | Role |
|---|---|
| `SerfSplitHook is IJBSplitHook` | Receives reserved $SERF, posts it as collateral to `REVLoans.borrowFrom`, forwards proceeds to `SerfLand`. Rule-capped to the current period's split; no discretionary parameters. |
| `SerfLand` | Holds VVV/sVVV/DIEM. Stakes, locks, mints, re-stakes DIEM. Allocates credit per **seat** (PLAN §7a) and recycles unclaimed seats' DIEM. Grants API keys to the agent's key manager. This is the "land." |
| `SerfSeats` | Seat registry: funded / claimed / bound-repo / expired. The gifting surface. |
| `SerfVest` | Escrow beneficiary for the influencer `REVAutoIssuance`. Claimable, time-locked. |
| `SerfPaymaster` | Converts protocol revenue into `terminal.pay()` calls so the buyback hook fires. |
| — | Buyback hook: **use `nana-buyback-hook-v6` as-is.** Don't write one. |

Deploy-time decisions that are irreversible, so get them right: stage schedule
(`initialIssuance`, `issuanceCutFrequency`, `issuanceCutPercent`), `cashOutTaxRate`,
`splitPercent`, and `operator`.

**Route B's live risk to watch:** `SerfLand`'s debt is denominated against a burned-collateral
position whose recoverable value tracks the cash-out floor, while its asset (DIEM) is
consumed continuously at $1/day per staked DIEM. If seat demand outruns revenue, the hook
borrows against a rising floor to fund a constant burn — which is fine while the treasury
grows and is a slow bleed if it doesn't. Cap seats by *funded* DIEM, never by expected
revenue, and the failure mode is "no new seats" rather than "insolvent land."

---

## 6. One correction to "put the protocol in charge"

Revnets are ownerless in the ordinary sense, but they are not humanless. The **operator** is
a real, persistent, human-controlled surface: it receives the production splits and *only the
current operator can replace itself* (`REVConfig` docs). `revnet-core-v6/README.md` lists as
an integration trap: *"operators are constrained, not equivalent to general protocol
governance."*

For a code deference agreement, that's the exact seam that needs drafting — what the operator
can do, what it contractually undertakes never to do, and what happens on reassignment. A
document that says "the code governs" without enumerating the operator envelope is
describing a system that doesn't exist.

*(Credit note: code deference agreement — Gabe Shapiro.)*

---

Sources for the Venice mechanics: [Introducing Diem as Tokenized Intelligence](https://venice.ai/blog/introducing-diem-as-tokenized-intelligence-the-next-evolution-of-vvv) ·
[VVV staking FAQ](https://featurebase.venice.ai/help/articles/2413543-how-does-the-venice-token-vvv-work-and-what-are) ·
[How to Mint DIEM](https://veniceaiguide.com/how-to-mint/)

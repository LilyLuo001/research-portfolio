# G8 — the registered functional form and sign, written before any outcome is opened

**Status: DECIDED UNDER DELEGATION 2026-08-19, awaiting counter-signature.** Written in
response to safeguard 2, which required the theoretical reason for a signed prediction *or*
a different functional form, chosen before G8 outcomes are accessed. No G8 outcome has been
computed; no ETF-mechanics data exists in the repo.

## The challenge, and the honest answer

v2.3/v2.4 registered **a₁ > 0 in signed L_tilt^pre = β_b^LOO − β_i**. Asked to write the
theory behind that sign, I do not think it holds. Stating why is more useful than defending
the earlier choice.

**What the signed lever means.** L_tilt is a *mismatch*: how much more (or less) the basket
responds to a macro surprise than the stock does on its own. Its **sign carries direction** —
L > 0 means refraction pulls the stock's macro response *up* toward the basket, L < 0 pulls
it *down*. That directional content is exactly what the headline γ needs, and it is why the
signed lever belongs in SPEC-MAIN.

**What G8's outcome measures.** φ is the sensitivity of a constituent's next-day residual
return to the ETF's creation/redemption flow, on non-FOMC days. That is a **connectivity
magnitude**: how hard does basket-driven arbitrage flow push this stock? It is governed by
how much of the flow lands on the stock (basket weight), and by price impact per unit of
flow (illiquidity). Both are magnitudes. Neither has a natural sign in β_b^LOO − β_i.

**Why a signed prediction would actually be wrong-headed here.** Consider two constituents
with mismatches of equal size and opposite sign — one whose own macro beta sits well below
its basket's, one well above. The arbitrage channel pushes both when the AP trades the
basket; nothing in the mechanism says the first should absorb *more* flow pressure than the
second. A signed prediction asserts an asymmetry the mechanism does not generate. Worse, it
would be passed or failed largely by whatever correlation happens to exist between β_i and
liquidity, which is a nuisance relationship, not the claim.

## Registered form

> **PRIMARY: a₁ > 0 in |L_tilt^pre|.** Constituents whose pre-conversion macro response is
> most mismatched from their basket's are the ones with the most *scope* to be moved by
> basket-driven flow, so connectivity should rise with the magnitude of the mismatch.
> One-sided, because the mechanism has a direction even though the lever's sign does not
> enter it.

**Secondary, reported and never decisive:**

1. **Signed L_tilt^pre**, two-sided, as a diagnostic. If the signed relation is strong while
   the magnitude relation is weak, that is evidence the measure is picking up a beta–liquidity
   nuisance correlation rather than connectivity, and it is reported as such.
2. **Basket weight** as a covariate in the same regression — not as the primary (it is
   near-mechanical in holdings) but as the benchmark |L_tilt| must beat: if |L_tilt^pre| adds
   nothing over basket weight, the lever is redundant and the paper says so.
3. **Linearity.** The primary is linear in |L_tilt^pre|. A quintile specification is reported
   alongside so a monotone-but-nonlinear relation is visible, but the **decision rule keys on
   the linear coefficient** — chosen now precisely so a nonlinear form cannot be adopted after
   seeing a disappointing linear one.

## What this does and does not change

- **SPEC-MAIN is untouched.** The headline γ keeps the *signed* lever, where direction is the
  economics. This memo governs the G8 validation only.
- **The G8 decision rule is unchanged in structure:** primary significant with the predicted
  sign → licensed; otherwise retired, with re-entry only via the external-sample or
  cross-fitting route.
- **Nothing was observed to make this choice.** The repo contains no ETF shares-outstanding
  series, so φ has never been computed for any stock.

## What the PI is signing

That G8's licensing decision keys on **|L_tilt^pre|**, linear, one-sided — and that the
signed version, basket weight, and the quintile form are reported as secondary evidence that
cannot overturn the primary. If you prefer the signed form, say so now: after the first φ is
computed, the choice is no longer free.

---

## Addendum, 2026-08-19 — two corrections to this memo, and the theoretical bridge

### Correction 1: the return outcome is not a magnitude test

This memo argued for |L_tilt^pre| on the ground that connectivity is a magnitude concept.
That reasoning is right about *connectivity* and wrong about *the outcome it was attached
to*. `CR × |L| → r_{t+1}` is a **signed price-persistence response**: it measures how much
of a flow-driven price move is still present the next day. It can be **zero or negative
while arbitrage connectivity is strong** — price impact fully absorbed within the session
leaves nothing to find at t+1, and an overshoot that reverses gives a negative coefficient.
A magnitude prediction cannot be tested on a signed persistence outcome.

**Revised registration.** The G8 **primary** is now a **trading-connectivity** outcome —
constituent abnormal volume or order imbalance around creation/redemption activity — where
"more connected ⇒ larger response" is a well-founded magnitude prediction. The return-based
result becomes **price-response corroboration**, and it cannot license the measure on its
own. `g8_first_stage.verdict()` refuses to license on the corroborating outcome class.

Its sign becomes interpretable only if a timing model establishes what next-day persistence
*should* look like under the mechanism. Until then it is reported without a directional
claim.

### Correction 2: the theoretical bridge, stated rather than assumed

G8 and the headline use the lever differently, and success in one does **not** transfer to
the other:

| | G8 validation | Headline (SPEC-MAIN) |
|---|---|---|
| Form | **\\|L_tilt^pre\\|** | **signed L_tilt^pre** |
| Claim | this stock is strongly *connected* to the ETF's arbitrage network | the wrapper pulls this stock's macro response in a *particular direction* |
| Prediction | magnitude: more mismatch ⇒ more trading response | direction: L > 0 pulls the response up toward the basket, L < 0 pulls it down |

**The separate economic prediction that gives the sign meaning.** Refraction says a
constituent's post-conversion macro response moves *toward its basket's* response. The
basket's response is β_b^LOO and the stock's own is β_i, so the direction of the pull is the
sign of (β_b^LOO − β_i) by construction — a stock whose basket reacts more strongly than it
does is pulled up, one whose basket reacts less is pulled down. That is a claim about
**where the response is dragged**, and it requires the arbitrage channel to be *transmitting
the basket's common exposure*, not merely to be *active*.

**So G8 licensing in absolute value does not validate the signed headline.** It establishes
that the channel exists and that |L_tilt^pre| ranks connectivity through it. The signed
prediction is tested only by the headline γ itself. If G8 licenses the measure and the
signed γ comes back with the opposite sign, that is evidence the channel transmits something
other than basket exposure — a finding, not a validation failure — and the paper must say so
rather than reinterpreting the lever after the fact.

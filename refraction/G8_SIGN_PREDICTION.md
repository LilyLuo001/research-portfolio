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

# W3 reconciliation — the v3 packet is primary; DWA transport is demoted

**Status:** recommendation with reasoning, recorded for PI signature. Both
underlying packets remain `NEED_HUMAN`; this does not sign either.
**Date:** 2026-08-23.
**Reconciles:** `dax/mapping/ONET_ALIGNED_BENCHMARK_V3_PI_DECISION_PACKET_2026-08-23.md`
against `dax/memo/W3_DECISION_dwa_transport_2026-08-23.md`.

## Decision

**The v3 O*NET-aligned bridge benchmark is the primary direction.** The DWA
transport proposed in the W3 decision memo is **withdrawn as primary** and
retained as a secondary robustness construction, conditional on the held-out
transfer validation described in section 3.

This decision goes against the memo I wrote earlier today. The reason is in
section 2, and it is not a matter of taste.

## 1. The two packets are not at the same level

They read as competitors because each nominates a primary, but they answer
different questions:

| | v3 packet | W3 memo |
|---|---|---|
| answers | what is the estimand, and how is it measured | how does a measurement reach 19,259 O*NET tasks |
| instrument | new instances built at the O*NET work-product boundary | GDPval, routed through shared DWAs |
| coverage | bounded by construction cost; S1 gave 13 PASS of 120 | 0.4169526 of allocable wage mass (upper bound) |

The W3 memo assumed the hard problem was **retrieval** — how to find, for an
O*NET task, a measurement that applies to it. The v3 packet identifies the hard
problem as **validity** — whether a measurement taken at one work-product
boundary licenses a claim about another. On that framing the v3 packet is
correct and the W3 memo is answering the easier question.

## 2. Section G of the v3 packet defeats DWA transport as a central mechanism

> "A GDPval whole-task score cannot be copied, scaled, or averaged into an
> O*NET task probability without new held-out validation of performance
> transfer at the same task boundary."

That condition applies to DWA transport, and the W3 memo does not satisfy it.

Routing through Detailed Work Activities fixes *coverage*: it explains how a
GDPval measurement can be associated with an O*NET task at all, and 186× the
direct-match reach is a real result. It does **not** fix *transfer*. A GDPval
task remains a composite professional assignment; an O*NET task remains a
narrower activity. Sharing the DWA "prepare research reports" does not
establish that a model which completed the GDPval assignment would complete the
O*NET task, because scope, difficulty, deliverable and failure mode all differ.

**The unit mismatch was not solved. It was moved one level up.** The DWA layer
made it auditable and much better covered; it did not make it valid. A
coverage figure without a transfer warrant licenses nothing, and I said so of
the 0.417 when reporting it — that caution turns out to cut against my own
proposal.

The v3 estimand is also simply more complete. Section A prices human
assistance, review, retry, residual work and expected failure loss, requires
the complete deliverable to pass a frozen criterion, and normalises over the
full eligible task frame rather than the benchmarked subset. The W3 memo
assumed the simpler `A_tom` crossing rule and inherits none of that care.

## 3. What the DWA work is still for

The measurement is not wasted, and it should not be discarded with the
proposal.

1. **It is the value-of-information estimate for ever validating transfer.**
   0.4169526 of allocable wage mass is the ceiling GDPval could reach *if* the
   held-out transfer validation in §G succeeded. That ceiling is high enough
   that running the validation is worth considering, which was not knowable
   before the bound existed.
2. **It bounds a secondary robustness construction.** The design memo already
   carries Tolan-style and Eloundou-style mappings as independent robustness
   constructions. DWA transport belongs in exactly that slot, and it is better
   evidenced than either, provided every figure carries "upper bound, transfer
   unvalidated".
3. **It retires direct matching on evidence.** Mapping A reached 0.0022461 of
   allocable wage mass. That is now a measured comparison rather than an
   impression, and it holds whichever primary is chosen.

Under §G's own terms this places DWA transport in the `F`
descriptive/sensitivity category. That is where it belongs until transfer is
validated, and the packet is right to put it there.

## 4. What carries over from the W3 memo

These survive the demotion and apply to whichever primary is signed:

- **The bound-inversion critique.** The v3 `non_evaluable_rule` upper bound is
  `1 - B(1 - E)`, which is *decreasing* in the evaluable share: occupations
  with the least evaluable mass receive the highest upper-bound exposure,
  inverting the treatment ordering. Setting `center: None` is right; the upper
  rule still needs repair. See `direction_review_2026-08-23.md` §1.
- **Bound the dose path, not the level.** Occupation fixed effects absorb the
  time-invariant unmeasured component, so the object needing bounds is
  `dN_ot`, not `N_ot`. See the same review, §2.
- **Sequencing.** Capture is deadline-bound; benchmark construction is not.
  The v3 packet §M agrees and says to freeze early enough for 2026-10-23.
- **Provenance discipline.** The v2 labels are single-annotator; S1 is
  `UNSIGNED` with `formal_s1_gate_result: UNRESOLVED` and descriptive mass
  shares. Those qualifiers travel.

## 5. Consequences for the W3 decision memo

`W3_DECISION_dwa_transport_2026-08-23.md` should be signed **rejected as
primary** and retained in the record. Its D2 (weakest-link aggregation), D4
(dual-channel and PI-DECISION 7 audit) and D7 (reporting rule carries the
basis) remain sound and can be lifted into a secondary-construction packet if
one is ever authorized.

The 220 GDPval→DWA annotations are **not purchased now**. They buy coverage for
a transport whose validity is unestablished, and under the v3 primary they are
not on the critical path. Cost was never the obstacle — roughly 831,000 input
tokens across two vendor families — but relevance now is.

## 6. Signature

    PI signature: ______________________  Date: ____________

    [ ] agreed — v3 packet primary, DWA transport secondary and conditional
    [ ] disagreed — DWA transport primary, with §G transfer validation
        prospectively scheduled before any production use
    [ ] neither — return both packets

Recorded by the DAX seat on delegated authority for the reconciliation only.
Both underlying packets still require the PI's own signature.

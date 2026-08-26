# Y5 — Manuscript, appendix, replication package

*Prepend `Y0_CONTEXT_PACK.md`. Requires Y4 complete.*

## Target

25–35 pages. 3–4 principal figures, 4–6 main tables, one measurement appendix,
one replication package.

## Structure

1. **Introduction.** The claim in the literature; why measurement decides
   whether it can be evaluated in public data; what this chapter establishes.
2. **Data and measurement.** CPS panel; the four public exposure measures; the
   vintage problem and its repair. This section carries the chapter — it is not
   preliminaries.
3. **Design.** The frozen specification, the pre-commitment, and the MDE. State
   plainly that the specification was frozen before estimation and point to the
   commit.
4. **Results.** Tables 2–6 in order.
5. **What the data can and cannot establish.** The bounding argument: coverage,
   vintage, telework collinearity, each quantified.
6. **Conclusion.**

**Appendix A — measurement.** The exposure-gate audit, repaired: common
support, SOC vintage, residual concentration, leave-one-out, the named
occupations supplying identifying variation.

## Framing — decided in advance, per `RESEARCH_PLAN_v1.md` §3

Per `RESEARCH_PLAN_v1.md` §3, three branches, all written from the same tables:

- **A material decline** → the public-data test corroborates the
  proprietary-data literature, with a magnitude and a stated MDE, under a frozen
  specification.
- **A null** → an **informative** null. With the MDE stated, this says the
  effect is smaller than the published estimates, not that the data could not
  see it. **The text must say this explicitly** — it is the chapter's
  contribution and must not be left for the reader to infer.
- **Rules A/B/C disagree** → a finding about the fragility of occupation-level
  exposure measurement, reported as such.

`RESULTS_NOTE.md` from Y4 already recorded which branch applies. Do not revisit
that decision.

## Claims you may not make

- No general-equilibrium employment claim.
- No firm-level mechanism. The data cannot observe hiring decisions.
- No causal claim about AI adoption. Exposure is technical feasibility, not
  realised adoption.
- No novelty claim beyond what Y2 established with locators. The vintage
  figure is the cost of an exact-code merge, never a gap in the measures —
  `CORRECTION_2026-08-25_vintage_gloss.md`.
- Never "100% power". The MDE with its bootstrap interval and the DGP's
  assumptions, always.

## Replication package

- All code, public inputs, receipts, lineage sidecars.
- **No licensed microdata.** Ship the IPUMS extract *specification* and the
  extract id so a reader with their own IPUMS account can rebuild the panel.
- A `REPRODUCE.md` giving the exact command sequence Y1 → Y5, including
  `yax/gates.py` and its expected all-PASS output.
- Verify the package builds from a clean clone with no private path. If it does
  not, that is a bug in the package, not a limitation.

## Definition of done

- Manuscript compiles, all tables and figures referenced in text.
- Every number in the text traceable to a receipt.
- Replication package builds clean.
- `pytest -q` green.

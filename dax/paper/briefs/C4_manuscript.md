# C4 — Manuscript, appendix, replication package

*Prepend `C0_CONTEXT_PACK.md`. Requires C3 complete.*

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

## Framing — decided in advance, per `CHAPTER_SCOPE_v1.md` §3

- **If the estimates are informative:** a robustness paper. Which measures
  sustain the finding, which do not, what drives the disagreement.
- **If the estimates are imprecise:** a bounding paper. Nationally
  representative data cannot adjudicate this, and here is exactly why.

Same tables, same figures, one different framing sentence. `RESULTS_NOTE.md`
from C3 already recorded which branch applies. Do not revisit that decision.

## Claims you may not make

- No general-equilibrium employment claim.
- No firm-level mechanism. The data cannot observe hiring decisions.
- No causal claim about AI adoption. Exposure is technical feasibility, not
  realised adoption.
- No novelty claim about the vintage finding **until audit item 10 is done**.
  Verify against the literature first; if it is documented, cite it and report
  the magnitude anyway. The magnitude is the contribution either way.

## Replication package

- All code, public inputs, receipts, lineage sidecars.
- **No licensed microdata.** Ship the IPUMS extract *specification* and the
  extract id so a reader with their own IPUMS account can rebuild the panel.
- A `REPRODUCE.md` giving the exact command sequence C1 → C4.
- Verify the package builds from a clean clone with no private path. If it does
  not, that is a bug in the package, not a limitation.

## Definition of done

- Manuscript compiles, all tables and figures referenced in text.
- Every number in the text traceable to a receipt.
- Replication package builds clean.
- `pytest -q` green.

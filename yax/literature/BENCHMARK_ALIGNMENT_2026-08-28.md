# Test C benchmark-alignment audit

**Audit date:** 2026-08-28  
**Outcome seal:** intact; no protected post-period YAX outcome was opened.  
**Result:** `BLOCKED_NO_COMMON_SCALE_BENCHMARK`

## Binding question

The owner-signed rule is:

    SESOI = 25% × |final literature-comparable Q5–Q1 benchmark|

The rule permits a number only when the published benchmark matches Test C on
the age band, employment-stock outcome, Q5–Q1 contrast, young-relative-to-pooled-
older estimand, unit, and functional scale.

## Closest published benchmark

Brynjolfsson, Chandar and Chen, *Canaries in the Coal Mine? Six Facts about the
Recent Employment Effects of Artificial Intelligence*, revised 2026-08-12,
Stanford Digital Economy Lab working paper:

- source: <https://digitaleconomy.stanford.edu/app/uploads/2026/08/Canaries_August2026.pdf>
- SHA-256: `c8d2e5c4ccc0de7ef977c191c144726d6073e164b33f30397fcb0090165d2bdf`
- data endpoint in the paper: June 2026.

The paper reports two prominent magnitudes. Neither is the signed-off benchmark.

| Candidate | What it measures | Why it cannot generate the SESOI |
|---|---|---|
| **19%** | Descriptive kept-pace shortfall for ages 22–25: the two most exposed quintiles versus the three least exposed, November 2022 to June 2026 (pp. 10–12) | Not Q5–Q1; no pooled ages 26–65 comparison; not the Test C estimator or log/PPML scale |
| **−0.179** | Table 1 Panel A: employment-weighted occupation-level long-difference coefficient for Q5 versus Q1 **within ages 22–25**, percent change from November 2022 to June 2026 (pp. 12–13) | Matches the young band, stock outcome and Q5–Q1 contrast, but not the young-relative-to-pooled-26–65 estimand and not the saturated cell-stock PPML/log scale |

Table 1 reports older groups separately, not as YAX's pooled ages 26–65
comparison. Its Q5 coefficients are −0.048 (26–30), −0.014 (31–34), 0.001
(35–40), 0.031 (41–49), and −0.009 (50+). Those coefficients cannot be
mechanically pooled into YAX's coefficient: the necessary cell weights and
joint nonlinear estimator are not published, and YAX's target is a saturated
young-relative coefficient rather than a difference between separately fitted
long differences.

## Alignment table

| Required dimension | BCC 19% | BCC −0.179 | YAX Test C | Exact match? |
|---|---|---|---|---|
| Young age band | 22–25 | 22–25 | 22–25 | yes |
| Outcome | employment stock | employment stock | occupation × age × month employment stock | broadly yes |
| Exposure contrast | Q4+Q5 vs Q1–Q3 | Q5 vs Q1 | Q5 vs Q1 | only −0.179 |
| Comparison age | none | none; older fitted separately | pooled 26–65 | **no** |
| Estimand/unit | descriptive growth gap | occupation-level percent-change long difference, separately by age group | saturated occupation × age × month stock model, young relative to pooled older | **no** |
| Functional scale | relative kept-pace percentage | percent-change coefficient | log/PPML coefficient | **no** |

## Decision

No exact published benchmark was located in the latest-version literature
audit. Therefore:

1. the numerical SESOI remains undefined;
2. 19% and −0.179 are explicitly rejected as shortcuts;
3. the outcome-blind paired simulation may estimate `SE(Delta)`, covariance,
   the paired null distribution, and `MDE_Delta,80`;
4. it may **not** populate the primary equivalence interval, equivalence power,
   or benchmark-fraction grid;
5. `paired_delta_power` and the v1.1 freeze remain blocked.

This is not a discretionary power failure. It is enforcement of the owner's
common-estimand rule. Substituting either headline magnitude would silently
change that rule after sign-off.


# Gate 2 implementation inventory

Prepared 2026-09-06 without reading protected data or running outcome models.
Gate 2 execution remains blocked until Gate 1 closes.

## Scope boundary

The provisional Gate 1 aggregate contract (468 occupations by 114 observed
months) can support the canonical support, accounting, conditioning, and
dynamic analyses. It cannot support the broader beta-valid universe, detailed
age/enrollment analyses, or occupations excluded solely by the Webb control.
Those require separately specified aggregate products; the canonical Gate 1
object must not be widened retroactively.

## Byte-locked reusable references

These are algorithm references, not V3-valid production runners. They import
historical builders, contain obsolete solver paths or hard-coded targets, and
in some cases rescan microdata.

| Role | Reference | SHA-256 |
|---|---|---|
| Within-family profiles, joint tests, information, LOFO, common draws | `yax/revision/substantive_r3_20260905/within_family/run_within_family.py` | `b16916bb3484926f15fd195fee2e5bffe8601f695427f52d08440a8c0b201a71` |
| Event regressors, covariance/influence, simultaneous inference | `yax/revision/substantive_r3_20260905/dynamics/run_dynamics.py` | `df2f54712dd763d2fd747c73ef68f164038e3db0a3a4771846d4bc2b325e8bd2` |
| Broader-support construction and paired Webb comparisons | `yax/revision/substantive_r3_20260905/architecture/run_architecture.py` | `700eea188371bf34f7543d1cfd37da8a82ae5b7b4072ec822666d9fb82187a77` |
| Matched-support and paired conditioning plumbing | `yax/revision/substantive_r3_20260905/characteristics/run_characteristic_conditioning.py` | `7135eff4b63873386a31f4e2e388a30da896f792e2949591e4e64a61f58c254b` |
| Later age/enrollment/industry scaffolding | `yax/revision/substantive_r3_20260905/heterogeneity/run_heterogeneity.py` | `8985b044ae8d02f9ee496da41f74e62a870b00fd34c6112a32e0746e9939831a` |

## Required authenticated packages

1. **Support:** 22-by-5 matrix, graph/rank evidence, direct-tail membership,
   supported heterogeneous contrasts, full Q2--Q5 and continuous models,
   own- and fixed-reference-curvature information diagnostics, broader-support
   fixed-cutoff versus reclassified-cutoff results, LOFO/influence, and raw plus
   readable paths.
2. **Accounting:** four tail stock levels, exact log-stock identity, symmetric
   family-composition decomposition, closure checks, and explicit handling of
   zero denominators without pseudocounts or dropped mass.
3. **Dynamic reconciliation:** frozen static/dynamic functionals, full
   coefficient/covariance/influence objects, nesting and pseudo-stock audits,
   reference-invariance transforms, pretrend blocks, onset, and seasonality.
4. **Conditioning:** common-support 2-by-2 baseline/computer/family-month/
   combined models, raw and standardized computer coefficients, full
   covariance and paired movements, a smaller characteristic block, and
   separately labelled industry-cell results.

## Required pre-result tests

- complete grid, support graph, and rank;
- fixed versus reclassified cutoff separation;
- exact accounting closure, including adversarial zero-denominator cases;
- equal-occupation estimand validation;
- identical-support and common-draw validation for the 2-by-2 design; and
- dynamic rebasing, nesting, and pretrend-block rank.

## Binding cautions

- D05--D07 age/enrollment work belongs to Gate 4 under the execution sequence.
- C04--C05 require Gate 3 inference/generated-regressor work and cannot be
  treated as Gate 2 completion.
- December 2022 is retained in the aggregate archive but omitted in these
  estimation models; October 2025 remains missing and is never interpolated.
- Broader-support differences are descriptive unless common support and common
  draws justify paired inference.
- A pooled direct-tail coefficient is not an average of family-specific effects.
- Gate 1 family assignments and numerical adjudications are binding inputs and
  must not be recreated locally.

Expected compute after Gate 1: minutes for support/accounting, generally under
30 minutes for conditioning, roughly 45--120 minutes for dynamics, and a pilot
before committing to a full within-family/influence bootstrap that may take
from tens of minutes to several hours.

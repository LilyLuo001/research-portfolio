# I07 linked-household full-refit sensitivity

Status: **VERIFIED**

The SCC execution completed 399 positive-CPSID multiplier draws with zero
failed pooled or family-month refits. Each mean-one Exponential multiplier is
held common across every observed month, co-resident record, and fractional
crosswalk descendant belonging to that CPSID. The calculation is a
released-weight repeated-sample sensitivity. It is not CPS design-based
inference because public Basic Monthly CPS extracts do not supply the original
PSU/stratum design variables or suitable replicate weights.

| Label construction | Target | Estimate | Sensitivity SD | Basic 95% interval |
|---|---|---:|---:|---:|
| Fixed | Pooled | -0.1321 | 0.0271 | [-0.1865, -0.0794] |
| Fixed | Family-month | -0.0217 | 0.0478 | [-0.1212, 0.0587] |
| Fixed | Family-month minus pooled | 0.1104 | 0.0378 | [0.0362, 0.1753] |
| Regenerated pre-period | Pooled | -0.1321 | 0.0273 | [-0.1864, -0.0762] |
| Regenerated pre-period | Family-month | -0.0217 | 0.0484 | [-0.1236, 0.0665] |
| Regenerated pre-period | Family-month minus pooled | 0.1104 | 0.0381 | [0.0355, 0.1771] |

Regenerating pre-period exposure quintiles and Webb normalization changes a
median of two occupations per draw (maximum five); 92.5% of draws reclassify
at least one occupation. Despite this, the fixed- and regenerated-label
sensitivities are nearly identical. Mean bootstrap shifts are small: 0.0010,
0.0021, and 0.0011 for the fixed pooled, family-month, and paired targets, and
-0.0003, -0.0005, and -0.0002 when labels are regenerated.

The bootstrap-of-bootstrap maximum endpoint Monte Carlo standard error is
0.00820, below the declared 0.01 target. An independent public-output validator
recomputed every batch hash, the 399-draw inventory, all six reported
summaries, both basic-interval endpoints, and the endpoint Monte Carlo errors.

These intervals are not mechanically added to occupation- or family-cluster
variance. They show that the central qualitative contrast is not an artifact
of treating repeated CPS households or pre-period labels as fixed, under this
explicit multiplier approximation. They do not recover unavailable CPS design
uncertainty.

## Evidence

- Design: `SCIENTIFIC_DESIGN_DRAFT.md`
- Code: `run_household_refit_batch.py`, `summarize_household_refits.py`, and
  `validate_household_outputs.py`
- Public run: `runs/gate3_household_0399_20260908/`
- Summary: `summary_0399/HOUSEHOLD_REFIT_SUMMARY.csv`
- Independent validation:
  `summary_0399/INDEPENDENT_VALIDATION.json`

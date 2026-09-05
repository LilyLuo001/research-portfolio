# BASE-03 findings: fully rebuilt corrected-treatment baseline

Status: **post-outcome exploratory; not part of confirmatory YAX v1.1**

Final SCC execution after the durable-receipt fix: job `7468725`, exit status
0, 64 seconds wall time, 1.899 GB maximum virtual memory.

Self-check: **PASS**, 21 checks

## Result

| Outcome calendar | Treatment construction | Occupations | Q5-by-post coefficient | 95% wild-score interval |
|---|---|---:|---:|---:|
| historical 108 months | historical full-static weights | 468 | -0.131074 | [-0.217779, -0.044369] |
| corrected 113 months | historical full-static weights | 468 | -0.134554 | [-0.222643, -0.046465] |
| corrected 113 months | corrected 71-month pre-period weights | 468 | **-0.132109** | **[-0.220565, -0.043654]** |

The rebuilt universe contains the same 468 occupations as the historical
production support. This is therefore not a support-expansion result. Restoring
the calendar while carrying the historical treatment moves the coefficient by
-0.003480 (paired 95% interval [-0.007943, 0.000983], p = 0.1317). Rebuilding
the treatment on the corrected pre-period then moves it back by +0.002445
(paired 95% interval [-0.001269, 0.006158], p = 0.3529). The design does not
detect either paired difference.

The full rebuild changes nine native quintile assignments. The changed codes
are 0845, 1350, 3620, 3655, 3710, 4461, 4500, 5410, and 8730; their names and
both classifications are preserved in `results/COMMON_SUPPORT_RECLASSIFICATION.csv`.
The first three historical beta cut points change from 0.162562, 0.328947, and
0.461538 to 0.153846, 0.324615, and 0.456522; the fourth remains 0.537037.

## Pipeline audit

- The corrected construction has exactly 71 pre-period months, January 2017
  through November 2022, and 113 static months after excluding December 2022.
- The loader explicitly removes the five wide-extract `03s` rows before adding
  the separately hashed `03b` repair. The removed rows contain zero eligible
  positive-weight observations, and the repair contributes 252,862 eligible
  records; the exact replacement rule is stored in the execution receipt.
- October 2025 is absent and is not interpolated.
- Strict Rule-A beta, finite Webb software exposure, and positive pre-period
  stock for both ages 22--25 and ages 26--65 are enforced before fitting.
- Rebuilt weights, cutoffs, quintiles, and Webb normalization use no stock after
  November 2022. The historical production treatment is separately and
  explicitly labeled as using its 108-month full-static window, including
  post-period stock.
- Declared bridge weights conserve stock among routed early records to relative
  error below 2e-16. The bridge covers 99.5460% of otherwise-valid early stock;
  the unmatched 0.4540% is reported rather than silently counted as routed.
- The rebuilt contract was written to `PREFIT_GATE.json` before the historical
  sealed support was authenticated or read.

## Interpretation

For this baseline, repairing the treatment-construction window does not explain
the estimated Q5--Q1 contrast: it changes the point estimate by about 0.24 log
percentage points relative to the calendar-corrected historical-treatment row,
and the paired interval includes zero. This is evidence about the sensitivity
to this specific pipeline correction, not proof that alternative treatment
constructions are economically equivalent and not evidence of a causal AI
effect.

The complete memberships, exclusions, cutoffs, normalizations, paired draws,
input hashes, output hashes, and failure registry are in `results/`.
The receipt deliberately excludes the mutable `SELF_CHECK.json` and the receipt
itself from its output-hash set; the verifier fails closed if either appears.

# Gate 3 pandemic-shortfall repair and resampling specification

Status: specified after the referee-identified construction audit and before
the replacement shortfall results are computed.

The historical shortfall rows remain archived but do not support an inference:
the total-stock construction mixed ages 18--21 into an ages-22--65 estimating
sample, split occupation codes generated extreme leverage, and an unconstrained
linear extrapolation of the young share left its logical support.

## Corrected constructions

Both measures use ages 22--65, the model's population. The trend window is the
36 months from January 2017 through December 2019. The measurement window is
the 35 months from January 2020 through November 2022. December 2022 remains a
transition month and never enters either the shortfall or post period.

For occupation `o`, let `N_ot` be total ages-22--65 employment and `s_ot` the
ages-22--25 share of ages-22--65 employment. The total-stock measure fits the
historical normalized linear trend in `N_ot / mean_pre(N_ot)`. Its extrapolated
level is bounded below at zero before the mean prediction-minus-observed gap is
taken. The young-relative measure fits the historical employment-weighted
linear trend in `s_ot`; predictions are bounded to `[0,1]` before the
employment-weighted prediction-minus-observed gap is taken. Positive values
mean employment or the young share fell below trend. No outcome is logged, no
pseudocount is introduced, and observed sampling zeros remain in the total
series.

The analysis support is fixed by structure, not by the replacement result. It
retains only one-to-one Census-2010-to-Census-2018 occupation mappings with
unit bridge weight and one route, positive pre-period stock, at least 24
positive pre-period age cells, and at least one positive measurement-period
age cell. This removes discontinuities created by split occupation codes. The
same intersection supports the baseline and both corrected shortfall models.
Canonical exposure quintile assignments are retained when support is reduced.

Each shortfall is standardized using that support's ages-22--65 2017--2019
employment. The standardized shortfall enters as shortfall-by-post alongside
the canonical exposure-quintile-by-post terms and Webb control. It is evaluated
separately in the pooled and SOC2-family-by-calendar-month structures.

## Linked-household full-pipeline sensitivity

Each mean-one Exponential multiplier remains common to every observed month,
co-resident record, and fractional route descendant of a positive CPSID.
Three calculations are reported side by side:

1. fixed corrected shortfalls and fixed exposure labels;
2. corrected shortfalls, normalization, and finite support regenerated inside
   each household draw while exposure labels remain fixed; and
3. corrected shortfalls and exposure labels regenerated inside the same draw.

For every mode and both shortfall definitions, refit the baseline and augmented
models and retain the pooled target, family-month target, their paired movement,
the augmented-minus-baseline exposure movement, and the standardized shortfall
coefficient. Use common draws; never add these sensitivity variances to the
occupation- or family-shock variances.

The household bootstrap estimates sampling sensitivity and reproduces shared
first- and second-stage error. It does not remove regression-to-the-mean bias.
Therefore a deterministic two-fold household diagnostic also constructs the
shortfall on one household half and estimates on the other, then swaps halves.
The two directional estimates and their equal-weight average are descriptive
bias diagnostics, not CPS design-based inference. The split unit is the encoded
positive CPSID, so all months, co-residents, and route descendants remain
together. Public PSU/stratum variables remain unavailable, and household
splitting does not remove PSU-level shared error.

Start with 399 household draws and reuse the declared bootstrap-of-bootstrap
endpoint MCSE target of 0.01 log point. Expand in blocks of 400 to 1,999 only if
needed. Failed joint refits remain in the denominator.

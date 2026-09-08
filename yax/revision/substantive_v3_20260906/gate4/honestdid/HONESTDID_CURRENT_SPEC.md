# YAX Gate 4 HonestDiD specification

Status: post-outcome, referee-requested V3 companion analysis. This file fixes
the implementation before the current-contract HonestDiD result is run.

## Scientific target

The input is the certified Gate 2 quarterly Q5-versus-Q1 event-study vector and
its full occupation-clustered covariance. The reference quarter is 2022Q4. The
scalar target is the dynamic `P` functional: the equal-observed-post-month
average of the 15 reported post-quarter coefficients. Its post-only weight
vector is nonnegative and sums to one. Regular three-month quarters receive
`3/42`; 2025Q4 receives `2/42` because October is absent; and 2026Q3 receives
`1/42` because only July is observed.

This is a companion dynamic functional. It is not the nonlinear grouped static
coefficient `S`, and no sensitivity interval below is interpreted as an
interval for `S`. The descriptive post-minus-pre functional `D` is also not
passed to the package because the official `l_vec` weights post-treatment
effects only.

## Structures and calibration windows

The exercise is run separately for the Gate 2 `unconditioned` and
`family_month` structures.

Two preperiod windows are fixed:

1. `full_2017Q1_2022Q3`: all 23 consecutive pre-quarter coefficients.
2. `recent_2021Q1_2022Q3`: the seven consecutive post-reopening quarters
   immediately preceding the 2022Q4 reference.

The recent window is motivated by calendar proximity and exclusion of the
acute 2020 disruption, not by its p-value or sensitivity result. It does not
splice 2017--2019 to 2021--2022, delete internal quarters, or renumber a gapped
calendar. Both windows retain the same reference and all 15 post quarters.

## Bias restrictions

The official `HonestDiD` implementation is pinned to version 0.2.8 at source
commit `6813f02ed38f0b63bdca6915604b2eac90491303`.

The smoothness restriction is `DeltaSD(M)`: the absolute second difference of
the counterfactual differential-trend bias is bounded by `M` at every adjacent
three-quarter block, including blocks that cross the omitted zero-normalized
reference. Thus `M=0` permits a linear, not necessarily flat, differential
trend. The declared grid, in log points per quarter squared, is
`0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05`.

The relative-magnitude restriction is `DeltaRM(Mbar)`: every pre-reference
consecutive-period change is bounded by the selected maximal signed pre change,
and every post-reference consecutive-period change is bounded by `Mbar` times
that selected pre change. Official inference unions over every eligible pre
change and both signs. The declared dimensionless grid is
`0, 0.5, 1, 1.5, 2`.

The Python preparation stage publishes the exact sparse constraint matrices for
these definitions. Before computing results, the R stage must reconstruct each
matrix using the private matrix constructors in the pinned official package and
obtain elementwise equality within `1e-12`.

## Inference and reproducibility

- Conventional and robust intervals use the complete event-vector covariance,
  not a static standard error.
- `constructOriginalCS`, `createSensitivityResults` (FLCI), and
  `createSensitivityResults_relativeMagnitudes` (C-LF) are called from the
  pinned official package with alpha 0.05, seed 2026090529, and 1,000 inversion
  grid points for relative-magnitude inference.
- The exact coefficient order, covariance, functional weights, sensitivity
  grids, restriction matrices, official returned frames, warnings, elapsed
  times, package versions, and file hashes are retained.
- A zero-exclusion breakdown of zero means only that the conventional interval
  for this dynamic `P` functional already includes zero. A first grid point that
  includes zero is a coarse declared-grid crossing, not an interpolated exact
  threshold.
- The approximate-Gaussian exercise is publication-eligible only because the
  separate Gate 3 inference validation establishes adequate behavior of the
  occupation-clustered dynamic estimator. HonestDiD does not repair an invalid
  input covariance.

## Bound inputs

The authoritative source is
`runs/gate2_dynamic_core_authoritative_20260908`, result ID
`yaxresult_v1_b039944581f0da60fb7e8368bff687858b740a7e638c190a8c934369fc10defe`.
The preparation code verifies the result manifest and every consumed artifact
hash before producing inputs.


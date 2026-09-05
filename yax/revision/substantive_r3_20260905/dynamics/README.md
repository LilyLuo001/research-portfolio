# R3 dynamics audit (DYN-01--DYN-04)

This directory executes the post-outcome exploratory dynamics program registered
for the substantive R3 revision. It does not alter the frozen YAX v1.1 analysis.

The main dynamic specification uses the corrected 113-month calendar (January
2017 through July 2026, with December 2022 excluded as the transition month and
October 2025 absent from the public extract). Calendar months are aggregated to
quarter bins to avoid the unstable parameter burden of a 565-slope monthly
model. The reference bin is 2022Q4, which contains October and November only.
For every other bin the model includes Q2, Q3, Q4, and Q5 interactions, with Q1
omitted, plus a Webb-software interaction. Thus the reported Q5 coefficient is
a Q5-versus-Q1 contrast rather than a Q5-versus-pooled-lower-quintiles contrast.

Two fixed-effect structures are declared and run:

1. occupation and calendar-month fixed effects; and
2. occupation and SOC2-by-calendar-month fixed effects.

The script serializes the complete target coefficient vector, occupation-cluster
covariance, and occupation-level influence representation. A fixed seed and the
stored influence matrix reproduce the common Rademacher score draws exactly.

The dynamic post functional is an observed-calendar-month-weighted average of
the post-2022 quarterly Q5 coefficients. It is a companion estimand. The script
fits the grouped static post coefficient separately and reports their paired
difference under common occupation multipliers; it never assumes equality.

`run_structure_pair.py` supplies the separate cross-structure comparison needed
for synthesis. On identical treatment support it stores the joint occupation
influence and covariance for the unconditioned and SOC2-by-calendar-month static
models, then reports the conditioned-minus-unconditioned coefficient with a
paired interval and MDE under their common multiplier draws. This difference is
a movement between conditioning estimands, not an additive causal decomposition.

Additional outputs cover joint pretrend tests and detectable slopes, every onset
date from November 2022 through June 2023, late-2025/2026 endpoints, and an
occupation-by-month-of-year seasonality sensitivity. Rambachan--Roth adoption is
decided only after checking the event vector, covariance, reference period, and
linear functional; the decision record is permanent even if implementation is
not possible.

The January 2023 static onset is retained because the frozen design treated
December 2022 as a transition after the public ChatGPT launch at the end of
November. The complete sensitivity grid nevertheless starts in November 2022
and ends in June 2023. Because December remains excluded in every static grid
row, the December-2022 and January-2023 onset regressors are mechanically
identical; both rows are retained so that this consequence of the transition
rule is visible rather than silently dropping a declared date.

`run_honestdid.R` is a deliberately separate second stage. It calls the
official `HonestDiD` package rather than recreating its optimization routines.
It runs only for rows that pass the Python applicability audit. Its smoothness
grid is fixed at 0, 0.005, 0.01, 0.02, 0.03, 0.04, and 0.05 log points per
quarter; its relative-magnitude grid is fixed at 0, 0.5, 1, 1.5, and 2. These
grids are declared before the corrected dynamic estimates are produced.
The installation helper pins the official repository to commit
`6813f02ed38f0b63bdca6915604b2eac90491303` and requires `R_LIBS_USER` to point
to project storage; it does not write packages into the quota-limited home
directory.
The SCC wrapper loads the site-provided `glpk/5.0` module and uses a fresh
`r-library/4.5-glpk-cvxr182-rust184-highs112` project library, so failed earlier dependency
builds cannot contaminate the authoritative installation. It loads SCC's
official `rust/1.84.0` module to compile CVXR's declared `clarabel (>= 0.11)`
dependency. `CARGO_HOME` also points beneath the dynamics project directory, so
the build does not write Rust registry or cache files into the quota-limited
home directory. It pins official CVXR 1.8.2
at commit `2fe1dac4d0c903c4a29515bef19c5d3824d09656`; that is the last official
tag satisfying HonestDiD's `CVXR (>= 1.8)` requirement while still exporting
the `status` API called by HonestDiD 0.2.8. CVXR 1.9.x is not substituted because
it removed that exported API.
The installer also pins the official CRAN `highs` 1.12.0-3 release before CVXR;
the older SCC-visible 1.10.0-3 namespace does not satisfy CVXR's declared
`highs (>= 1.12)` requirement.
It likewise pins the official CRAN `osqp` 1.0.0 release because SCC's visible
0.6.3.3 namespace does not satisfy CVXR's declared `osqp (>= 1.0)` requirement.
After the official package finishes, the wrapper reruns `selfcheck.py` with
`--require-honestdid`. That final mode verifies the pinned package source and
version, both declared restriction grids, event-vector dimensions, functional
weights, and SHA-256 hashes for every HonestDiD input and result file.

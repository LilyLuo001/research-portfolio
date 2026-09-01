# YAX Phase 2.5C — Realized Versus Matched-Marginal Benchmark

**POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

## Classification: BENCH-B1

Realized transitions are meaningfully more conflict-heavy than the single
predeclared economically matched benchmark.

The primary realized six-architecture opposite-direction conflict rate is 53.283%.
Across 999 fixed-seed destination remappings that preserve the weighted origin and
destination marginals and prohibit self-transitions, the benchmark mean is 45.267%
(2.5th–97.5th percentiles: 45.077%–45.458%). The realized-minus-benchmark difference
is 8.016 percentage points and the finite-draw upper-tail probability is 0.001.

The same logic applied to persistent A–B–B switches yields 54.462% realized conflict,
a 45.999% benchmark mean (95% simulation interval 45.800%–46.183%), and an 8.464-point
difference. This rules out an explanation based only on immediate reversal noise.

## Benchmark definition and limit

The implementation Hamilton-expands the observed weighted joint transition table to
200,000 pseudo-units, permutes destinations while holding both weighted marginals
fixed, and repairs prohibited self-matches without altering the fixed seed. Maximum
cell-share approximation error is 0.000253 percentage points; the realized pseudo-
sample conflict rate is 53.295%, close to the official-weight rate. All 999 draws
contain zero false self-switches after repair.

This is a descriptive counterfactual benchmark, not a causal randomization test.
It establishes that actual origin–destination pairing is more architecture-conflicting
than expected from the observed marginal occupation composition alone. It does not
identify why workers make those moves.

Source: `YAX_PHASE25_REALIZED_VS_MATCHED_BENCHMARK.json`; seed 2026090101 for the
primary sample and 2026090102 for persistent switches.

# Narrow pre-outcome amendment: Test C paired-difference precision

**Date:** 2026-08-29. **Owner instruction:** proceed with Option 2.

**Outcome seal at amendment:** intact; zero protected post-period outcomes read.

This is the final narrow amendment before `v1.1-design-freeze`. It changes only
the inferential role of Test C. The estimand, exposure pair, common support,
bootstrap draws, estimator, timing, age groups, computerization control and all
other design elements remain unchanged.

## Feasibility finding that triggers the amendment

The originally signed rule required a numerical SESOI equal to 25% of a
verified literature-comparable Q5–Q1 benchmark. The benchmark audit found no
published estimate matching all of YAX's required dimensions:

- ages 22–25 relative to pooled ages 26–65;
- occupation × age-group × month employment stock;
- Q5–Q1 exposure contrast;
- saturated young-relative estimating variation; and
- the YAX PPML/log coefficient scale.

The BCC 19% headline and −0.179 coefficient are explicitly rejected as
substitutes in `literature/BENCHMARK_ALIGNMENT_2026-08-28.md`. Therefore the
signed SESOI rule cannot be instantiated. No numerical threshold is invented or
substituted. The owner sign-off, alignment audit, failed fields in
`power/PAIRED_EQUIVALENCE_PRECISION_v1.json`, and their git history remain the
permanent record of this outcome-blind feasibility finding.

## Test C retained

Test C remains centered on

    Delta_(m,m') = beta_m - beta_m'.

For the explicitly frozen pair, this is the Q5–Q1 coefficient under Eloundou β
minus the Q5–Q1 coefficient under Eloundou α, estimated on their common
occupation support with Webb software exposure as the primary computerization
control.

Retained as binding design elements:

1. one common set of at least 999 bootstrap draws applied to both exposure
   definitions;
2. the paired bootstrap distribution of `Delta`;
3. paired `SE(Delta)`;
4. a 95% paired confidence interval constructed from the common-draw bootstrap
   critical half-width; and
5. outcome-blind `MDE_(Delta,80)` as the formal precision diagnostic.

The frozen precision result is `MDE_(Delta,80) = 0.032722` log points, or 3.326%
in relative magnitude. The ex-ante statement permitted in the paper is:

> The frozen paired design had 80% power to detect coefficient differences of
> approximately 3.27 percentage points.

## Binding interpretation

- If the paired confidence interval excludes zero, the paper may state that the
  downstream estimates are statistically distinguishable across exposure
  definitions and must report the magnitude directly.
- If the paired confidence interval includes zero, the paper may state only
  that the design **does not detect a difference**.
- The paper must never interpret failure to detect a difference as economic
  equivalence.

## Requirements retired

The following are no longer binding and must not be fabricated:

- a numerical SESOI;
- an equivalence interval;
- equivalence-test power; and
- any claim of economic equivalence based on failure to reject `Delta = 0`.

The `paired_delta_power` gate is replaced by
`paired_difference_precision`. The new gate checks the stored paired
distribution or authenticated representation, `SE(Delta)`, the 95% CI
construction, `MDE_(Delta,80)`, common-draw covariance preservation and the
outcome seal. It deliberately contains no SESOI requirement.

## No other design change

This amendment does not alter the January-2023 post-period start, December-2022
transition exclusion, October-2025 gap, July-2026 end, Rule A coverage primary,
β primary / α contrast ordering, estimating equation, clustering, table shells,
or novelty claim. Protected post-period outcomes remain unopened.

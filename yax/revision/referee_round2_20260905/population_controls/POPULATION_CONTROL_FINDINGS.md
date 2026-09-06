# January 2025 population-control findings

Status: post-outcome exploratory; not part of confirmatory YAX v1.1.

## Bottom line

The unusually large January 2025 CPS population-control revision does not explain the negative YAX association in the available diagnostics. This is a bounded conclusion: no valid age-by-occupation counterfactual micro-weights exist, so the audit does not claim to estimate the literal model “without” the revision.

On the repaired 113-month calendar, the official-weight coefficient is -0.13455 (SE 0.04496; 95% interval [-0.22264, -0.04646]). The respondent-equivalent version is -0.13482 (SE 0.04414; interval [-0.22158, -0.04806]). Ending both series in December 2024 gives -0.11347 under official weights and -0.10558 under respondent-equivalent counts. Thus the post-2025 extension makes the full-period average more negative under both cell constructions, not only under revised weights.

In a joint repaired-calendar model, the official-weight coefficient is -0.11077 for 2023--24 and -0.16639 for 2025--26. Their paired difference is -0.05562 with interval [-0.12284, 0.01161], so the weighted design does not detect a change between eras. The respondent-equivalent coefficients are -0.10259 and -0.18263; their paired difference is -0.08004 with interval [-0.13899, -0.02109]. This divergence does not prove response composition, but it is inconsistent with the claim that revised population weights alone mechanically generate the late negative estimate.

The raw, unadjusted Q5-minus-Q1 log young/older contrast moves by +0.01393 from December 2024 to January 2025 under official weights (slightly less negative) and by -0.03024 under respondent-equivalent counts. There is no discrete negative official-weight break in this diagnostic.

## Why there is no fabricated counterfactual-weight result

BLS states that the January 2025 controls use Vintage 2024 population estimates and increased the estimated civilian noninstitutional population by 2.9 million. Official pre-2025 levels were not revised. BLS's experimental historical series applies aggregate population ratios only to total labor-force and employment levels; it explicitly does not supply adjustments for demographic subgroups. The YAX outcome requires joint age-by-occupation weights, so applying the aggregate ratio would silently invent the missing allocation.

The precise interpretation is therefore:

- the official-weight discontinuity is real and disclosed;
- the corrected-calendar estimate is the substantive baseline;
- unweighted and pre-2025-endpoint checks remain negative;
- 2025--26 is not statistically distinguishable from 2023--24 under official weights; and
- a literal common-control microdata series is unavailable.

Exact estimates are in `results/POPULATION_CONTROL_STATIC_SENSITIVITIES.csv` and `results/POPULATION_CONTROL_ERA_COMPARISON.csv`. Raw monthly diagnostics and all input hashes are stored beside them.

# Analysis specification before execution

Status: written after outcomes were previously observed and before any analysis newly authorized by the 2026-09-05 referee-revision prompt. Every result below is **post-outcome exploratory**. The protected design and confirmatory outputs are unchanged.

## Common implementation rules

- Reproduce the corrected frozen beta-by-Webb model before new fitting. Abort if the coefficient differs by more than `1e-10` or if protected refs/input hashes move.
- Unit: Census-2018 occupation by age group by calendar month employment stock.
- Weights: CPS final person weights aggregated once to cells. No second survey weighting of already weighted stocks.
- Baseline static window: January 2017--July 2026, excluding December 2022 from static fits and retaining the documented October 2025 gap.
- Estimator: the existing grouped-binomial conditional equivalent of the two-age-group PPML with occupation-by-age, occupation-by-month, and age-by-month fixed effects.
- New bootstrap: occupation-cluster Rademacher wild-score multipliers, 999 draws, master seed `2026090500`; paired comparisons reuse the same multiplier matrix.
- All treatment definitions, inclusion rules, seeds, and failures are reported. No result-based selection.

## A. AI-specificity placebo benchmark

Primary identical-support placebo set: log mean annual wage, required-education index, cognitive ability importance, Dingel--Neiman teleworkability, and STEM major-group share. The common sample is the intersection of beta, Webb software, and all five placebo columns. Beta and every feasible placebo use employment-weighted, tie-preserving quintiles recomputed on that fixed sample. A collapsed cutoff is a failure of the quintile implementation and triggers a separately labeled natural-group result, not arbitrary tie-breaking.

Each fit holds outcome, ages, calendar, fixed effects, support, and Webb conditioning fixed. Store the entire Q2--Q5 coefficient vector, occupation-cluster influence matrix, paired AI-minus-placebo Q5--Q1 difference, paired interval, and tail-membership overlap. The selected characteristics are descriptive placebo benchmarks, not a calibrated null.

Synthetic diagnostic: within each two-digit SOC major group, permute beta scores across occupations, leaving group membership, stocks, Webb, mapping, and support fixed. Use 999 independent permutations with seed `2026090502`; recompute weighted quintiles and the point estimate for each feasible draw. This is an assumption-dependent permutation diagnostic, not design-based randomization inference.

## B. Reference-tail and composition checks

On the primary beta/Webb support, fit the original four post-quintile indicators once and obtain Q5-Q2, Q5-Q4, Q4-Q2, and Q5-Q3 by linear combinations of the same coefficient vector and the same joint influence draws. No re-referencing changes the sample or fitted model.

Create descriptive Q1/Q5 monthly young stock, older stock, and young/older ratio series. Index each series to its mean over observed 2019 months and, separately, its mean over observed 2022 months. These paths are not additive decompositions of the nonlinear coefficient.

Exclusions are fixed before fitting: Census major group 35 (food preparation and serving); major group 15 (computer and mathematical); major group 43 (office and administrative support); and an `IND1990` leisure/hospitality exclusion only after the authoritative code range is documented. Each exclusion retains the primary construction and recomputes cutoffs on the disclosed support; a second fixed-cutoff descriptive membership check records whether the result comes from sample versus classification changes.

Stable/reclassified Q1 and Q5 occupations are defined across the six architecture-specific weighted quintiles on literal common support. Report employment and existing estimator-information shares; use actual deletion/refit or score influence, never an unsupported additive decomposition.

## C. Comparison age and time heterogeneity

Retain ages 22--25 versus 26--65. Additional binary comparison models use 26--35, 26--45, 36--55, and 51--65, with the same beta/Webb construction and calendar. The 18--21 sensitivity uses 18--21 versus 51--65. Every model reports its own support and paired/common-draw contrasts where the occupation support matches.

The existing six-bin age profile remains a multinomial exploratory profile and is not treated as algebraically identical to the binary comparisons. The pooled-model interpretation is evaluated using fitted comparison-stock weights; any one-third description is labeled descriptive unless an exact decomposition is established.

Time heterogeneity uses mutually exclusive post indicators for calendar 2023, 2024, and 2025--July 2026 in a single fit. Store joint covariance and formal pairwise differences. The result is an era-specific occupational stock association, not an adoption event study.

## D. Family-model construction sensitivity

Reproduce the original F/G/Webb fit on the literal 444-occupation common support. Standardize each of the six primitive implementation scores with the original pre-period employment weights on this support. For each leave-one-measure-out model, average the remaining measures equally within its family, construct raw `F=(A+E)/2` and `G=(A-E)/2`, then standardize F, G, and Webb on the unchanged support. Report both coefficients, joint wild-score inference, scale constants, family balance, and common-support hash. The no-alpha model is reported first; every other deletion is reported regardless of direction.

Additional declared models on the same support are: representative AIOE (`aioe_admin_equal`) plus beta plus Webb; direct primitives `D=alpha` and `S=broad-alpha` plus Webb; and direct A/E plus Webb as an exact change of basis of the reproduced F/G fit. The direct A/E transformation uses every stored F/G draw consistently. No model enters alpha, beta, and broad as independent primitives.

Construction continuum: evaluate `X(lambda)=D+lambda*S` for lambda `0, .25, .5, .75, 1`, using both fixed normalization anchored at lambda `.5` and separately restandardized scores. Hold mapping/support/Webb fixed; report membership, residual information, stock estimates, and mobility ranking diagnostics. This grid is descriptive and was specified after outcomes were seen.

## E. Calendar, reconstruction, sample, and estimator audits

- Rebuild cells directly from the wide extract, first reproducing the frozen 109-month calendar and then restoring March 2017--2021 for a 114-month balanced-calendar sensitivity. October 2025 remains absent and is identified as an extract-specification omission.
- Audit split-code routing: route shares, source-to-target multiplicity, shared young/older conversion weights, pre-period exposure/employment/information shares, and a stable Census-2010/coarse-major-group benchmark. A post-2020-only estimate is separately labeled as a shorter temporal estimand.
- Produce one sample-flow table for 463, 468, 465, and 444 universes; records, cells, months, weighted/unweighted stocks, coverage, empty/zero-young cells, convergence, and exclusions.
- Minimum-size sensitivities use fixed thresholds of 100, 250, and 500 unweighted employed respondents over the full panel. The unweighted-cell construction is a different descriptive estimand and is labeled as such.
- Occupation-age seasonality sensitivity adds occupation-by-young-by-calendar-month-of-year interactions to the baseline residualized model only if the design matrix has full residual rank; otherwise report failure and parameter burden.

## F. Inference, power, and mobility

Reproduce the six one-sided marginal p-values, conjunction p-value, simultaneous critical value, and upper bounds. Transform verified coefficient limits monotonically to `100*(exp(beta)-1)`.

For the primary and no-alpha F/G models, compare the existing one-step wild-score interval with 199 full cluster-wild re-estimations using the first 199 rows of the common multiplier matrix (seed `2026090503`). Failures and convergence counts remain visible.

Power work starts from the code-only E3 conclusion: no nominal/effective-count heuristic is treated as a decomposition. Historical simulations may be replayed under explicitly varied occupation-common, calendar-common, serial, and post-variance components only if the saved inputs identify each component; otherwise the requested quantitative allocation is unresolved.

Mobility uses the existing official-weight switch frame. Report all-six and pairwise conflict, within/between-family conflict, and no-alpha results. For thresholds `0`, `.1`, `.25`, and `.5` weighted SD, implement (i) eligibility when any absolute architecture movement exceeds the threshold and (ii) substantial opposition when both a positive and negative movement exceed it. Add weighted percentile-rank movement thresholds at 5, 10, and 20 percentiles. Report all-switch denominators, eligibility, conditional conflict, movement-mass-weighted conflict, immediate reversals, persistent switches, and named nontrivial examples. No immediate reversal is called a coding error.

The hard benchmark is re-audited on its exact retained records. Report self-transition feasibility, no-self implementation, excluded weight, pseudo-unit size, Monte Carlo error, and the exact product-marginal expectation only for the unconstrained null. The 0.96-point excess is not an equivalence result.

## G. Additional architecture admission

Webb AI and OECD enter the outcome grid only if an exact version, construct definition, outcome-independent inclusion rule, and Census-2018 mapping with disclosed coverage are verified before their outcomes are fitted. Frey--Osborne remains an automation-risk comparator; LLM-annotated alternatives remain excluded unless the same admission rule is met. Non-admission is a reported construct/coverage decision, not missing robustness.

## Stop and disclosure rules

Stop on moved protected refs, changed authenticated input hashes, baseline reproduction failure, silent support changes, or nonconvergence that makes a requested contrast undefined. Missing full referee reports prevent a claim that the response matrix covers unseen wording; all master-prompt comments are nevertheless tracked. Manuscript framing is chosen only after the result ledger is complete.

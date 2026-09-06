# YAX V5.1 referee-repair execution plan

**Written before executing any V5.1 quantitative calculation.**

This is a closed, post-outcome exploratory repair. It is not Phase 4 and does not reopen the empirical search. The parent state is `ed4055eab8d303c2ff48e18562a99dd43b3c7874`. The protected `v1.1-design-freeze` and `v1.1-confirmatory-results` tags must continue to peel to `22fbf7924809b7a535e31ae0ab68f5b113ce8078` and `b16109482c3bf5ca176f6f08976e120b04769945`.

Exactly one new labor-outcome specification is authorized: the joint continuous F+G stock model in `YAX_V51_FG_JOINT_MODEL_PLAN.md`. No other new labor-outcome regression may be executed.

## Authorized treatment-side diagnostics

1. Compute pairwise Cohen's kappa for all 15 architecture pairs on the frozen 108,500-switch literal-common-support sample. Labels are the existing three nominal categories `-1`, `0`, and `+1`; no deadband is introduced. Report official-`LNKFW1MWT` and unweighted versions. Raw exact agreement, opposite-sign conflict, and any-tie rates accompany kappa.
2. Compute a single Fleiss-type six-rater kappa on the same three labels. Report the standard unweighted statistic and its direct official-weighted descriptive analogue. No alternative kappa definition is searched.
3. Render the six-measure occupation-level weighted Pearson and weighted rank-correlation matrices from the frozen 463-occupation pre-period measurement file. Weighted rank correlation means the employment-weighted Pearson correlation of average ranks. No labor outcome enters.

## Authorized model-based dependence sensitivity

Reconstruct, without changing point specifications, the primary beta-by-Webb Q5-versus-Q1 stock model and the six previously reported literal-common-support Q5-versus-Q1 stock models. Replace only the one-way occupation covariance estimator with the Cameron-Gelbach-Miller inclusion-exclusion covariance clustered by occupation and calendar month:

\[
\widehat V_{o,t}=\widehat V_o+\widehat V_t-\widehat V_{o\cap t}.
\]

Each component uses absorbed score contributions and the finite-cluster multiplier `G/(G-1)` for its clustering dimension; the cell-intersection term uses `N/(N-1)`. Report analytic two-way standard errors and normal 95% intervals as a model-based dependence sensitivity, not a survey-design correction. Do not rerun the wider model grid. Point estimates must reproduce their sealed values to absolute tolerance `1e-10` or execution stops.

## Other repairs

- Reconcile the prospective paired MDE from its stored simulation and code; do not calculate a replacement ex-post MDE.
- Audit the existing CPS links and occupation coding using the frozen construction and official documentation. Do not estimate a new switching specification.
- Define the hard benchmark's broad-family partition from the recorded SOC-2018 major-group mapping. Do not run another benchmark.
- Revise the manuscript, architecture matrix, estimand ledger, mechanisms/stopping record, open issues, table/figure map, and referee red team only after the fixed calculations complete.

## Stop rules

Execution stops on moved protected refs, an input-hash mismatch, changed 444-occupation support, failure to reproduce sealed point estimates, or any request for an analysis outside this plan. An implementation defect may be repaired only if documented and if it leaves all frozen estimands, samples, scales, seeds, and output definitions unchanged.

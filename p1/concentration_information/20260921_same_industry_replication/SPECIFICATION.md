# Frozen-design specification for the bounded same-industry replication

## Question and estimand

This stage asks whether the narrow development-sample association replicates in the approved 2023-H2 date pool. It estimates an association, not ETF mediation, a concentration trend, price-discovery speed, or a causal effect.

For receiver company `i` and issuer-event `e`, the response is

`D_ie = |two-session event return| - mean(|two-session eligible control return|)`.

The exposure is the log of the positive observed 2022-12-30 `PURE_D` issuer-receiver pair strength. A missing pair row is unknown, never zero. For direct comparability, the log exposure is standardized using the already exposed H1 development constants: mean `-7.120058696390034` and sample standard deviation `1.575275281258204`. No H2 value changes this scale.

The primary pooled model contains issuer-event fixed effects, standardized exposure `X`, the actual issuer/receiver SIC2 match indicator `S`, `X*S`, baseline log company size, and December-2022 log average dollar volume. Every issuer-event has total weight one and its eligible receiver rows are equally weighted. This event-balanced weighting is a prospective replication choice and differs from the H1 row-weighted pooled regression; the fixed H1 exposure scale aids coefficient-unit comparison but does not make the estimands identical. A row-weighted H1-comparable coefficient may be reported only as a labeled secondary diagnostic, never substituted for the primary. The two primary reported quantities are the same-industry slope `beta_X + beta_XS` and the directly tested same-minus-other slope difference `beta_XS`; their intervals use the fitted covariance, including the covariance between `beta_X` and `beta_XS` for the combined slope. Separate subgroup significance labels are not a cross-group test.

The already exposed H1 adjusted same-industry benchmark is `+0.002599258363117126` per fixed H1 exposure standard deviation. It is retained only as a development comparison: H1 was row-weighted and did not estimate the direct pooled interaction, so equality or change is not inferred from the numerical comparison.

Historical identity and SIC are date-valid at the baseline cutoff. Missing SIC is excluded from the primary model and counted. Multiple share classes are aggregated to company returns with lagged market-cap weights. A missing class return contributes neither its return nor its lagged-cap weight. `RET` and `DLRET` are compounded when both exist; a lone `DLRET` is used when `RET` is missing. The lag must be the immediately preceding trading session. Baseline size and liquidity are fixed before 2023. Winsorization and response-based trimming are prohibited.

## Result-blind calendar construction

The approved pool is 2023-H2 only. The exposed 2023-07-28 Exxon diagnostic and any event or control window overlapping its two-session response window are excluded. No event or control response date may cross outside H2.

The main event window is the first trading session on or after the announcement date plus the following trading session. Candidate controls retain the prior rule of exact same-weekday calendar offsets `-28, -21, -14, +14, +21, +28`. Candidates are ordered by absolute offset, past before future at a tie, then date. The deterministic global greedy allocation excludes any top-eight announcement overlap and prevents an event or control trading date from appearing in two distinct calendar-support blocks. It also prevents an allocated control date from serving as another block's event date. No result is used to choose or reorder candidates.

Receiver own-news screening is conservative about the unobserved time of day. The exact date-only predicate is `prior_trading_date <= own_announcement_date <= second_window_date`: it includes the entire trading date preceding the first response session, even though an announcement earlier that day would predate that close. This prevents a prior-close after-hours release from escaping the screen. Each retained receiver-event needs at least two controls. Attrition is reported before and after every rule. The metadata package reports shared dates, duplicate receiver-control keys, support-graph components, repeated companies, group coverage, exposure overlap and design rank. Components diagnose source sharing; they are not effective sample sizes.

## Pre-outcome support and inference gate

The gate is evaluated on the actual result-blind design, not on stock-row counts. For this bounded exercise an interpretable descriptive interval requires all of the following:

- at least eight disjoint calendar-support blocks;
- each industry group represented with exposure variation in at least six blocks;
- no block exceeding 25% of total analysis weight;
- a full-rank main within-event design, retained after every leave-one-block deletion;
- zero event/control trading-date reuse across blocks and at least two controls per retained receiver-event.

These are study-specific triage conditions: eight blocks supplies seven cluster degrees of freedom and permits meaningful deletion checks; six group-support blocks guards against a slope identified by only a handful of dates; the weight cap prevents one block from dominating the sandwich score. They are not universal statistical guarantees and do not establish power. If any condition fails, the terminal status is `STOP_SUPPORT`; the analysis does not read H2 responses, expand years, change windows, or purchase data.

A failure establishes that the predeclared deterministic allocation lacks support, not that no feasible allocation exists. Global infeasibility is claimed only if a separate result-blind exact feasibility or valid upper-bound calculation establishes it; otherwise that stronger claim is explicitly `NOT_RUN`.

If the gate passes, uncertainty uses a calendar-support-block clustered sandwich with the CR1 finite-sample factor and a `t(G-1)` reference. The residual-dimension correction counts all five slope columns plus one absorbed intercept for every issuer-event (the algebraically equivalent no-global-intercept dummy parametrization). Its interpretation assumes independent shocks across the disjoint calendar-support blocks conditional on included covariates. Repeated receivers and unmeasured macro or industry shocks can violate that assumption even without shared dates, so intervals remain descriptive. Leave-one-calendar-block and leave-one-issuer estimates are mandatory. There is no approved economic-importance threshold and none will be invented after results.

The same-industry slope and direct slope difference are a family of two primary quantities. Each receives a two-sided 97.5% marginal interval (`alpha/2 = 0.0125` per tail), yielding conservative 95% Bonferroni familywise coverage conditional on the cluster-sandwich approximation; ordinary marginal 95% intervals are not described as simultaneous. `CONTINUE_MECHANISM_FEASIBILITY` requires both familywise lower bounds above zero and both estimates positive after every leave-one-calendar-block and leave-one-issuer deletion. If the support gate passed and either familywise upper bound is at or below zero, the action is `STOP_SIGNAL_ROUTE`. Every other result is `INCONCLUSIVE_STOP_SPENDING`. This rule is directional evidence triage, not an economic-importance or equivalence threshold.

## Outcome opening and finite repair

The execution script refuses to read response-bearing files unless `PREOUTCOME_REVIEW.json` records `PASS_OPEN_RESULTS`, binds the exact configuration and metadata hashes, and the current hashes match. Tests use synthetic data or exposed H1 material only. Once outcomes are opened, the primary sample, window, assignment, model, weighting, exposure scale and inference method cannot change. A genuine implementation fix preserves the failed run, states whether results were visible, and receives a new independent check.

If response missingness that could not be known from result-blind availability metadata removes blocks, group support, or rank after opening, the allocation is not refilled and the sample is not changed. The execution reports attrition and no certified interval. When one share class lacks a usable return, the company aggregation renormalizes over contributing date-valid common-share classes and reports the number of missing classes and the retained fraction of lagged market-cap weight; source-date presence alone is not called valid-return coverage.

Licensed row-level designs, controls and returns remain on SCC. Git-safe outputs contain aggregate counts, coefficients, sensitivities, hashes and receipts only.

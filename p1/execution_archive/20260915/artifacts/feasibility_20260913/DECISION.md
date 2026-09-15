# P1 feasibility decision

**Overall verdict: `HOLD_DESIGN`**  
**Concurrent domain hold: `HOLD_DATA`**  
**Run:** 20260913; source HEAD `35361cc5a8c6360e1d48da9a2aa4fd40458b0e04`; advanced evidence snapshot `cb36417304b282cda5e38ede13d1af872ad9f346`.

This is not a `NO_GO`: the audit found neither a demonstrated zero effect nor an estimator-correct empirical precision failure. It is not a `GO`: the primary comparator, treatment clock, aggregation, timing/equivalence contrast and inference grouping are not fully authorized, and the actual earnings/session/quote design needed to measure and calibrate the test is unavailable. The observed post-conversion earnings-response outcomes stayed sealed throughout.

## 1. Is the outcome comparable and observable before and after conversion?

**Domain verdict: `HOLD_DATA`.** A stock-level outcome can be comparable in principle because the same underlying stock has pre- and post-conversion prices. The new ETF's own tape cannot be a before/after leadership outcome; P1 must remain a stock earnings-response design. The documentary outcome is the signed `CAR^h` response curve at 5m, 15m, 30m, 60m, close and +1d, constructed from stock and SPY quote-midpoint price returns on matching clocks. Premarket and aftermarket events start at the appropriate opening and measure post-open adjustment; they are not the same estimand as RTH releases. Opening gaps remain separate.

The required evidence is not presently accessible in an authorized joined view: no validated analyst-level forecast/actual/SUE panel, timezone-resolved release time, market-session mask, live bid/ask quote panel, complete horizon mask or pre-treatment/untreated quote-response calibration panel was found. Midpoint data alone will also require bid- and ask-side diagnostics because asymmetric spread resolution can move the midpoint without proving faster informed price discovery. These omissions block actual observability, comparable selection and empirical calibration. Daily or macro-only prices are not a valid substitute.

## 2. Is there a defensible counterfactual for the exposure gradient?

**Domain verdict: `HOLD_DESIGN`.** The conversion is selected and changes a package of tax, fee, distribution, clientele, liquidity and trading arrangements. It is not an exogenous instrument for AP arbitrage. A defensible claim requires parallel conversion-absent changes in the **SUE response slope** across the chosen exposure groups, stable or explicitly standardized analyst coverage/SUE measurement, and no omitted exposure-proportional fund shock. Average-return pretrends and additive fund fixed effects do not establish those restrictions.

The authority record does not settle the comparison. The plan prioritizes high versus low dose among positive converted-fund holdings; the blueprint instead defines `D>=0.005` treated tiers against clean zero-dose controls and drops `0<D<0.005`. The cited V-decision receipts are absent from the located owner log. In addition, the measured exposure snapshot uses latest PRE-effective holdings, while the blueprint requires PRE-announcement holdings. Earliest public anticipation and public-availability rules have not been applied. Selecting on post-conversion continuity or controlling for post flows/fees would redefine the package effect and cannot be done silently.

## 3. Does the actual estimator have usable identifying variation and valid inference?

**Domain verdict: `HOLD_DESIGN` plus `HOLD_DATA`.** Exposure metadata are substantial but highly concentrated. Reproduced all-sponsor support is 8,801 positive primary-ready stock-wave cells, 3,440 stocks and 30 waves; 583 cells / 573 stocks / four waves reach 0.5% ownership. Dimensional alone supplies 561 of those high-dose cells across two waves. Excluding Dimensional leaves 21 high-dose stocks across two waves. These are exposure cells, not earnings observations or independent shocks. Adviser labels are unsigned sponsor proxies.

The documented estimand is an equal average of conversion-wave effects. Equal total row weight per wave in a pooled regression does not implement that object: nuisance-residualized information still weights each wave. The correct construction needs wave-specific identified coefficients and an explicit equal-weight contrast with shared-stock/event covariance. The referee reproduced a two-wave counterexample in which the pooled estimator is 0.9 while the equal-wave target is 0.5.

Generic weighted FWL and cross-horizon covariance mathematics passed independent checking. The repaired code now has pinned input hashes, ownership-range checks, anticipation blocking, enumerated missing-input guards and a signed-crosswalk schema guard; seven focused tests pass. But no actual candidate A/B/C design, stock×wave FE system, wave-specific nuisance, control reuse, release-date dependence or declared `boottest` procedure was executed. Economic sponsor groups and bootstrap clustering remain unresolved. Thus actual rank, residualized support, leverage, leave-sponsor-out stability, test size and coverage are unknown.

## 4. Can the design detect or rule out an economically meaningful timing effect?

**Domain verdict: `HOLD_DATA` and `HOLD_DESIGN`.** The historical MDE claim is invalid for this question. Its code uses raw `Exposure/0.005`, a raw exposure-squared denominator, pooled weights and imposed 30/25/20/25 variance shares without SUE, Post, nuisance residualization, the actual horizon mask or calibrated covariance. Its 1.508/2.334 residual-SD MDEs and “1,300 events” implication are not estimator-correct empirical evidence and cannot support `NO_GO`.

Timing also cannot be equated with one significant early coefficient. An amplitude-only response can raise all horizons. The proposed design-only restriction tests whether `beta_h` departs jointly from a transported amplitude shape `f_h beta_T`; a pure timing claim additionally requires terminal-effect equivalence. No amplitude-reference population or economically meaningful terminal/timing margin is signed, and a weak terminal denominator blocks normalization. Consequently 80%/90% MDEs, equivalence probabilities and basis-point translations for the actual contrast are `NOT_AVAILABLE`.

The 2,000-repetition output is deliberately only a generic pooled-continuous oracle development fixture. It verifies numerical behavior under explicit synthetic assumptions, includes null, faster, slower, amplitude-only, mixed and missingness/dependence cases, and is labeled `DEVELOPMENT_FIXTURE/ASSUMED_SCENARIO/CONDITIONAL`. It is not P1 power and is not used to select a design.

## 5. Would the result or a precise bound materially add to the closest literature?

**Domain verdict: `HOLD_DESIGN`.** The conversion setting already has a direct predecessor: Saglam–Tuzun studies the 2021 Dimensional conversion, transferred ownership, volatility and spreads. ETF/passive ownership and earnings efficiency, ERCs, PEAD and cross-firm information transfer are already covered by GNZ, Huang–O'Hara–Zhong, Sammon and Bhojraj–Mohanram–Zhang. Intraday quote adjustment and earnings jumps are established measurement literatures. A generic “ETF improves price discovery” claim is not a material increment.

A potentially material, narrower contribution remains: a predeclared conversion-package exposure contrast that shifts the **within-event horizon shape** of the underlying stock's own signed earnings response, distinct from amplitude, while bounding the terminal response. That contribution survives only if the comparator and transport assumptions are credible, quote-side interpretation is valid, and the design can deliver a precise timing/equivalence statement. Those conditions are unresolved, so novelty is conditional rather than signed off.

## What was actually executed

- Verified client/version, native subagent support, model-routing discrepancy, git state/branches and available local evidence; created separate local worktrees without merge or push.
- Recomputed exposure hierarchy, repeats, high-dose support, concentration and leave-one-wave/adviser-proxy diagnostics from frozen metadata.
- Audited the historical power code and invalidated its use as actual-estimator power.
- Produced an explicit estimation contract with signed/proposed/unknown statuses; verified targeted primary literature.
- Implemented and tested outcome-sealed input guards, generic FWL/covariance fixtures and explicit unavailable rows for actual design, MDE, equivalence and `boottest` metrics.
- Obtained an independent Astra referee derivation, support recount, 50,000-draw variance check and challenge ledger; remediated the bounded code defects it found. No SCC job, licensed outcome integration, Stata run, headline coefficient or post-treatment curve was executed.

## One next action

Execute the single owner contract-reconciliation task in `NEXT_ACTION.md`: sign the comparator/population, pre-announcement exposure clock, equal-wave aggregation, amplitude-proof timing contrast and margins, and SUE definition; also sign outcome-independent procedures that use permitted coverage/sponsor metadata to finalize the primary session and bootstrap dimension before any response estimate. Only after that record should the narrowly scoped protected design extract be commissioned and those procedures applied. More Monte Carlo repetitions or a data purchase cannot choose the economic object.

## Signoff

The independent econometrician and referee agree on the generic FWL/aggregation mathematics and on the current `HOLD_DESIGN`/`HOLD_DATA` blockers. Neither signs empirical identification, actual-estimator power or `GO`. The referee found no demonstrated basis for `NO_GO`.

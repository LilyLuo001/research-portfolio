# YAX Phase 3 execution plan

**POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.**

This plan is binding from the pre-result implementation commit. No new Phase 3 quantitative result may be opened before this plan, the implementation, and targeted tests are committed and pushed. Only implementation bugs that leave the estimand unchanged may be repaired afterward, with a permanent ledger entry.

## Scope and immutable inputs

- Parent: `3feda26c698b19823d3370eecb3abf2a57ad9cfd`.
- Branch: `task/yax-phase3-final-20260901`.
- Frozen architectures, in order: AIOE administrative/equal, AIOE ability-direct, AIOE OEWS/source-weighted, Eloundou alpha, beta, gamma.
- The only new labor-outcome model is the single shared-family-component employment-stock PPML specified below.
- The joint-sign exercise reconstructs joint influence inference for the six already reported literal-common-support parameters; it does not define new point-estimate specifications.
- O*NET, BTOS, adoption, wages/hours, heterogeneity, timing, exposure construction, residual-stock, and other prohibited extensions remain closed.

## 1. Hard reallocation benchmark

### Universe and weights

Use exactly the frozen Phase 2.5 realized-switch universe: harmonized adjacent-month employed-to-employed occupational switches, official `LNKFW1MWT`, no long-gap links, literal six-architecture origin-and-destination common support, and the frozen persistent `A-B-B` sensitivity.

### Primary constraint and pseudo-population

The hard-benchmark stratum is:

`age_group × calendar month × origin broad occupational family × destination broad occupational family`.

Construct 200,000 pseudo-units by Hamilton apportionment over observed `stratum × detailed origin × detailed destination` weighted cells. The resulting pseudo-population approximates the official-weight joint distribution once, before any draw. Within every stratum, the detailed origin and destination arrays therefore reproduce the Hamilton-discretized weighted marginals exactly.

For each of 999 draws, independently rematch destinations only within the frozen stratum. False self-transitions are repaired only by within-stratum destination swaps, which preserve both detailed marginals. The implementation must verify zero self-transitions after repair and must never move a destination across strata. Seed: `2026090301` for the primary sample and `2026090302` for the persistent sample.

The current marginal benchmark is read from the sealed Phase 2.5 JSON; it is not rerun or tuned.

### Frozen fallback

The primary implementation is feasible because the Hamilton counts are derived from observed non-self detailed pairs. If the repair algorithm nevertheless fails after 20 independently seeded within-stratum attempts, stop the primary run and use exactly one fallback: replace calendar month with calendar quarter, retain only strata with at least two observed detailed origin-destination cells and four pseudo-units, and report official-weight support. No other constraint, distance metric, or adaptive benchmark is authorized. If fallback support is below 90% of six-way official weight, the hard benchmark is classified `HB-C` for manuscript-claim purposes because the intended reference distribution was not credibly implemented.

### Classification

The sealed current marginal gap is 8.0158 percentage points. Define half that benchmark, rounded before execution, as 4.01 points.

- `HB-A`: realized-minus-hard gap is at least 4.01 points and realized conflict exceeds the hard benchmark 97.5th percentile.
- `HB-B`: the gap is at least 1.00 point but fails `HB-A`, or exceeds 4.01 points without exceeding the 97.5th percentile.
- `HB-C`: the gap is below 1.00 point, or the fallback retains less than 90% of official six-way weight.

The empirical tail area is descriptive and is never called a conventional or causal p-value.

## 2. Shared and architecture-specific exposure components

Use the 463-occupation complete six-measure file sealed in Phase 2.5 and its positive pre-period employment weights. For each measure `m`, form a weighted z-score `Z_om` using that file's pre-period weights.

Define mechanically, without rotation or outcome-guided sign changes:

- `A_o = mean(Z_o,m)` across the three AIOE measures;
- `E_o = mean(Z_o,m)` across alpha, beta, and gamma;
- `F_o = (A_o + E_o) / 2`, the shared family component;
- `G_o = (A_o - E_o) / 2`, the family-disagreement component;
- `R_om = Z_om - F_o`, the architecture-specific residual used only for switch decomposition.

All six source measures are already oriented so larger means more exposure. The sign of `F` is therefore fixed as written and may not be flipped. `F` and `G` are not restandardized. The existing family-balanced PCA is a descriptive stability row only.

The 463 current-taxonomy occupations define the six weighted z-score means and standard deviations once. For the harmonized `OCC2010` switch panel, apply those same six fixed transformations to the already frozen `occ2010_sensitivity_all_years` exposure values used in Phase 2.5; do not re-estimate moments on the switch sample. For the stock model, apply them directly to the corresponding current-taxonomy values. This keeps one coordinate system across the two exercises while preserving each frozen occupational mapping. Any six-way switch lacking a finite transformed component is excluded transparently and its official-weight share is reported; the component exercise is not permitted to impute or restandardize to rescue coverage.

## 3. Realized reallocation decomposition

For every frozen six-way realized switch, compute `ΔF`, `ΔG`, every `ΔZ_m`, and `ΔR_m`. Directional conflict means at least one strictly positive and one strictly negative `ΔZ_m`; zero changes alone do not create conflict.

### Frozen bins and displacement summaries

- Form five tie-preserving official-weight bins of `|ΔF|` using weighted 20/40/60/80 percent cut values on the full six-way realized-switch sample.
- Compute the cuts once and reuse them unchanged for the persistent sample and all architecture pairs.
- Do not search alternate cut counts or boundaries.
- Avoid a ratio with an arbitrary epsilon. Report jointly `|ΔF|`, `|ΔG|`, and `H = sqrt(mean_m((ΔR_m)^2))`.
- Compare weighted medians and means of these quantities for conflict versus unanimous-direction transitions, plus the weighted share with `|ΔG| > |ΔF|` and with `H > |ΔF|`.
- For every one of the 15 frozen architecture pairs, report weighted sign-conflict rates by the same `|ΔF|` bins and the pair-specific residual displacement `H_mn = |ΔR_m - ΔR_n| / 2`.

### Classification

Let `C15` be the conflict rate in the lowest `|ΔF|` bin minus the rate in the highest bin. Let `HR` be weighted median `H` among conflict transitions divided by its weighted median among unanimous transitions.

- `SC-R1`: primary `C15 ≥ 0.15`, primary `HR ≥ 1.25`, persistent `C15 ≥ 0.10`, and all three differences have the predicted sign.
- `SC-R2`: primary `C15 ≥ 0.05`, primary `HR ≥ 1.10`, and persistent `C15 > 0`, but `SC-R1` is not met.
- `SC-R3`: otherwise.

This is descriptive organization, not a causal mechanism test.

## 4. The single shared-component employment-stock model

Use the literal 444-occupation support already frozen for the six-architecture Table 5B comparison, finite Webb software exposure, the 108 static months, ages 22–25 versus 26–65, January 2023 post start, December 2022 transition-month exclusion, and the existing grouped-binomial conditional implementation of the saturated PPML.

`F` itself is built with pre-period weights as above. Its Q1–Q5 classification uses young-plus-older employment-stock weights over the same 108 static estimation months as the existing headline comparison. Keep tied values together through the existing weighted-quintile helper. Q1 is omitted and Q2–Q5 enter separately. Webb enters as the single standardized comparison-technology-by-young-by-post interaction. Fixed effects, occupation clustering, and one-step wild-score inference are unchanged. Use 999 Rademacher draws with seed `2026090303`.

No continuous-F, G, residual, alternative-cut, alternative-support, or alternate-factor outcome model is allowed.

Report the F Q5–Q1 coefficient, analytic occupation-cluster SE, one-step wild-score p-value and 95% interval, `100(exp(beta)-1)`, support count/share, and Q1/Q5 Jaccard overlap with each frozen architecture.

Use the weakest previously reported literal-common-support magnitude, `|beta| = 0.07385795`, as the non-arbitrary existing-result reference:

- `SC-A`: coefficient negative, upper wild-score interval below zero, and absolute coefficient at least `0.07385795`.
- `SC-B`: coefficient negative but either the upper interval includes zero or magnitude is below `0.07385795`.
- `SC-C`: coefficient is zero or positive.

## 5. Joint architecture-robust sign inference

Use the exact 444-occupation support, six frozen architecture-specific Q5 maps and Webb controls from the existing Table 5B specifications. Reconstruct the six frozen fits solely to recover aligned occupation-cluster influence contributions; verify point estimates against the sealed Table 5B CSV to tolerance `1e-10`. This verification is supporting inference, not a new architecture specification.

Use one common `999 × 444` Rademacher multiplier matrix, seed `2026090304`. Preserve the six-by-six covariance of centered coefficient shifts. Let:

- joint null `H0 = union_m {theta_m >= 0}`: at least one architecture coefficient is nonnegative;
- joint alternative `H1 = intersection_m {theta_m < 0}`: every architecture coefficient is negative.

Construct 95% simultaneous one-sided upper bounds using the 95th higher quantile of the draw-wise maximum of `-shift_m / analytic_SE_m`. Also report each one-sided marginal randomization tail area and the intersection-union p-value `max_m p_m`. The joint all-negative statement is supported only if every simultaneous upper bound is below zero; otherwise report that it is not supported. No model averaging or common-parameter interpretation is allowed.

## 6. Final path and stopping rule

- `PATH-P3-A` only if `HB-A`, `SC-R1`, and `SC-A` all hold.
- `PATH-P3-C` if any of `HB-C`, `SC-R3`, or `SC-C` holds.
- `PATH-P3-B` otherwise.

Build exactly one V5 consistent with the selected path, label all Phase 3 material post-outcome exploratory, run the full repository suite in a clean SCC checkout, seal receipts and hashes, push, verify the remote commit, and stop. No Phase 4 is authorized.

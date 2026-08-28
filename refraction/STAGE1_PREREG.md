# Refraction — Stage-1 pre-registration

Registered spec: **SPEC-MAIN-v2.4**. Generated from `refraction/frozen_config.yaml`; every value below is injected from that file, not written by hand.

Stage 1 registers what is already determined and requires no data. Stage 2 appends only quantities a stage-1 algorithm computes: realized_w_shrink, g8_outcome_arm_selected, usable_cluster_counts, realized_sample_sizes, g7_coverage_shares, gate0_pass_fail_lines. Changes to hypotheses, estimators, decision rules or thresholds are forbidden at stage 2.

## 1. Sample frame

| item | value |
|---|---|
| announcements_start | 2017-01-01 |
| announcements_end | 2026-06-30 |
| waves_start | 2021-03-01 |
| waves_end | 2025-06-30 |
| pre_quarters_required | 8 |
| post_quarters_required | 4 |
| announcement_types | FOMC |

## 2. The flow measure (CR)

    CR_{f,t} = (S_{f,t} - S_{f,t-1}) / S_{f,t-1}

| element | registered value |
|---|---|
| source | Plan v2.4 §6.1.2, frozen |
| numerator | etf_shares_outstanding_difference |
| numerator_uses_price_or_nav | no |
| denominator | shares_outstanding_prior_trading_day |
| denominator_timing | t_minus_1 |
| sign_convention | positive_is_creation_inflow |
| shares_corporate_action_adjusted | yes |
| corporate_action_convention | p1/t2_wrds/corpactions.py |
| undefined_on_missing_prior_day | yes |

### Primary exposure magnitude

    CR_mag = |CR_raw|

| element | registered value |
|---|---|
| transform | identity |
| centering | none |
| scaling | none |
| winsorization | none |
| standardize_within_fund | no |

No centring, no within-fund scaling, no winsorization. Creation/redemption is rare, and any fund-specific statistic computed on a mostly-zero series is dominated by the zeros: a fund with 2 nonzero days in 250 has a within-fund 99th percentile of zero, which would clip both of its genuine events to zero exposure. Comparability across funds is handled by the fund x date fixed effects, which absorb any fund-level scale.

### Robustness exposure magnitude (never the primary)

| element | registered value |
|---|---|
| column | CR_mag_capped |
| clip | upper_tail_only |
| clip_pct | 99 |
| clip_estimated_on | nonzero_event_magnitudes_only |
| min_nonzero_events_for_fund_specific_cap | 20 |
| pooled_cap_fallback | yes |
| preserve_zero_exactly | yes |
| never_zero_a_genuine_event | yes |
| scaling | none |
| may_replace_primary | no |

Columns: raw `CR_raw` (sign, zero-event status, event census, concentration); untreated magnitude `CR_mag_raw`; primary exposure magnitude `CR_mag`; robustness column `CR_mag_capped`.

Invariants, enforced on every build:

- **zero_iff_zero** — `CR_raw == 0  <=>  CR_mag == 0`
- **non_negative** — `CR_mag >= 0`
- **symmetric** — `equal-and-opposite raw values map to equal CR_mag`
- **monotone** — `|CR_raw| ordering is preserved exactly (the primary is the identity)`

## 3. G8 — first-stage mechanism validation

Primary outcome class `trading_connectivity`; exposure `abs_CR_x_absL`. The signed form `signed_CR_x_absL` is forbidden for the primary and belongs only to the return corroboration.

### 3.1 The two candidate arms

| arm | outcome | exposure | sided | requires |
|---|---|---|---|---|
| preferred | `sign(CR^raw_{f,t}) * (SignedDollarImbalance_{i,t} / ADV_pre_i)` | abs_CR_x_absL | one_sided | signed_trade_classification |
| fallback | `(DollarVolume_{i,t} - ADV_pre_i) / ADV_pre_i` | abs_CR_x_absL | one_sided | intraday_or_daily_volume |

### 3.2 The arm-selection rule (data quality only, resolved before any coefficient)

| criterion | floor |
|---|---|
| signed_trade_classification_available_share_min | 0.9 |
| intraday_coverage_share_of_volume_sample_min | 0.95 |
| cross_algorithm_daily_oib_sign_agreement_min | 0.95 |
| cr_timestamp_audit_complete | yes |

All must hold; otherwise the fallback arm. Decided before any treatment coefficient: yes. Recorded in `refraction/G8_OUTCOME_CHOICE.md`.

### 3.3 Outcome unit

| element | registered value |
|---|---|
| numerator | signed_dollar_imbalance |
| denominator | adv_dollar_pre |
| unit | fraction_of_predetermined_average_daily_dollar_volume |
| adv_window_trading_days | -252, -22 |
| adv_statistic | median |
| adv_min_nonzero_days | 60 |
| winsorize_outcome_pct | 1, 99 |
| log_transform | no |

### 3.4 Design

Pooled interaction, fixed effects `fund_x_date`; CR-interacted controls: size, illiquidity, index_membership, pre_period_etf_ownership, pre_conversion_holding_weight (all predetermined). Post-treatment controls forbidden in the baseline: realized_creation_basket_weight, post_conversion_holding_weight, post_conversion_etf_ownership. Response lag: primary 0 day(s), corroborating 1 day(s).

Calibration window: start_trading_days_after_conversion = 21; end_trading_days_after_conversion = 252; exclude = fomc_statement_dates, fomc_press_conference_dates, fomc_minutes_dates; exclude_buffer_trading_days = 1.

### 3.5 Decision rule

Outcomes: licensed, not_licensed_inconclusive, retired_from_headline, INSUFFICIENT_IDENTIFYING_VARIATION.

- Test is one-sided on the linear coefficient at `first_stage_primary_alpha` = **NOT SET** (stage 2).
- Retirement requires an equivalence margin (`first_stage_equivalence_margin` = **NOT SET** (stage 2)); without one, a non-significant estimate is **inconclusive**, not retired.
- `INSUFFICIENT_IDENTIFYING_VARIATION` is a numerical-degeneracy classification: min_nonzero_cr_days = 2; degenerate_exposure_rank_tol = 1e-10; mde_sigma_max = **NOT SET** (stage 2); mde_sigma_max_may_not_inherit_from = gate0_thresholds.mde_sigma_max; power_target = 0.8.
- Power trigger active: no. MDE is reported in every case but classifies nothing.
- Reported for every outcome: a1, se_a1, ci_low, ci_high, t_a1, p_one_sided, mde_sigma, n_obs, n_nonzero_cr_days, share_of_fund_days_nonzero, concentration_top1_share, concentration_top5_share, n_effective_fund_clusters, n_effective_adviser_clusters, n_effective_event_clusters, within_fund_date_exposure_sd.
- Headline use permitted only when: licensed.

## 4. G9 — portfolio continuity

Corporate-action convention: `p1/t2_wrds/corpactions.py`, field `cfacshr`; as-of field `report_dt` (report date, never a filing date). Continuity is reported continuously with threshold sensitivities; the registered anchors are **NOT SET** (stage 2) / **NOT SET** (stage 2) / **NOT SET** (stage 2).

Response if continuity fails: restrict_to_high_continuity_waves

## 5. Shrinkage weight — the algorithm, not the value

`beta.w_shrink` = **NOT SET** (stage 2) at stage 1; it is a **stage-2** quantity, computed by the frozen algorithm below from the G2 sweep.

Candidate grid, frozen at stage 1: min 0.0, max 1.0, step 0.1, 11 points, endpoints included yes. Post-sweep refinement forbidden: yes.

    grid = 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0

Feasibility at a grid point requires all four G2 conditions:

| condition | threshold |
|---|---|
| sd_L_min | 0.25 |
| corr_L_convexp_max | 0.3 |
| n_pre_median_min | 30 |
| se_share_min | 0.7 |

Selection: **midpoint_of_longest_feasible_run**. Minimum qualifying run length = `sweep_window_min_gridpoints` = 2 grid points. Tie-breaks: run earliest_start, midpoint lower. No feasible run → FAIL_G2.

Implemented in `refraction/pipeline/w_shrink.py`.

## 6. Gate-0 thresholds

| threshold | value |
|---|---|
| convexp_treated_min | 0.005 |
| corr_L_convexp_max | 0.3 |
| d_b_mass_share_min | 0.5 |
| d_b_min | 0.1 |
| estimator_fallback_if_vecm_unstable | arbitrage_gap_convergence, lead_lag |
| first_stage_primary_alpha | **NOT SET** (stage 2) |
| g7_tests_vecm_estimability | yes |
| g9_confirmatory_response | restrict_to_high_continuity_waves |
| g9_failure_response | restrict_to_high_continuity_waves, relabel_treatment |
| g9_reporting | continuous_with_threshold_sensitivity |
| g9_secondary_interpretation | wrapper_plus_portfolio_change_reported_separately |
| intraday_coverage_min | 0.7 |
| intraday_vendor_agreement_tol | **NOT SET** (stage 2) |
| mde_sigma_max | 0.5 |
| n_pre_median_min | 30 |
| portfolio_overlap_min | **NOT SET** (stage 2) |
| portfolio_turnover_max | **NOT SET** (stage 2) |
| portfolio_weight_corr_min | **NOT SET** (stage 2) |
| pretrend_individual_lead_adjust | holm |
| pretrend_joint_p_min | 0.1 |
| sd_L_min | 0.25 |
| se_share_min | 0.7 |
| se_to_sdL_ratio_max | 0.3333 |
| surprise_coverage_min | 0.95 |
| sweep_window_min_gridpoints | 2 |
| vecm_min_effective_obs_per_event | **NOT SET** (stage 2) |

Null entries are undecided by policy: R3 stops rather than defaulting them, and any value they later acquire must arrive with a recorded owner decision.

## 7. Lookahead and prereg-before-outcomes

Betas, lever and weights use only data strictly before a wave's effective date (assert A4). Any estimation touching post-period outcomes calls `guards/prereg_guard.py::assert_prereg_ok()`, which refuses until `prereg.osf_timestamp` and `beta.w_shrink` are set.


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

No centring, no within-fund scaling, no winsorization. Creation/redemption is rare, and any fund-specific statistic computed on a mostly-zero series is dominated by the zeros: a fund with 2 nonzero days in 250 has a within-fund 99th percentile of zero, which would clip both of its genuine events to zero exposure.

CR is cross-fund comparable **because it is a unitless proportional change** — a 2% creation is a 2% creation at any fund size — so no further scaling is required. The fund x date fixed effects are a separate mechanism and do not normalize the interaction: they absorb fund-day common components (the CR level among them), and `CR_ft x |L_i|` is then identified from constituent-level `|L_i|` variation within the fund-day.

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

### 3.4 CR event timing (binding on the sample)

A CR change is **dated** only on per-observation evidence that the ECONOMIC observation is as of that day, at BOTH endpoints of the change (economic_as_of_freshness_at_t, economic_as_of_freshness_at_t_minus_1). Otherwise it is an **interval** event of width days_back_to_last_fresh_observation.

Freshness means the economic as-of date, **not** that the vendor file or API response was refreshed that day. A feed can restamp, republish or re-serve a row daily while the shares-outstanding figure still refers to an earlier economic as-of date; a publication timestamp certifies that the pipeline ran, not when the shares were counted. So a per-observation as-of date is necessary but not sufficient — it must sit against a **documented_daily_economic_cutoff** establishing what "as of day t" means for this field.

| freshness evidence | status |
|---|---|
| per_observation_economic_as_of_date | sufficient, WITH documented_daily_economic_cutoff |
| vendor_file_publication_timestamp | never sufficient alone |
| api_response_timestamp | never sufficient alone |
| vendor_refresh_flag | never sufficient alone |
| row_republished_indicator | never sufficient alone |
| file_last_modified | never sufficient alone |

**A documented cutoff fixes the as-of DATE; it does not by itself align the two measurement intervals, and calendar-date equality is not alignment.** CR differences two cutoff snapshots, so it spans `(economic cutoff at t-1, economic cutoff at t]`, while OIB spans a trading session. Those coincide only when the cutoff is the market close.

| cutoff | alignment class | OIB window | may enter the primary |
|---|---|---|---|
| cutoff_time_is_market_close | close_to_close_rth_declared | rth_session_day_t | yes |
| cutoff_time_known_and_documented | aligned_cutoff_to_cutoff | cutoff_t_minus_1_to_cutoff_t | yes |
| nothing_further_is_knowable | unaligned_unknown_cutoff | **NOT SET** (stage 2) | no |

**Coverage is required for every class, on whatever window that class registers (`yes`), and a market-close cutoff is not exempt.** A close-to-close CR interval is `(close_{t-1}, close_t]`, which contains the overnight and pre-market session, so an RTH-only outcome does not literally cover it. That class therefore DECLARES its estimand — RTH constituent trading associated with day-localized close-to-close NET CR — rather than claiming exact alignment, and names the uncovered stretch (overnight_and_pre_market). An exact-alignment claim requires full-window OIB coverage (`yes`). Partially covered observations are **downgrade_to_interval_robustness**; where the feed covers only part of the registered window the measured imbalance is a partial-window quantity paired with a full-interval CR — a different variable, whose gap is systematic rather than random.

Alignment is a **separate condition from datedness**: an event can be day-localized and still interval-misaligned, and such an event may not enter the same-day primary (it goes to interval_robustness). Where the cutoff is a known non-close time, OIB must be constructed over the matching cutoff-to-cutoff window rather than taken from the trading session. Where the cutoff time is unknown, the claim `exact_same_day_interval_alignment` is forbidden.

**Timing eligibility applies to zero-CR observations too.** An observed `CR_raw = 0` is a claim and needs the same endpoint evidence as a nonzero event. Unchanged shares outstanding under carry-forward are an absence of measurement, and would otherwise enter the regression as a zero-exposure control drawn from days nobody looked at.

What a verified zero establishes is **zero NET CR over the interval**, not zero gross AP activity: a creation and a redemption of equal size inside the interval also leave the share count unchanged. These are valid zero observations for the registered net-CR estimand, and they may **not** be interpreted as no-AP-activity controls.

| zero class | meaning | may enter the primary |
|---|---|---|
| zero_net_verified | an observed and measured ZERO NET creation/redemption day | yes |
| zero_net_unverified | unchanged shares whose endpoints were not both freshly measured | no |

`zero_net_verified` requires economic_as_of_freshness_at_t, economic_as_of_freshness_at_t_minus_1, cr_oib_interval_alignment — the same conditions a dated event requires. Unverified zeros in the primary: **excluded**; treating them as no-creation days: **no**.

**Dated is day-localized only.** It does not establish within-day ordering between AP activity and constituent order imbalance: both are measured over the same day and either could precede the other. Same-day G8 is therefore **mechanism_association_and_calibration**, not a causal sequence; within-day ordering would require true_ap_transaction_timestamps.

**The rule does not bend for data availability.** If the vendor lacks the freshness metadata, G8 returns `INSUFFICIENT_IDENTIFYING_VARIATION` on the same-day primary rather than a relaxed standard.

A run of equal shares outstanding is **not** evidence of carry-forward. A genuinely daily series is constant on every day without a creation or redemption, which for most funds is most days; "same value" and "stale observation" are different claims and the share series alone cannot separate them. Equal-value runs are carried as a staleness **diagnostic** only. Under verified daily freshness a constant stretch is a run of genuine zero-CR days, and the change that ends it is still dated.

| rule | registered value |
|---|---|
| primary_sample | dated_only |
| interval_events_in_primary | excluded |
| interval_events_may_be_matched_same_day | no |
| absent_freshness_evidence | interval |
| equal_value_runs_are_diagnostic_only | yes |
| equal_value_run_is_sufficient_proof_of_carryforward | no |
| verified_freshness_zero_days_stay_zero_days | yes |
| on_unaudited_refresh | all_events_interval |

Interval events may **not** be paired with same-day constituent order imbalance: the vendor's update day is the one day in the interval guaranteed to carry a printed share change, so a same-day pairing dates constituent trading to a day the data cannot support, in the direction that manufactures a same-day association.

They are not discarded. Interval-level robustness outcome:

| element | registered value |
|---|---|
| outcome | cumulative_aligned_signed_dollar_imbalance_over_the_interval |
| normalization | sum_over_interval_days / (adv_dollar_pre * interval_days) |
| exposure | abs_CR_x_absL |
| sign_source | CR_raw |
| interpretation | net_interval_association |
| recovers_gross_ap_activity | no |
| recovers_event_timing_within_interval | no |
| offsetting_flows_within_interval_are_unobserved | yes |
| role | robustness_only |
| may_replace_primary | no |

This is reported as a **net interval association**. Net change in shares outstanding is a net quantity: a creation and a redemption inside the same interval cancel, so a quiet net figure can sit on top of heavy two-way AP activity. It therefore recovers neither gross AP activity nor event timing within the interval, and may not be described as either.

Reported in every case: n_dated_events, n_interval_events, median_interval_width_days, share_of_events_dated.

### 3.5 Design

Pooled interaction, fixed effects `fund_x_date`; CR-interacted controls: size, illiquidity, index_membership, pre_period_etf_ownership, pre_conversion_holding_weight (all predetermined). Post-treatment controls forbidden in the baseline: realized_creation_basket_weight, post_conversion_holding_weight, post_conversion_etf_ownership. Response lag: primary 0 day(s), corroborating 1 day(s).

Calibration window: start_trading_days_after_conversion = 21; end_trading_days_after_conversion = 252; exclude = fomc_statement_dates, fomc_press_conference_dates, fomc_minutes_dates; exclude_buffer_trading_days = 1.

### 3.6 Decision rule

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


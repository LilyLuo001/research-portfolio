# FOMC two-step identification plan

## Verdict

**NOT VIABLE as a current headline; conditional secondary design only.** Stock-event rows do not create independent macro shocks. The effective treatment count is the number of FOMC announcements with usable predetermined exposure and a credible first stage.

## Step 1: estimate one cross-sectional response slope per FOMC event

For each FOMC date `t`, estimate the cross-sectional slope of the pre-specified stock response on frozen exposure to the ETF architecture channel. The response may be a short-window return, signed volume, or price-discovery measure only when the required data exist. Include pre-announcement beta, size, industry, and liquidity controls frozen from lagged data. Save `beta_t`, its standard error, sample size, exposure dispersion, and influence diagnostics.

Statement and press-conference windows must be separate. Overlapping earnings or firm-news windows are excluded by a fixed news-screen rule. With no TAQ, only daily/available quote-based outcomes can be scoped; the intended intraday test cannot currently run.

## Step 2: explain date-level slopes with monetary-policy news

Estimate `beta_t = alpha + gamma × monetary_policy_surprise_t + controls_t + error_t` at the **FOMC-date level**. Use a pre-selected high-frequency policy surprise series and separate target/rate-path components if coverage supports them. Precision weighting may use capped inverse variance fixed ex ante; show unweighted estimates as primary robustness so one high-precision date cannot dominate.

## Inference and falsification

- The reported N is FOMC dates, not stocks or stock-date rows.
- Use date-level randomization/sign inference and small-sample robust intervals. Cluster-by-stock standard errors are invalid for the macro interaction.
- Report leave-one-FOMC-date-out and leave-one-policy-cycle-out estimates.
- Placebo dates use the same weekday/time and preserve exposure dispersion.
- Require the `L_tilt` first-stage kill test to pass before interpreting `gamma` as an arbitrage mechanism.

## Promotion gate

Do not estimate the two-step treatment coefficient until there are at least 24 usable FOMC dates, at least 18 after all contamination screens, and no date supplies more than 15% of total precision weight. The current conversion-era window is unlikely to satisfy this with strong independent exposure variation. A historical extension is permissible only if exposure is constructed with the same rule and without post-event information. Until then this is a design option, not an empirical result.

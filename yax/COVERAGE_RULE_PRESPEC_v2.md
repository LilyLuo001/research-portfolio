# Exposure-coverage rule v2

**Recorded 2026-08-29 before any protected post-period outcome was opened.**

This file implements, without further change, the Rule A decision already
recorded in `FREEZE_AMENDMENT_2026-08-27.md` and `RESEARCH_PLAN_v5.md`.
`COVERAGE_RULE_PRESPEC_v1.md` remains preserved as the original decision record.

## The three frozen rules

- **Rule A — STRICT (PRIMARY).** Include a Census occupation only when every
  component is exposure-scored (`s_c = 1`). The resulting estimand is the
  full-component published-exposure support, covering 88.70% of eligible
  employment. The failed original 90% gate is disclosed permanently.
- **Rule B — SIBLING-IMPUTED.** Include occupations with `s_c >= 0.95`; impute
  an unscored component from the employment-weighted scored siblings in its
  six-digit SOC parent broad group.
- **Rule C — RENORMALIZED.** Include occupations with `s_c >= 0.95`; compute
  exposure from scored components only after renormalizing their weights.

Rule A is **PRIMARY**. Rules B and C remain required reported sensitivity
columns, with coverage, excluded occupations and movements between rules named.
The 0.95 threshold for Rules B and C does not move.

## Ordering and disclosure

The primary changed from Rule B in v1 to Rule A before outcomes were opened for
the reason documented in the 2026-08-27 amendment: the visible sequence under
Rule B was failed strict gate followed by imputation. This is a disclosed
pre-outcome design revision, not a claim that v1 named Rule A. Both records must
be cited in the paper's design history.

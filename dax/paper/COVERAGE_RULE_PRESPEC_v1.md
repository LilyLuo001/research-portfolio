# Pre-specification: the exposure-coverage rule

**Written 2026-08-25, BEFORE any post-ChatGPT outcome has been opened.**
**Commit this file before the design-freeze tag. It is void if committed after.**

## Why this document exists

The predeclared primary rule required ≥90% exposure-route coverage of eligible
employment. On the real pre-period panel it returned **88.70%** and therefore
**failed**. That failure is recorded, not patched: no design freeze was created,
and the power run that followed is labelled
`DIAGNOSTIC_AVAILABLE_SUPPORT_ONLY`.

The failure has a diagnosed cause, and the cause makes the strict rule look
wrong rather than binding. The top 25 target codes account for **93.4%** of the
excluded exposure mass. Two of them — Janitors and Building Cleaners, and Cooks
— are about **2.50% of all eligible employment** despite component coverage of
**99.38%** and **99.27%**. The fail-closed rule discards the entire Census
occupation when any component is unscored, so an occupation that is 99.4%
covered contributes nothing.

The unscored components are overwhelmingly residual "All Other" SOC categories
that O\*NET, and therefore Eloundou, never rated: Building Cleaning Workers,
All Other; Cooks, All Other; several All Other teacher categories; Surgeons,
All Other. For Janitors and Cooks these are under 1% of the Census occupation.
For broader teaching groups they are much larger.

**That is a measurement choice, not a clerical fix.** Sibling imputation is
defensible when the unscored residual is a small tail of an otherwise-scored
occupation and indefensible when it is most of the occupation. Choosing the
threshold after seeing outcomes would destroy the only thing this chapter has
that the contested literature does not: a specification fixed in advance.

So all three rules are specified here, now, with the primary named in advance.

## The three rules

Let an eligible Census occupation *c* have exposure-scored component employment
share `s_c` ∈ [0,1] — the fraction of *c*'s employment whose SOC components
carry an exposure score.

### Rule A — STRICT (the original predeclared rule)

Include *c* only if `s_c` = 1. Occupations with any unscored component are
dropped entirely.

- Coverage achieved: **88.70%** of eligible employment. Fails the 90% gate.
- Interpretation: assumes unscored components are non-ignorably different, and
  refuses to extrapolate at all.

### Rule B — SIBLING-IMPUTED, THRESHOLDED (**PRIMARY**)

Include *c* if `s_c ≥ 0.95`. For included *c*, impute each unscored component's
exposure as the **employment-weighted mean of the scored components within the
same 6-digit SOC's parent broad group**, then form *c*'s exposure as the
employment-weighted mean over all components.

Occupations with `s_c` < 0.95 are dropped and reported, not imputed.

- Rationale for 0.95: it admits Janitors (99.38%) and Cooks (99.27%), where the
  unscored residual is a negligible tail, and excludes the broad teaching
  groups, where the residual is large enough that a sibling mean is a guess.
  The threshold is set by the *structure of the missingness*, which was
  diagnosed on outcome-blind pre-period data only.
- **This is the primary rule.** Named before estimation, on the reasoning
  above, not on any comparison of results.

### Rule C — RENORMALIZED

Include *c* if `s_c ≥ 0.95`. Form *c*'s exposure as the employment-weighted
mean over the **scored components only**, renormalizing weights to sum to one.
No imputation.

- Interpretation: assumes unscored components are missing at random *within*
  the occupation — a weaker assumption than B's sibling mean, but one that
  silently reweights toward whichever components happened to be scored.

## What must be reported

All three rules, in every results table, as three columns. Not one primary with
two robustness footnotes — three columns, always, so a reader can see the
measurement choice rather than take it on trust.

Additionally report, once:

- the coverage achieved by each rule
- the number of occupations and the employment share each rule drops
- the exposure-value correlation between rules B and C across occupations
- the named occupations that move between rules

## Anti-search commitments

1. This file is committed before the design-freeze tag. If the tag exists
   first, this pre-specification is void and the coverage rule must be treated
   as a post-hoc choice and labelled as one in the paper.
2. The primary is **Rule B**, fixed here. It does not change because another
   rule gives a cleaner result.
3. The 0.95 threshold does not move. If it is wrong it is wrong in the paper.
4. If the three rules disagree materially, that disagreement **is a reported
   result** about the fragility of occupation-level exposure measurement. It is
   not a problem to be resolved by picking one.
5. No post-ChatGPT outcome is opened until this file and `DESIGN_FREEZE_v1.md`
   are both committed and the `v1.0-preregistered` tag exists.

## Provenance

- Coverage failure receipt: `young_relative_employment_cells_v1_receipt.json`
- Failure audit: `coverage_failure_audit_{target,source}.csv`,
  `coverage_failure_audit_summary.json`
- Audit code: `dax/memo/power_calcs/audit_preperiod_coverage_failure.py`
- All computed on the outcome-blind pre-period file (6,188,956 rows) from the
  wide extract (9,262,480 rows).

# R3 BCC public-grouping bridge specification

**Status:** POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.  
**Registry scope:** BCC-01 through BCC-03 only.

This specification was written before the new R3 BCC-bridge estimates were
computed.  It implements only the publicly reproducible part of the August 12,
2026 Brynjolfsson--Chandar--Chen (BCC) design: Eloundou GPT-4 beta exposure and
a top-two-versus-bottom-three exposure contrast.  It is a CPS employment-stock
bridge, not a replication of BCC's proprietary ADP population, worker--firm
match unit, title-to-SOC mapping, balanced-firm panel, firm-time controls, or
hiring and separation outcomes.

## Verified facts and unresolved membership

The accompanying primary-source audit establishes that BCC uses Eloundou et
al.'s GPT-4 beta measure and reports exposure quintiles.  The official Canaries
Dashboard says occupations receive equal weight when exposure groups are
formed; BCC's occupation-level outcome regressions subsequently use employment
weights.  The inspected public materials do not provide a complete occupation
membership file or all cutoff and tie mechanics.  BCC's public CPS Tracker uses
unweighted occupation-level `pandas.qcut` for a related quartile exercise, which
is corroborating but not dispositive implementation evidence.

Accordingly, this module reports two constructions, neither called BCC-exact:

1. `historical_YAX_employment_weighted_approximation`: the historical YAX
   employment-weighted, tie-preserving GPT-4 beta quintiles on the fixed
   468-occupation YAX support.  The cut weights are total young-plus-older CPS
   stock over the historical 108-month static panel, including postperiod
   months.  This reproduces the earlier YAX bridge, but it is not the grouping
   rule documented by the official dashboard.
2. `public_dashboard_equal_occupation_approximation`: equal-occupation,
   tie-preserving GPT-4 beta quintiles on the same 468 occupations.  Each
   occupation has cut weight one.  A score equal to a cutoff remains in the
   lower quintile (`searchsorted(..., side="left")`).  This is the closest
   reconstruction possible on the available YAX classification and common
   support.  It does not establish concordance with BCC's proprietary
   SOC-2010/title universe or its exact memberships.

Keeping the model support fixed isolates the documented cut-weight change.
It does not repair the unresolved difference between BCC's occupation universe
and the Census-2018 occupations in YAX.

## Common CPS outcome design

All static models use March-restored CPS employment stocks from January 2017
through July 2026, exclude December 2022 as the transition month, and retain
the genuine October 2025 collection gap.  The outcome is the grouped-binomial
young share for ages 22--25 versus ages 26--65, with occupation and time fixed
effects.  It is therefore a young-relative national CPS stock coefficient, not
BCC's within-young occupation long difference or its aggregate 19-percent
kept-pace statistic.

Both grouping constructions use the same occupations, outcome cells, Eloundou
beta values, historical Webb-software normalization, and 9,999 common
occupation-level Rademacher multipliers (seed `2026090561`).  `high` means Q4
or Q5; `low` means Q1 through Q3.  The coefficient is `high x post`, where post
starts in January 2023.  Every static construction retains the historical
standardized Webb-software-by-post slope.

For each grouping, estimate:

1. `occupation_plus_calendar_month_FE`: occupation and calendar-month fixed
   effects, with no SOC2 conditioning;
2. `SOC2_x_post`: row 1 plus SOC2-by-post slopes, omitting the stock-largest
   SOC2 family as the redundant reference; and
3. `SOC2_x_calendar_month`: occupation and SOC2-by-calendar-month fixed
   effects.

The latter two change the conditioning estimand; they are not additive
decompositions.  Report point estimates, occupation-cluster standard errors,
wild-score intervals and p-values, information diagnostics, and paired changes
under common multipliers.  Also pair the two grouping rules within each fixed-
effect structure.  An interval containing zero means the design does not
detect a difference; it does not establish equivalence.

For descriptive endpoint alignment, report November 2022 to June 2026 young
and older stock growth and the within-age high-group kept-pace contrast under
each approximate grouping.  These aggregates have no hiring interpretation.

## BCC-03 dynamics

Computationally permitting, fit a fully interacted quarterly companion for both
groupings under (i) occupation plus calendar-month fixed effects and (ii)
occupation plus SOC2-by-calendar-month fixed effects.  The omitted event bin is
2022Q4, observed here in October and November because December 2022 is excluded.
For every other quarter include `high x quarter` and standardized
`Webb-software x quarter`.  Report the complete high-path, pointwise and
simultaneous intervals, joint preperiod and postperiod tests, the complete
target covariance, and occupation influence representations.  Use the same
common multipliers across grouping rules and report paired dynamic differences.

Quarterly dynamics are a YAX companion estimand; they are not BCC's rolling
occupation long-difference regression.  If any dynamic model fails or is
computationally infeasible, retain the failure and complete BCC-01/BCC-02.

## Required output labels

Every result records the BCC version, CPS population and unit, age bands,
calendar endpoints, contrast, exposure measure, cut/tie/weight rule,
membership-concordance status, regression weights, conditioning set, and
inference procedure.  No output may contain `BCC-exact` or describe this module
as an ADP replication.

## Outputs

- `BRIDGE_MEMBERSHIP.csv`, `BRIDGE_GROUP_SUMMARY.csv`,
  `BRIDGE_MEMBERSHIP_CONCORDANCE.json`
- `STATIC_MODEL_RESULTS.csv`, `STATIC_PAIRED_DIFFERENCES.csv`,
  `STATIC_INFORMATION_BY_OCCUPATION.csv`, `STATIC_GROWTH_ENDPOINTS.csv`
- `DYNAMIC_PATHS.csv`, `DYNAMIC_JOINT_TESTS.csv`,
  `DYNAMIC_PAIRED_GROUPING_DIFFERENCES.csv`,
  `DYNAMIC_TARGET_COVARIANCE.csv`, `DYNAMIC_TARGET_INFLUENCE.csv`
- `MODEL_FAILURES.json`, `EXECUTION_RECEIPT.json`, `SELF_CHECK.json`, and
  `FINDINGS.md`

# Rebuilt-treatment FAM-01--FAM-06 contract harmonization

Status: **post-outcome exploratory contract harmonization, written before the
rebuilt-treatment FAM results in this directory were run**

The earlier registered FAM-01--FAM-06 implementation used historical treatment
assignments. The revised manuscript uses the corrected-preperiod rebuilt
treatment contract throughout. This package therefore reruns the identical
within-family models, support definitions, age groups, calendar, seeds, draws,
inference routines, LOFO rules, information formulas, and trajectory-selection
rule using `REBUILT_TREATMENT_MEMBERSHIP.csv`.

The harmonization changes only these treatment inputs on the same 468-
occupation support:

- fixed beta-quintile membership comes from the rebuilt file;
- raw Rule-A beta values come from its `rule_A_beta` field;
- Webb-software values and preperiod normalization weights come from its
  `webb_pct_software` and `preperiod_weight` fields.

The original 9,999-draw occupation Rademacher procedure and seed 2026090517 are
retained. Outputs include the full Q2--Q5 profile and joint tests under baseline,
SOC2-by-post, and SOC2-by-calendar-month conditioning; direct-tail models and
support; continuous within-family models; LOFO and information diagnostics; and
the already-registered information-ranked family trajectories.

One additional public aggregate is produced for figure construction: for each
of the corrected 113 months and rebuilt Q1/Q5, sum survey-weighted employment
stock separately for ages 22--25 and 26--65, then report their ratio, log ratio,
and own-preperiod-mean indices. It contains no person record or occupation-month
cell. This is a deterministic aggregation of the same fitted input panel, not a
new regression specification.

Historical-only FAM rows are comparison artifacts and must not enter the revised
main-text results as though they used the rebuilt treatment contract. Any failed
rebuilt model remains a blocker; no thresholds, supports, or models may be
changed after results are seen.

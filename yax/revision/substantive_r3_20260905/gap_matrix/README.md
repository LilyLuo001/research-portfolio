# Substantive R3 requirement-to-status gap audit

Audit date: 2026-09-05

Repository snapshot audited: `6b8d85e` on branch
`task/yax-substantive-revision-r3-20260905`.

This is a read-only inventory of the repository and supplied text attachments.
No protected CPS outcome record was opened for this audit, no model was fit, and
no result was inferred from an unexecuted script.  Statuses describe what exists
at the audited snapshot; they are not claims that the new revision has been
completed.

## Bottom line

The repository contains a substantial first major-revision package, but the new
execution prompt is materially broader.  The strongest reusable modules are the
historical corrected-calendar estimate, SOC2-by-post and SOC2-by-month target
estimates, architecture paired comparisons, calendar/crosswalk audits,
population-control diagnostics, BCC public-grouping bridge, and adjacent-month
flow work.  The load-bearing missing modules are:

1. a **fully rebuilt corrected treatment pipeline** rather than corrected cells
   with historical treatment held fixed;
2. the full conditional Q2--Q5 profile, direct-tail and continuous within-family
   estimands, leave-one-family-out results, and family-level trajectories;
3. actual **conditioning on occupational characteristics**, including a
   defensible pandemic-shortfall object, rather than treating characteristics as
   alternative exposure rankings;
4. SOC2 few-cluster inference, household/sample-unit reaggregation of core CPS
   cells, and a valid full-refit or coverage benchmark;
5. a corrected-calendar, family-conditioned dynamic design plus the requested
   trend-sensitivity, seasonality, onset-date, and endpoint program;
6. BCC grouping under SOC2-by-post and SOC2-by-month, exact endpoint/population
   alignment, and a documented decision on stock--flow calibration;
7. twelve-month links and a scoped feasibility/estimation program for hours,
   earnings, unemployment, and labor-force participation;
8. the requested manuscript contraction and removal of stable tails, mobility
   rematching, and F/G from the scientific paper and appendix; and
9. new deliverables: separate editor/R1/R2 responses, a complete machine-readable
   matrix, a unified master command, covariance outputs, a change-marked draft,
   and new numerical/inference audits.

The detailed inventory is in `GAP_MATRIX.csv`.

## Input audit and report-version conflict

The following supplied inputs were located:

| Input | Located file | SHA-256 | Finding |
|---|---|---|---|
| Integrated execution prompt | `<SUPPLIED_INPUT:R3_EXECUTION>` | `8e4dc7e60a5ac9fc70799b669fb140b2dfa44c2a67589bdd87f31afdead8851c` | Authoritative new execution specification. |
| Referee report, 12 major and 14 secondary comments | `<SUPPLIED_INPUT:R1>` | `f5af3adc0774002fe3f0f76f7959ba336b47ff6a03b55aab6c49bf7141b73c67` | Matches the report called RR1 in the existing September 5 revision package. |
| Referee report, 9 major comments plus six specific corrections | `<SUPPLIED_INPUT:R2>` | `78dd89b842934e10842e202b6578b655a4afb4bd1efb2a20a47cf2c05bda5146` | Matches the report called RR2 in the existing package. |

There is a version conflict that the new revision must not hide.  The integrated
prompt identifies R2 as a report with sections `3.1--3.9`, `4.1--4.9`, and
`5.1--5.11`; neither located report has that numbering.  The second located
report has nine numbered major comments, followed by six unnumbered specific
corrections.  Consequently, the integrated prompt can be executed, but a claim
that every sentence of the specially described R2 has been answered is blocked
until that exact report is located or the owner confirms that the second file is
the intended R2.  The prior response letter's statement that it resolves every
numbered major comment is true only for the two located reports, not necessarily
for the newly described version.

## Existing manuscript package

The auditable source currently compiled by `paper/main/main.tex` is organized as
introduction; constructed-treatment literature; data/harmonization; estimand and
inference; broad-family support/results; architecture comparisons; timing and
remaining interpretations; conclusion.  It compiles the eight section files
through `08_competing_interpretations.tex`; `09_implications.tex` and
`10_conclusion.tex` are stale, unreferenced source files.

The current major-revision PDFs have hashes:

| Artifact | SHA-256 |
|---|---|
| Main manuscript | `39315398c0bea4f87e055af537080627a976faa5cddc53963f4c5a4df26ba067` |
| Online appendix | `f5aed632c4f09b35c745371e1e4a8cc04a5a69e458927b97717b753172ff970a` |
| Major-comment response | `184541a944ea4a9ea5c481e62ffdd7a82027a602c3cad23b77ba47c60077f723` |
| Revision diagnosis | `2a565350c63c1d0501f66ad4cda8f293ddb22f588ef7984760a394fd5c77dae9` |

These are comparison artifacts, not deliverables satisfying the new prompt.

## Status vocabulary

- `complete_existing`: a result or audit with machine-readable evidence exists
  and substantially answers the item, although it still needs to be carried into
  the new source of truth.
- `partial_reaudit`: useful code/results exist, but support, calendar, estimand,
  covariance, provenance, or requested detail differs and must be rerun or
  audited.
- `missing`: no responsive executed result or implementation was located.
- `blocked_method`: the requested exercise needs an unavailable input or a method
  decision; it must not be fabricated.
- `editorial_pending`: principally a writing/packaging task for the new draft.
- `contradicts_prompt`: the present paper contains material the new prompt
  explicitly requires removing or demoting.
- `pending_new_revision`: a formerly completed deliverable has to be regenerated
  after the new analyses.

## Important non-substitutions

- The existing `PLACEBO_BENCHMARK.csv` ranks wage, education, cognition,
  teleworkability, and STEM as *alternative treatments*.  It is not the requested
  exercise that conditions the beta contrast on those characteristics.
- The mobility household bootstrap is not a sampling-oriented bootstrap of the
  core occupation-by-age-by-month stock estimator.
- The current time-HAC sensitivity is not, by itself, a completed audit of the
  new prompt's inclusion--exclusion formula and calendar-lag convention.
- The existing corrected-calendar coefficient keeps the historical treatment
  definition.  It is not a fully recomputed corrected pipeline.
- The BCC bridge reproduces a public grouping inside CPS.  It is not an ADP
  replication, and the SOC2-conditioned BCC rows requested now have not been
  run.
- The stable-tail result is currently in the main paper, directly contrary to
  the new prompt.

## Highest-risk methodological decisions

1. The exact R2 version must be reconciled before a final comment-by-comment
   completion claim.
2. Household/sample-unit resampling cannot be described as fully design-based
   unless the available longitudinal identifiers and missing public PSU/stratum
   variables justify that target.  A transparent sampling-oriented
   approximation may still be feasible.
3. Rambachan--Roth-style sensitivity is conditional on a valid joint event-time
   vector, covariance matrix, and explicit linear post functional.  The present
   restricted dynamic output is not sufficient.
4. A stock--flow calibration must account for entry, exit, occupation switching,
   aging, and denominator changes.  If those objects cannot be aligned, a
   principled nonimplementation is more faithful than an implied stock response.
5. Population-control counterfactual weights, true occupation-miscoding rates,
   and age-specific crosswalk probabilities remain unavailable and must not be
   invented.


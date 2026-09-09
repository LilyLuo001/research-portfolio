# Gate 4 age, cohort, and enrollment results validation

Status: **authoritative SCC run complete; public recomputation passed;
manuscript integration pending**.

This note records the D05--D07 execution specified before these extensions were
estimated. They are post-outcome, referee-led descriptive analyses and do not
make any older group an untreated counterfactual.

## Provenance and validation

- SCC job `7500522` completed at repository commit
  `baeda97a9da64b46ff9dba68344e5e12a21a3959`.
- The run produced 20 models and 14 covariance-preserving paired comparisons,
  with zero failures and 9,999 common occupation and family draws.
- The protected canonical cells reproduce to a maximum relative gap of
  `3.15e-15`; the fixed-age population identity reproduces to `5.32e-16`.
- The current runner and specification hashes exactly match the receipt.
- The public validator recomputed every model and paired standard error from
  the stored influence vectors, checked all output hashes and supports, and
  returned `PASS_RECOMPUTED_COHORT_ENROLLMENT_VALIDATION`.
- No protected row or identifier was published, and national population rows
  received no occupational exposure assignment.

## D05: older-age bands and fixed-age composition

On the common 467-occupation support, pooled Q5-by-post coefficients are
`-0.1205` against ages 26--30, `-0.1598` against ages 31--40, `-0.1392`
against ages 41--50, and `-0.0971` against ages 51--65, compared with
`-0.1321` against ages 26--65. The occupation-clustered interval for the
51--65 comparison contains zero; those for the first three bands exclude zero.

The paired occupation-clustered differences from the 26--65 comparator contain
zero for the 26--30, 31--40, and 41--50 bands. The 51--65 difference is
`0.0350` with interval `[0.0036, 0.0663]`. These are comparator sensitivities,
not treatment effects for older workers.

Fixing the exact-age composition of the 26--65 denominator changes the pooled
coefficient by only `0.0008`, with paired interval `[-0.0011, 0.0027]`, and the
family-month coefficient by `-0.0001`, with interval `[-0.0026, 0.0023]`.
The design therefore does not detect a change from this standardization; it
does not establish equivalence.

## D06: enrollment restrictions

The code audit treats only `SCHLCOLL=5` as nonenrolled and never classifies
invalid or not-in-universe values as nonenrolled. A common-observable older
comparison ends at age 54 because the valid enrollment universe has no weight
at ages 55--65.

Restricting young workers to the nonenrolled changes the pooled coefficient
from `-0.1321` to `-0.1239` against all ages 26--65. On the common enrollment
universe, the analogous pooled change is from `-0.1407` to `-0.1354`. Both
paired occupation-clustered intervals contain zero. The corresponding
family-month estimates also have paired intervals containing zero. These are
selected-population descriptions because enrollment may respond to labor-market
conditions.

## D07: composition accounting

The national ages-22--25 profile is reported separately from employed-young
profiles by occupation quintile. National records are never assigned an
occupation or exposure quintile.

Between the aggregated pre and post periods, the national enrollment share
among valid responses changes from `0.2336` to `0.2211`, the BA-or-higher share
from `0.2941` to `0.3121`, the employment rate from `0.7110` to `0.7247`, and
the mean age by only `-0.0085` years. Among employed young workers, the
enrollment share changes by `-0.0010` in Q1 and `-0.0180` in Q5; the BA-or-
higher share rises by `0.0179` in Q1 and `0.0381` in Q5. These patterns document
composition and selection; they do not identify a cohort correction.

## Remaining boundary

D05--D07 remain `RUN_UNVALIDATED` in the master ledger because their upstream
T02/D06 dependencies and final manuscript presentation have not yet been
closed together. The computations and public numerical checks are complete;
no rerun is currently indicated.

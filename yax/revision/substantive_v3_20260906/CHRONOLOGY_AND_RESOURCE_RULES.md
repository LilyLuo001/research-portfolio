# V3 chronology and resource rules

Recorded before the first new V3 empirical run: 2026-09-06  
Review role: execution-agent self-review, not preregistration and not
independent scientific review

## Chronology

YAX outcomes were opened after the v1.1 design freeze, and multiple R3
post-outcome estimates already exist. V3 is a referee-led, outcome-informed
revision. It is not a preregistration and must not be described as one. The
referees' criticism, the prior assistant failure audit, and observed R3 results
motivate the new checks. This chronology is part of the interpretation of
every new estimate.

The V3 order is nevertheless fixed for error control and reproducibility:
canonical reconstruction and numerical existence precede support and
decomposition; those precede calibrated inference; ancillary outcomes and
external extensions follow their feasibility gates; writing follows the
result and claim ledgers.

## Accuracy rules

1. The R3 values approximately -0.132109, -0.0217, 468 occupations, 71
   construction months, and 113 static months are checkpoints, not targets to
   recover by changing code.
2. The canonical contract fixes inputs, support, labels, scale, age groups,
   calendar, objective, nuisance space, contrast, solver, and uncertainty.
   Every alternative receives a new content-derived ID.
3. Numerical existence, separation, rank, gradients, and a same-objective
   second solver are resolved before a nonconvergent central model is used.
   Penalties, pseudocounts, clipping changes, or selective deletions define a
   different target and may not be hidden as solver fixes.
4. Through-2024 and full-window results remain visible. Neither is selected as
   primary because of significance. December 2022 and October 2025 follow the
   declared calendar rules.
5. Independent compute branches may continue after another branch fails. A
   failed branch and its log remain in the DAG; descendants cannot use it as a
   cache hit.
6. No manuscript number may bypass the result and claim ledgers. Changed
   upstream artifacts invalidate dependent covariance, figures, prose, and
   responses.
7. Existing R3 outputs are reference evidence, not V3 reruns. An aggregate
   rebuild is never relabeled as a licensed-microdata re-estimation.

## Compute and storage rules

- New SCC computation uses a fresh worktree beneath the verified
  `/project/econdept/.../yax-substantive-revision-20260905` tier.
- Restricted microdata remain read-only at their authorized locations and are
  never copied into Git or a public package.
- The stale dirty SCC checkout is not authoritative. Pre-existing sessions,
  worktrees, and jobs are not killed, cancelled, or repurposed.
- Runs begin with a pilot/resource estimate where computationally material,
  use restartable outputs when possible, and record every failed bootstrap or
  simulation replicate.
- Credentials, personal absolute paths, licensed data, and direct identifiers
  are excluded from versioned output.

These rules constrain execution but cannot erase the post-outcome status of
the revision.

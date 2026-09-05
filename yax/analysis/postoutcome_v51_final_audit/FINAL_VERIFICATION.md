# YAX V5.1 final audit verification

Date: 2026-09-05  
Branch: `task/yax-v51-final-influence-audit-20260905`  
Final audited content commit: `e39cbb5eab26fa9362aa8ffd659ac3cd16a8576a`

## Outcome-dependent boundary

PASS.

- The only new outcome-dependent computations are the primary beta-by-Webb LOCO loop and the frozen joint-model G LOCO loop.
- No new labor-outcome specification was estimated.
- LOCO refits only delete one occupation while preserving the exact previously defined treatment and model.
- No leave-one-measure-out labor-outcome model was executed.
- No direct A/E labor-outcome model was estimated.
- No new bootstrap multipliers were generated.
- Full estimates were reproduced exactly before either deletion loop.

## A/E presentation

PASS (`AE-R1`, bounded by `G-PARTIAL`). The scale-correct algebra gives +0.02493 per weighted SD for the AIOE centroid and -0.06148 for the Eloundou centroid. The transformed fitted contribution matches the F/G predictor to maximum absolute error `2.78e-17`. The A-minus-E contrast inherits G's existing wild-score interval and p-value; individual A/E level intervals are explicitly labeled normal-covariance intervals. The manuscript calls this a reparameterization of the same exploratory model, not corroboration.

## Fixed-treatment occupation influence

PASS.

- Primary: `LOCO-B2`; 468 deletions; full -0.131074; range [-0.142384, -0.110553]; maximum absolute movement 0.020521; zero sign reversals.
- G: `LOCO-G1`; 444 deletions; full +0.030894; range [+0.025128, +0.035993]; maximum absolute movement 0.005766; 0/444 estimates at or below zero.

All CSV hashes match the machine-readable result receipt. Treatment reconstruction is false in every row.

## Power code/history audit

PASS (`POWER-C3`). The prospective code retained an ordered historical residual path and one common sign across months within each occupation. It did not treat all occupation-month residuals as temporally independent, so the proposed serial-dependence-omission explanation is not supported. The heuristic `m=42` calculations imply rho 0.3004 for the 3.649 headline ratio and rho 0.2203 for the 3.167 paired ratio; these are explicitly descriptive, not causal decompositions.

## Manuscript and final framing

PASS (`SUBMIT-S1`). The title is unchanged. The confirmatory headline is retained with a compact `LOCO-B2` disclosure. Section 6.2 leads with A/E as the exact basis change, distinguishes normal and wild-score inference, and reports `G-PARTIAL` beside `LOCO-G1`. The abstract contains only one bounded A/E clause. The empirical search remains closed.

## Reproducibility and tests

- Pre-execution plan/code commit: `e371c465b95d8e496c0bc3ee439451c1dfa06c31`.
- Frozen design tag: `22fbf7924809b7a535e31ae0ab68f5b113ce8078`.
- Frozen confirmatory-results tag: `b16109482c3bf5ca176f6f08976e120b04769945`.
- SCC targeted suite: 8 passed in 1.05 seconds.
- SCC full suite: 880 passed, 3 skipped, 13 warnings in 16.92 seconds.
- Remote target: `origin/task/yax-v51-final-influence-audit-20260905`.
- Remote verification: pending retry after a transient GitHub connectivity failure; no content or test failure is involved.

Final artifact hashes and input lineage are recorded in `YAX_V51_FINAL_AUDIT_RECEIPT.json`.

## Stop rule

STOP. No further empirical analysis is authorized. Remaining actions are final citation/version verification, prose compression, journal formatting, figures/tables, seminar slides, cover letter, and submission.

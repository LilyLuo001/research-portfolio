# Gate 2 support/accounting provisional-run review

Date: 2026-09-07

Scope: independent review of the model-free support and accounting module and
the non-citable provisional execution from commit `18facff`. This review does
not validate the replacement output, sampling inference, or manuscript claims.

## Arithmetic checks

No P1 scientific or arithmetic failure was found. The reviewer independently
checked the 468-occupation support, the complete 22-by-5 matrix, the four
direct-tail families, the five-node incidence rank, the tail log-stock
identity, the midpoint level closures, and the log Shapley closure. A separate
1,000-draw randomized stress test of the three-factor Shapley implementation
had maximum closure error `4.44e-16`.

## Findings and disposition

1. **P2, fixed before replacement execution:** the graph field
   `full_contrast_rank` overstated what an aggregate incidence graph proves. It
   is now `graph_incidence_full_rank`; the receipt and graph interpretation say
   explicitly that topology is not a full regression design-matrix,
   information, or finite-estimability certificate. Regression certification
   remains in the separate Gate 1 A1 evidence.
2. **P2, fixed before replacement execution:** the provisional receipt lacked
   artifact-level result IDs. Each replacement artifact ID now binds the
   signed specification ID, logical filename, and artifact SHA-256. The
   provisional run remains unchanged and ineligible for citation.
3. **P3, fixed before replacement execution:** the runner now requires the
   exact January 2017--July 2026 calendar with October 2025 absent and December
   2022 present. A wrong-missing-month mutation is rejected.
4. **P3, fixed before replacement execution:** an asymmetric boundary-mass test
   independently enumerates all six Shapley orders, checks all eight hybrid
   levels, and reconciles the log endpoint with the aggregate tail identity.
5. **P3, fixed before replacement execution:** pinned receipt hashes are now
   supplemented by fail-closed schema/status checks, unique numerical model
   IDs, and the required per-model A1 certification status.
6. **P3, fixed before replacement execution:** the direct-tail occupation share
   is now named `within_family_quintile_preperiod_stock_share`; a distinct
   across-Q1/Q5 family-tail share is also emitted. Neither is described as
   statistical influence.
7. The occupation-stock reproduction tolerance was tightened to the Gate 1
   standard (`rtol=1e-12`, `atol=1e-6`). On the authenticated aggregate, the
   largest absolute discrepancy is `2.98e-08` and the largest relative
   discrepancy is `4.10e-16`.

## Scope ruling

The replacement package may advance the model-free portions of S01--S02 and
the point accounting for D01/D03/D04. It must not mark those requirements
`VERIFIED` until the required inference, presentation, and manuscript/appendix
integration checks have also passed. D02 and the remaining inferential
requirements are not completed by this module.

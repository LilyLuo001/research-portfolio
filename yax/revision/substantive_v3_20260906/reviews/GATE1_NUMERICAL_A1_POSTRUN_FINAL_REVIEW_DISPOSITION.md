# Disposition of the final independent Gate 1 A1 post-run review

Date: 2026-09-07

Independent review: `GATE1_NUMERICAL_A1_POSTRUN_FINAL_REVIEW.md`

## Bottom line

The review found no P1 defect and independently upheld the numerical result:
all 11 frozen models meet the unchanged A1 thresholds. Its one P2 and four P3
findings concern evidence labeling, ledger integrity, and disclosure. They do
not change an estimator, scientific input, treatment, support rule, objective,
target, tolerance, coefficient, or release conclusion.

## Finding dispositions

| finding | disposition | corrective evidence |
|---|---|---|
| P2-1: two parent-reuse checks were hardcoded `true` | **Accepted and corrected prospectively; historical source preserved** | Future parent-reuse normalization emits an explicit skip marker and a narrower `shared_cells_target_authorization_*` prefix. `TRANSFER_VALIDATION_INTERPRETATION_CORRECTION.json` supplies the truthful interpretation of the immutable historical output. Regression tests distinguish fresh and parent-reuse behavior. |
| P3-1: five stale working-ledger hashes | **Accepted and corrected** | The stale entries are updated. `test_requirements_evidence_hashes.py` now recomputes every declared evidence hash and fails on missing, escaping, symlinked, or mismatched evidence. |
| P3-2: full-suite count understated by three | **Accepted and corrected** | The guard correction document now records the commit-specific `1,114 passed` count and identifies the three evidence tests omitted from the earlier prose. |
| P3-3: focal estimate source undocumented | **Accepted and disclosed additively** | `FOCAL_TARGET_SOURCE_AUDIT.json` records that all 11 displayed focal estimates equal the independent reference-path values, compares them with the primary path, and verifies a maximum difference of `4.632128597359397e-09` against the unchanged `1e-07` tolerance. The signed pre-outcome specification is not rewritten. |
| P3-4: guard reader changed post-outcome and outside frozen byte binding | **Accepted and disclosed** | The schema-correction record now labels the change explicitly as post-outcome, records before/after guard hashes, and states that the numerical producer and immutable result bytes did not change. The current guard hash is pinned in the working ledger and mechanically checked. |

## Preserved evidence and non-changes

The successful SCC job 7482383 artifacts, their transfer validation, and their
dependency release remain byte-for-byte unchanged. The failed SCC job 7482111
also remains unchanged and blocked. No protected cell file was opened or added
to the repository. No numerical rerun was needed because the independent
review recomputed the load-bearing quantities and found no numerical defect.

The prospective normalizer correction is itself post-outcome code. Its
SHA-256 changed from
`fc05ff81e8959255d5c438ff9d0f554b72c7d40ce80f5882b335e65f0e603763`
at reviewed commit `d98371d5` to
`acb32a66c9e2e81167cda39cb302b191e1e4a4bcb9dea91ed1298cd4d01a7f9f`.
It cannot retroactively alter the preserved transfer output; its role is to
prevent the same evidence-labeling defect in future transfers.

## Requirement interpretation

This closes the requested independent artifact review of the Gate 1 A1
numerical certificate. It does not by itself validate manuscript presentation
or satisfy downstream empirical requirements that require separate analysis
and integration. Those remain governed by the target-level dependency map and
working requirements ledger.

## Verification

- Targeted closure suite: 117 passed.
- Full repository suite after the corrections: 1,116 passed, 3 skipped, 26
  subtests passed.
- Every evidence path/hash pair declared in `requirements_status.json`
  recomputes successfully under the new repository-wide hash test.

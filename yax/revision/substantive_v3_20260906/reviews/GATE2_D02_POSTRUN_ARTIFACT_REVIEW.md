# Gate 2 D02 post-run artifact review

Date: 2026-09-07

Status addendum: this initial same-team review was subsequently challenged by
`GATE2_D02_CLAUDE_FINAL_REVIEW.md`. That review found one P2 evidence-contract
defect in the platform-specific numeric-difference field of the retained
validation report. The defect and four associated P3 hardening items were
repaired locally without changing the authoritative run bytes or rerunning
SCC. The final disposition is recorded in
`GATE2_D02_CLAUDE_REVIEW_DISPOSITION.md`; the historical review below is
retained as the pre-challenge record.

Scope: read-only same-team review of the authoritative outcome-free D02 run,
its validator, and its tests. No SCC execution, protected outcome, aggregate
cell, or row-level record was opened by the reviewer.

## Verdict

This initial review found no P1 or P2. It recorded three P3
provenance/validator hardening findings; none
changes the identification result and none warrants an SCC rerun.

The reviewer independently recomputed:

- specification ID and SHA-256;
- runner, audit, and receipt SHA-256 values;
- result and receipt IDs;
- all five authenticated input hashes;
- 468 unique sorted occupations and the exact 113-month calendar;
- the 52,884 row pivots and row-key hash;
- exact saturation of all five exposure-by-post columns; and
- rank five for the additive occupation-plus-month companion.

The smallest companion singular value is 4.731888 and exceeds its rank cutoff
by approximately 1.91e12. Cross-platform singular-value differences reached
only 1.421e-14, approximately 3.0e-15 relative to the smallest singular value.
The retained run contains exactly two regular JSON files and no private paths,
secrets, links, protected data, or coefficients. The focused suite passed 28
tests before the P3 hardening.

## P3 findings and disposition

1. The validator originally ignored extra subdirectories when constructing the
   file inventory. Accepted and corrected: it now checks all directory entries
   and requires exactly the two declared regular, non-symlink files. An
   extra-directory regression test was added.
2. The producer receipt omits Git commit and tree-clean fields. Accepted as a
   provenance limitation. Exact specification, runner, and input hashes bind
   the scientific bytes; the execution worktree was externally verified at
   pushed commit 9c197418122623cd86f0a4990ffa4013ba93b656. The corresponding
   transfer bundle had SHA-256
   0d4163362d66b74a4b40a1c8912b9e09850aad5bdeecb4ced97172d613b94e73.
   This is recorded additively rather than altering the immutable run.
3. The validator originally did not check run_id or executed_at_utc
   semantically. Accepted and corrected: the run ID must match the leaf and the
   frozen regex, and the timestamp must be timezone-aware UTC. Rebound metadata
   tamper tests were added.

After these corrections, 33 focused tests pass. The authoritative run bytes are
unchanged.

## Status ruling

D02 may advance to RUN_UNVALIDATED, not VERIFIED. The outcome-bearing additive
companion has not been specified or estimated, and manuscript and appendix
integration remain outstanding.

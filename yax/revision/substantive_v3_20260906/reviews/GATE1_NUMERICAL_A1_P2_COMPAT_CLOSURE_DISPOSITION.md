# Gate 1 A1 P2/compatibility closure-review disposition

The independent review is retained at
`GATE1_NUMERICAL_A1_P2_COMPAT_CLOSURE_REVIEW.md` with SHA-256
`a5531e946f79b6865032c13e65866a5c02d7e0a59031f7876fc989d29d5156ab`.
It reviewed the exact delta
`efb714894c16ccd4e6dec645d6d6f6f5703d17cb..576133d86e9305726d0ceb78413fec2ac795cdb0`
and found no P1 or P2 issue. Its three P3 observations are disposed as follows.

## P3-1 — retain job 7482111 evidence

Adopted. The failed compatibility run's exact `EXECUTION_RECEIPT.json` and
`MODEL_AUDIT.json`, plus a fresh byte-pinned scheduler-accounting export, are
retained under `runs/gate1_numerical_a1_compat_blocked_7482111/`. The failed
run remains immutable evidence: it certifies no model and is not substituted
for the replacement run.

## P3-2 — add the failed A1 specification to the denylist

Not applied after execution. Adding the ID would change the target-map bytes
after the pre-execution authorization and would make the current map differ
from the exact map committed in authorization commit
`b7c9e1c2d165c88d185cf85559f83b6329204ceb`. The positive specification-ID,
specification-hash, and runner-hash pins already reject job 7482111's artifacts.
The failed ID and hashes remain explicitly recorded in the compatibility
record and retained receipt. This is a deliberate preservation of the
pre-outcome map, not a waiver of any certification check.

## P3-3 — fail-closed branch coverage

Adopted for the dependency-map branches. A table-driven regression now checks
unknown requirements, orphaned requirements, absent/empty contracts, and five
malformed contract-value shapes. The focused suite passes 29 tests and 9
subtests. The NumPy compatibility path was separately executed on SCC under
the exact pinned NumPy 2.5.1 runtime, where `np.row_stack` is absent; 244 focused
tests and 17 subtests passed before the authorized replacement run.

The review's suggested process improvement therefore has direct pinned-runtime
evidence without changing the scientific specification.

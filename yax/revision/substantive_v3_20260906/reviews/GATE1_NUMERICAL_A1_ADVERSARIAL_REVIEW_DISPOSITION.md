# Disposition of the A1 adversarial final review

Date: 2026-09-07

Reviewed report:
`reviews/GATE1_NUMERICAL_A1_ADVERSARIAL_FINAL_REVIEW.md` (SHA-256
`5fc64c812ebc4082dbe2c3e095205677b5f18b615d9b8db5ff9e32c0e062bb3a`).

The external read-only review found no P1 issue and one P2 issue. The P2 is
accepted: `downstream_requirement_model_contract` was present in the frozen
map, but the guard did not mechanically enforce that a consumer naming a
requirement carried the requirement's full declared model set, and it did not
emit a requirement-keyed numerical release status.

## Correction

`scripts/dependency_guard.py` now:

- validates a nonempty, unique, known-model requirement contract;
- rejects unknown requirement IDs and consumers missing any model required by
  the requirement they name;
- rejects contract requirements that have no mapped consumer;
- makes both consumer and requirement release conditional on the authenticated
  non-model prerequisites;
- emits `downstream_requirement_releases`, including required, certified or
  blocking model evidence and the mapped consumer IDs.

`tests/test_dependency_guard.py` now proves that a consumer cannot claim a
requirement with a shortened model set and that one blocked constituent model
blocks the requirement while an unrelated certified consumer remains released.
The existing post-outcome map-tampering test now weakens both the requirement
contract and its consumer so it continues to reach, and be rejected by, the
separate immutable pre-outcome Git binding.

The focused guard suite passed 27 tests. The full repository suite passed
1,109 tests, skipped 3, and passed 17 subtests. No numerical runner,
`ANALYSIS_SPEC_A1.json`, scientific target, target-map byte, threshold, input,
or retained historical artifact changed in this correction.

## Effect on the first SCC A1 attempt

The finding concerns downstream release computation, not the numerical
producer. The frozen map already gives every named requirement its complete
declared model set, so the issue cannot change any model estimate or model
certificate. The first A1 attempt was authorized before the review commit in a
separate clean SCC worktree whose implementation tree was byte-identical to the
reviewed `cb9310c5` tree. Its authorization commit has that implementation
commit as its parent and changes only the authorization file. Advancing the
GitHub branch with the review did not retroactively alter that local
authorization chain.

That attempt subsequently completed with all 11 models blocked by the separate
NumPy `row_stack` compatibility failure recorded in
`numerical_existence/NUMERICAL_AMENDMENT_A1_COMPATIBILITY_01.md`. It produced no
certified coefficient and no downstream release decision.

The corrected guard, rather than the reviewed pre-correction guard, must be
used for every post-run target and downstream-requirement release decision.

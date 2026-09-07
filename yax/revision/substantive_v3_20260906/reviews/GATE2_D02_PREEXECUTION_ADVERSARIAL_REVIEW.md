# Gate 2 D02 pre-execution adversarial review

Date: 2026-09-07

Scope: outcome-free D02 identification specification, runner, and focused tests.
The reviewer did not edit the repository, run SCC, open protected outcomes, or
inspect row-level data.

## Initial verdict

No P1, one P2, and no separate P3 finding.

The substantive geometry was correct. With one unrestricted
occupation-by-calendar-month pivot for every one of the 52,884 rows, the
saturated nuisance spans the row space and absorbs all five exposure-by-post
columns. The distinct additive occupation-plus-month companion retained rank
five. The production proof did not allocate a 52,884 squared matrix.

The P2 was a fail-closed contract defect. Six binding fields could be altered,
the specification ID recomputed, and the modified specification accepted even
though the runner retained hard-coded behavior:

1. `calendar.expected_estimation_month_count`;
2. `membership.expected_panel_row_count`;
3. `design.post_definition`;
4. `design.q1_normalization`;
5. `proof_contract.fixture_materialization_limit`; and
6. `outputs.files`.

The current bytes were mutually consistent, so the finding did not change the
identification result. It did prevent the artifact from being commit-ready at
the project's fail-closed standard.

## Repair re-review

The runner now validates the six fields above as well as the output schemas,
unexecuted-at-freeze marker, and atomic non-overwrite policy. Eleven semantic
mutation cases exercise those bindings.

The separate-agent same-team re-review found no remaining P1, P2, or P3 issue:

- all six formerly accepted mutations now fail closed;
- focused suite: 24 passed;
- static compilation passed;
- temporary end-to-end output hash, result ID, and receipt ID recomputed;
- the 52,884-row absorption proof and companion rank five were unchanged;
- no dense production matrix or protected-data input surface was introduced.

Frozen identifiers after repair:

- specification ID:
  `yaxgate2d02spec_v1_2357904781f082216bc398baadef1e2005bc0b1d4c40d0b7ed1c63250e09e0c3`;
- runner SHA-256:
  `2e1e0c712d04b16e2d6f6c5661645c05c1814f14ae2cd498a08800420db6bc0d`.

## Readiness

Safe to commit as a pre-result artifact. D02 is not yet complete: an
authoritative execution, post-run artifact validation, ledger advancement to
`RUN_UNVALIDATED`, and manuscript/appendix presentation remain downstream.

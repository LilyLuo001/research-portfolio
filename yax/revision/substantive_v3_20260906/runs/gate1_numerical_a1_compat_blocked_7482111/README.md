# Gate 1 A1 compatibility-blocked run — job 7482111

This directory preserves the exact aggregate receipt and model registry from
the first A1 execution attempt, plus a fresh sanitized scheduler-accounting
export. It closes an evidence-retention gap identified by the independent
compatibility review.

The run is permanently classified as blocked. Pinned NumPy 2.5 lacked the
removed `np.row_stack` alias, so the common problem-binding path stopped before
solver certification. All 11 model rows are
`BLOCKED_UNEXPECTED_NUMERICAL_FAILURE_NO_SUBSTITUTION`; no coefficient or
target is certified.

- SCC job: 7482111
- Scheduler: `failed = 0`, `exit_status = 2`, wallclock 605 seconds,
  maximum virtual memory 1.932 GB
- `numerical/EXECUTION_RECEIPT.json` SHA-256:
  `d6bd6b5d743c9510c124caeacfad5f3505bafc8cc57af972c05e75420bc7f59e`
- `numerical/MODEL_AUDIT.json` SHA-256:
  `18869185dfecad9f546bb51609e3bbf51d8c85fdb3fef4f6fd6c218032c4fc74`
- `scheduler/numerical.json` SHA-256:
  `cc6cc450621b51494b29965958753700d41244b0ca546a1ea1fa22b88479e120`

The later successful replacement run does not overwrite, reinterpret, or
substitute this evidence.

# Gate 2 dynamic-core execution 7489898

- Frozen implementation commit: `6c65820f9ba525ec31f97ead0d4db5fc6d60d668`
- SCC job: `7489898`
- Queue/host: `econ@scc-gr4.scc.bu.edu`
- Scheduler result: `failed=0`, `exit_status=0`
- Wall time: 223 seconds
- Maximum virtual memory: 3.727 GB
- Standard error output: empty
- Result ID:
  `yaxresult_v1_b039944581f0da60fb7e8368bff687858b740a7e638c190a8c934369fc10defe`
- Imported immutable artifact directory:
  `runs/gate2_dynamic_core_authoritative_20260908/`
- Independent post-run validation:
  `gate2/dynamic/evidence/DYNAMIC_CORE_POSTRUN_VALIDATION.json`

The run freshly certified the pooled, family-month, dynamic-unconditioned, and
dynamic-family-month models at the unchanged A1 numerical thresholds. It
published the predeclared Y01--Y05 public coefficient, covariance,
occupation-influence, common-draw inference, nesting/projection, and
reparameterization artifacts. It did not publish protected aggregate cells,
cell stocks, fitted designs, fitted probabilities, or private absolute paths.

The repository-side validator independently reproduced all 18 reconciliation
targets and their full paired covariance, all event-study pointwise and
simultaneous intervals, all 16 frozen pretrend tests, and all leave-one-quarter,
level, drift, and seasonal diagnostics. The largest absolute recomputation
difference was `1.19e-12`.

Y08 onset-grid and T05 endpoint estimates were not run or claimed by this
execution. Their existing numerical prerequisites do not substitute for the
additional requested result objects.

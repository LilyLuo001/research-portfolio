# Gate 2 support-inference successful execution 7489785

This is the execution record for the authoritative Gate 2 support-inference
run covering requirements S03, S04, S06, and S07. It does not claim that the
results have yet been integrated into or validated in the manuscript.

- SGE job: `7489785`
- Run ID: `gate2_support_inference_sge_7489785`
- Implementation commit: `6cff175da72cb938e947c8715bc8e67d73bbe075`
- Authorization commit: `62c3da6c5ea950a39c0fa80b04e0450594318d0b`
- SCC host/queue: `scc-gr4.scc.bu.edu` / `econ`
- Start/end: `2026-09-08 00:41:46` / `2026-09-08 00:45:24` (SCC time)
- Accounting: `failed=0`, application `exit_status=0`, wall clock 218 seconds,
  maximum virtual memory 3.207 GB
- SCC output: authenticated project-tier result leaf for run ID
  `gate2_support_inference_sge_7489785`; the private absolute compute path is
  intentionally not published.
- Retained repository copy:
  `runs/gate2_support_inference_authoritative_20260908/`
- Result ID:
  `yaxresult_v1_b53fefb7dd5185f8a7d6d3e7cf45df938d6e5205bf75eacabc9e8ee26bfc496a`
- Receipt ID:
  `yaxreceipt_v1_7de4623cf604275dcfb753c763e0bf2ac2b3f967f6cba586136b636f1e5e7cd2`

The run published 40 declared result artifacts plus the result manifest and
execution receipt. All five required models passed the unchanged A1 numerical
certificate. All 26 producer validation checks passed. The 89-dimensional
supported-edge joint test remained deliberately blocked because the functionals
and their covariance have structural rank 50; no invalid chi-square statistic
or p-value was emitted for that singular object.

The repository-side validator independently checked the exact 42-file
inventory, every declared byte count, SHA-256, and content-derived identifier,
then recomputed the paired profile identity, covariance-based standard errors,
pointwise and simultaneous confidence intervals, simultaneous critical values,
and the three four-degree-of-freedom profile joint tests from the retained
public artifacts. Its report is
`evidence/POSTRUN_VALIDATION_REPORT.json`.

The authorization at commit `62c3da6` was single-use. It is preserved in Git
history and removed from the subsequent implementation state.

# W06 current-contract carry-forward validation

Status: **PASS for the retained computation; delivery remains unvalidated**.

The public carry-forward validator in
`gate3/architecture/run_architecture_reconciliation.py::validate_w06` was run
against the retained 113-month architecture output at
`yax/revision/substantive_r3_20260905/architecture/results`. All six focused
architecture tests passed on 2026-09-08. No protected calibration or outcome
file was opened and no model was refit.

The validator authenticated all 28 hashes in the retained execution receipt
(status `PASS_ARCHITECTURE_AUDIT`, source commit
`797447a411e85f9e8412a3cfbec75cf43f96b4aa`). It then independently required:

- five lambda values and 2,340 occupation-membership rows;
- 30 paired lambda comparisons using common multiplier draws;
- exact lambda-0.5 membership and coefficient identity with literal beta;
- a maximum identity gap below the signed `1e-10` tolerance;
- six raw/standardized D/S result rows, 18 covariance rows, and all 9,999
  centered draws for all six primitive coefficient representations;
- three scale-reconciled illustrative contrasts using common draws; and
- an empty model-failure registry.

The active appendix states the D and S raw-share units and weighted-standard-
deviation presentation, exposes the joint-model covariance and common-change
interpretation, and labels `D+0.5S` as beta. The active main text reports the
five-point lambda sensitivity and its changing memberships. These are
post-outcome exploratory architecture diagnostics, not evidence of adoption
or a causal decomposition.

W06 remains `RUN_UNVALIDATED` because its upstream T02 requirement and the
compiled-document review are not yet verified, and the final V3 sanitized
delivery has not yet copied and manifest-bound the retained result files.

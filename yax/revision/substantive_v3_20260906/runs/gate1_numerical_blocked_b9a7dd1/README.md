# Gate 1 numerical audit: blocked frozen run

This directory preserves the sanitized evidence from the fresh, authorized
Gate 1 execution at Git commit `b9a7dd1c8703397f1a6686ff9b1a55d4bb67cbde`.
It is a blocked-run record, not a validated-results package.

## Outcome

- The restricted-data cell builder completed successfully. It authenticated a
  53,352-row, 468-occupation, 114-month transport grid. The aggregate cell file
  is restricted and is not present here.
- The exact-target audit passed. The canonical static grid contains 52,884
  occupation-month rows, of which 51,891 have positive total stock.
- The numerical audit ran all 11 predeclared models. Every model was classified
  `BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK`, so the overall numerical
  receipt is `BLOCKED_ONE_OR_MORE_CORE_TARGETS_NOT_ESTABLISHED`.
- For most models, the trust-region solver passed the frozen KKT/full-Hessian
  checks but L-BFGS-B did not. For the unconditioned quintile-by-month seasonal
  model, neither solver passed the frozen original-coordinate KKT rule. Some
  dynamic L-BFGS-B fits also exceeded the target-correction tolerance.
- The diagnostic coefficient values in the report are not validated estimates
  and must not be quoted as confirmatory findings.

The frozen rule says that a blocked numerical finding is retained and is not
replaced by another estimator. An identical deterministic rerun would not
resolve the failed two-solver certificate. Dependent Gate 2 estimation therefore
remains blocked unless a separately documented scientific adjudication changes
the specification; no such change is made here.

## Publication and transfer checks

The GPFS compatibility amendment worked as designed. Publication used the
declared same-parent POSIX rename fallback under the exclusive sibling lock
after the filesystem reported the kernel no-replace operation as unsupported.
The cell, target, and numerical receipts report no cleanup warnings.

The ordinary PASS-only transfer normalizer rejected this package because the
numerical receipt is blocked. That is the intended fail-closed behavior. A
separate receipt-only diagnostic transfer was then inspected without weakening
the PASS contract. All 27 retained files passed the decoded sensitive-text
scan, and all producer-declared output hashes were recomputed successfully.

## Scope and safety

This record contains only sanitized specifications, fingerprints, receipts,
reports, diagnostics, scheduler accounting, and stdout/stderr. It contains no
restricted microdata, no aggregate estimating cells, no credentials, and no
private compute paths. Existing unrelated scheduler jobs were not cancelled,
killed, or modified.

The authoritative scientific status is in
`numerical/EXECUTION_RECEIPT.json`; the readable summary is
`numerical/CONVERGENCE_EXISTENCE_REPORT.md`.

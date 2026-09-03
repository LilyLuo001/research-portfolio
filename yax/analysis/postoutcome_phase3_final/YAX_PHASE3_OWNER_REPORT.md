# YAX Phase 3 final owner report

**POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.**

## Outcome

Phase 3 is complete and the authorized stopping rule has been executed: **Phase 3 → V5 → STOP**. The selected path is **PATH-P3-C**. No Phase 4 analysis was opened.

The immutable v1.1 design and confirmatory-results tags still peel to their frozen commits. The apparent SHA discrepancies are annotated-tag object hashes versus peeled commit hashes, not ref movement. The V4.1 manuscript baseline was not modified.

## Decisions

- **HB-C:** realized conflict is 53.28%; the hard assortative-rematching mean is 52.32%; the remaining gap is 0.96 percentage points, below the frozen 1.00-point meaningful threshold. The manuscript withdraws the stronger benchmark-based economic-relevance claim.
- **SC-R1:** conflict falls from 94.59% to 19.06% from the lowest to highest quintile of absolute shared-component movement; the persistent difference is similarly sharp.
- **SC-A:** the only new labor-outcome regression gives a shared-F Q5-versus-Q1 coefficient of -0.12854, with a 95% wild-score interval of [-0.21849, -0.03858].
- **Joint sign not supported:** all six point estimates are negative, but one simultaneous one-sided 95% upper bound is positive. The manuscript does not claim familywise simultaneous negativity.

## Verification

The pre-result implementation was committed and pushed before Phase 3 outputs were opened. All numerical outputs were rerun from the beginning after two documented estimand-preserving pandas-access fixes. The final figures use the sealed result files only.

The complete result/V5 package is commit `9bf8f8546a949be1740703167fb89f0301e7279e`. A fresh clone of that remote branch on SCC resolved to the same commit. The full repository suite in that clean checkout passed: **849 passed, 3 skipped**. The local Phase 3 audit passed: **17 passed**.

## Delivered package

- Shorter PATH-P3-C V5 manuscript and supplementary appendix
- hard-benchmark decision record
- shared-component stock and reallocation figures
- manuscript-ready Phase 3 tables
- complete numerical outputs and covariance files
- execution and final reproducibility receipts
- permanent implementation-fix ledger

All Phase 3 claims are labeled post-outcome exploratory. The final paper's central sentence is: **Robustness does not transfer automatically across economic statements.**

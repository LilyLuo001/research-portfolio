# Gate 2 support/accounting execution history

- `gate2_support_accounting_20260907` ran successfully from pre-result commit
  `18facff` on the authenticated Gate 1 aggregate. During post-run contract
  review, the output receipt was found to lack the V3-required artifact-level
  `result_id` fields. No scientific number, support rule, period, or estimator
  was changed. This first run is retained on SCC as an uncommitted provisional
  execution and is not eligible for manuscript citation.
- The additive receipt fix computes each result identifier from the signed
  module `spec_id`, logical artifact filename, and artifact SHA-256. A fresh run
  is required and will use a distinct run ID. Only that replacement may enter
  the repository evidence package.
- Independent provisional-run review also narrowed the graph-rank wording,
  enforced the exact observed-month set, added semantic receipt checks,
  tightened the stock-reproduction tolerance, and expanded boundary-mass
  tests. These are fail-closed contract/test changes; they do not alter the
  scientific treatment, support, periods, or accounting estimand. The final
  replacement specification is
  `yaxgate2sa_v1_6069f368581e958805977c30572cce09f6fabe8f6d0da70505682e68f8cdca5f`.

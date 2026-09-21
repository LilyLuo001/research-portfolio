# P1: bounded same-industry replication

This stage executes the user-approved one-time replication following commit `2514b9a7db014eaa2d7324d189c3b5f6c609c04e`. It does not revive the MF-to-ETF conversion identification or test minute price-discovery speed.

## Completed result

Scientific action: **INCONCLUSIVE_STOP_SPENDING**. The one frozen H2 test retained 4,871 observations, 488 receivers, 12 issuer-events and nine blocks. The same-industry slope is -0.111 percentage points and the direct same-minus-other slope difference is -0.032 percentage points per fixed H1 standard deviation of log coholding; both adjusted intervals include zero. This does not support the proposed positive pattern, but it does not prove absence of an effect. No power or causal claim is made.

The separate referee independently reproduced the primary coefficients, covariance-based intervals and all deletion checks. Job `7671847` completed with exit status zero; no duplicate outcome job or new purchase occurred. The final decision is to archive this test and stop automatic spending/sample expansion for this route.

## Read first

- `DECISION.md`: final scientific result and single next action.
- `INDEPENDENT_REVIEW.md`: separate referee's pre-outcome and final checks.
- `SPECIFICATION.md` and `analysis_config.json`: outcome, direct interaction, weighting, inference and decision rules.
- `TASK_SCOPE.md`: user authorization and finite stop conditions.
- `COORDINATION.md`: explicit model/effort dispatch versus observable telemetry.

## Result-blind support

The corrected, independently recounted metadata design has 4,904 unique issuer-event/receiver rows, 12 issuer-events, nine calendar-support blocks and 490 receivers. Same-industry support has 433 rows and 137 receivers. Both groups exhibit within-event exposure variation across all nine blocks. The within-event design has rank five, including every leave-one-block check; maximum equal-event block weight is one sixth. No event/control trading dates are shared across distinct blocks. Within-block control reuse remains explicitly counted.

These facts pass the study-specific metadata triage conditions; they do not certify independent shocks, statistical power or causality. New response access additionally requires the separate signed, hash-bound pre-outcome review.

## Evidence map

| Evidence | File |
| --- | --- |
| Corrected source and exposure scope | `SOURCE_MANIFEST.json`, `EXPOSURE_LEDGER.json` |
| Actual metadata attrition | `SUPPORT_AND_ATTRITION.csv` |
| Public authoritative gate summary | `SUPPORT_GATE_SUMMARY.json`; full date-coded diagnostics remain on SCC |
| Calendar/control support | `CONTROL_ASSIGNMENT_AND_DEPENDENCE_SUMMARY.json` |
| Metadata construction and superseded first run | `metadata/EXECUTION_RECEIPT.json`, `metadata/build_result_blind_metadata.py` |
| Guarded response construction | `build_replication_response.py` |
| Pooled interaction and covariance | `replication_statistics.py`, `run_frozen_estimation.py` |
| Logical and source boundary tests | `test_replication_statistics.py`, `test_response_boundaries.py` |
| Hash-bound pre-outcome approval and freeze | `PREOUTCOME_REVIEW.json`, `SPEC_FROZEN.json` |
| Two primary estimates and adjusted intervals | `REPLICATION_RESULTS.csv` |
| All prespecified deletion checks | `SENSITIVITY_RESULTS.csv` |
| Response attrition and post-missingness gate | `RESPONSE_BUILD_RECEIPT.json`, `ESTIMATION_RECEIPT.json` |
| One actual run and new authorized exposure | `EXECUTION_RECEIPT.json`, `EXPOSURE_UPDATE.json` |

The public gate summary reflects the authoritative corrected calculations. Full date-coded gate/design diagnostics remain on SCC; their hashes are bound in the approval records without publishing those labels. Where older metadata-subfolder summaries use different labels or calculations, follow the explicit supersession record rather than pooling versions. The initial 11,736-row variant-mixed output is invalid and never authorized outcome access.

## Boundaries

Raw licensed rows, returns and private assignments remain on SCC. Only small aggregate artifacts/code are published. H2 is not globally pristine: prior concentration-stage processing loaded 452 H2 delisting rows without analytic use, and earlier unrelated exposure is not certified absent by this bounded audit. This stage preserves that ledger rather than redefining historical access.

No purchases, WRDS/LSEG connections, authentication changes, automatic year extension or merge are part of this task. The fixed baseline network and event-balanced estimand are not identical to the earlier row-weighted H1 regression, despite common exposure units. A replication association cannot by itself establish ETF mediation or a concentration trend.

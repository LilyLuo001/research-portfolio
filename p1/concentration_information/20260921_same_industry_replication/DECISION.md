# Decision: INCONCLUSIVE_STOP_SPENDING

The separate referee independently reproduced the final arithmetic and frozen decision rule. This is an executed inconclusive test, not a proposed analysis or a claim of zero effect.

## Answer to the research question

The prospectively specified H2 test did not obtain positive support for the same-industry coholding slope or its direct difference from other-industry receivers. Both point estimates are negative and both multiplicity-adjusted intervals include zero. This is not an equivalence test, proof of zero spillovers, or proof that the entire concentration/price-discovery story is false.

| Primary quantity, per one fixed H1 SD of log coholding | Estimate, percentage points | Adjusted interval, percentage points |
| --- | ---: | ---: |
| Same-industry slope | -0.111 | [-0.423, +0.202] |
| Same-industry minus other-industry slope | -0.032 | [-0.365, +0.301] |

These are two-sided 97.5% marginal intervals using the predeclared Bonferroni rule for the two primary quantities, with a calendar-block clustered covariance and `t(8)` reference. The nominal familywise interpretation depends on the covariance approximation and cross-block shock assumptions. Nine calendar-disjoint blocks do not establish those assumptions or certify power. The intervals still permit positive effects; no economic materiality threshold was approved and none is inferred from these results.

The same-industry point slope stays negative in every leave-one-block and leave-one-issuer calculation. The direct interaction changes sign in deletion checks. These checks do not establish precise absence of a signal, but they do not rescue the prespecified positive-support criterion.

## What was actually executed

- Result-blind construction: 4,904 unique receiver-event rows, 12 issuer-events, nine blocks and 490 receivers; 433 same-industry rows before response missingness.
- Separate pre-outcome review passed and bound 11 files before the new response read.
- Response construction retained 4,871 rows, 488 receivers and 430 same-industry rows. Thirty-one candidate rows lacked a valid event response and two lacked at least two valid controls. No replacement observations or alternative controls were added.
- One response/estimation job, `7671847`, completed with scheduler `failed=0`, `exit_status=0`, wall time 24 seconds and maximum virtual memory 1.556 GB. There was no duplicate outcome run.
- No data purchase or Databento query was made. Licensed row-level outputs remain on SCC.
- Independent full-event-dummy weighted least squares and covariance reconstruction reproduced both primary estimates, standard errors and intervals to numerical precision, and all 16 deletion estimates. The retained sample still passes the prespecified operational support gate.

## Why this does not establish identification

The two-session outcome measures unsigned price movement relative to selected non-event controls. It does not measure information absorption speed or accuracy. Historical coholding is not exogenous ETF trading, and industry information, selection and common shocks remain alternative explanations.

This is a prospective test motivated by H1, not an identical-estimator rerun: controls were allocated differently, issuer-events received equal weight and the main model uses a pooled interaction. A common H1 exposure scale supplies comparable units, not an identical estimand. Differences from the prior +0.260-percentage-point strict-subsample estimate cannot be attributed solely to calendar time or changing market ecology.

Calendar nonreuse addresses the previously measured shared-window problem. Repeated receivers and issuers and unmeasured common shocks can still create dependence. Accordingly, neither the row count nor passing the study-specific support gate implies sufficient empirical power.

## Exposure and implementation history

The initial metadata output mixed receiver-score variants and was invalidated before outcome access. The corrected unique-key PURE_D design alone entered the gate. Source-manifest omissions were corrected as disclosures before the signed opening review. These were result-blind metadata repairs, not outcome-selected changes.

The H2 source stack is not globally pristine. Earlier concentration-stage processing loaded 452 H2 delisting records without using their values in H1 estimates or model-visible results. This stage does not certify absence of every unrelated historical access. The bound ledger remains unchanged, with the new authorized response access recorded separately in execution receipts.

## One concrete next action

**Archive this completed test and stop new purchases and automatic sample expansion for this coholding/earnings-response route.** Do not run another year merely to look for a favorable coefficient.

Continuing the broader concentration story would require a separately justified question and design that can distinguish industry fundamentals from ETF transmission; it is not authorized as an automatic continuation of this inconclusive result. This recommendation is a resource-allocation decision under weak evidence, not a claim that all information-transmission mechanisms have been disproved.

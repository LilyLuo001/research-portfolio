# P1 compute handoff — 2026-09-13

## Scope and sealing

Implemented outcome-sealed support diagnostics and a **GENERIC_POOLED_CONTINUOUS_ORACLE_FIXTURE / DEVELOPMENT_FIXTURE** only. The production runner validates the canonical detached exposure root, exact expected SHA256 for each of the three exposure files, and rejects outcome-like paths before CSV parsing. I did not open any actual or uncertain earnings-response result, earnings calendar, SUE/actual/forecast, quote, CAR, residual, IRR, VECM, Refraction, control, calibration, or empirical design file.

`support_diagnostics.csv` makes the boundary explicit: counts and exposure concentration are `MEASURED_NOW`; actual earnings-event/session/horizon-mask/SUE interaction/residualized design/contrast leverage/covariance and empirical MDE rows are `NOT_AVAILABLE`.  The old raw-exposure `design_stats()` ESS/MDE is marked `INVALID_ESTIMATOR_NONINVARIANT`: its raw-dose-square and imposed variance shares omit SUE, post, nuisance FWL residualization, actual complete masks, and outcome covariance.

## Measured metadata results

From `primary_ready == True` and positive ownership exposure: all sponsors have 8,801 stock-wave cells, 3,440 stocks, 30 waves, 2,380 repeated stocks (maximum 16 waves), and 583 / 573 stocks / 4 waves at >=0.5% ownership.  Dimensional-only has 3,503 / 2,548 / 2 and 561 / 559 / 2 at the threshold; excluding Dimensional has 5,638 / 2,979 / 29 and 21 / 21 / 2.  Adviser labels remain explicitly **unsigned proxies**, so leave-one-proxy rows are not economic-sponsor LOSO.  The CSV also provides leave-one-wave/proxy counts and cell/exposure HHI/top-share concentration.

## Generic pooled continuous oracle development fixture

`power_results.csv` has seven fixed-seed, 2,000-rep fixture cells: iid null; dependence-plus-few-proxy null; timing shift; slower shift; amplitude-only; mixed amplitude/timing; and timing shift with invented missingness, dependence, and few proxies. Its invented six-horizon panel uses a toy pooled continuous dose and lower-order terms, weighted FWL (`Q=sqrt(W)`, residualized `QZ`, and `B=(Zr'Zr)^-1 Zr'Q`), an oracle synthetic covariance, and the joint amplitude restriction `q_h=beta_h-f_h beta_T`. It is explicitly **not candidate A/B/C, equal-wave aggregation, stock×wave FE, the full estimator, or empirical power**. It does not model repeated economic-event mapping, common-date shocks, ordered event serial dependence, or heterogeneous slope shocks. Matching geometry/dependence scenarios reset a common random stream; missingness/few-proxy fixtures necessarily map that stream differently. No timing classification/equivalence is made: the terminal-equivalence margin is not signed.

Fixture joint-restriction rates (95% Monte Carlo intervals) are 4.2% [3.3%,5.1%] iid-null, 5.0% [4.0%,6.0%] dependence/few-proxy null, 20.7% [18.9%,22.4%] timing shift, 19.9% [18.2%,21.6%] slower shift, 4.9% [3.9%,5.8%] amplitude-only, 20.7% [18.9%,22.4%] mixed amplitude/timing, and 14.7% [13.1%,16.2%] missingness/dependence/few-proxy timing shift. These are properties of assumptions, not empirical MDEs, candidate selection, or an overall P1 verdict.

## Checks and receipts

All commands exited `0`:

```sh
cd /Users/lilyluo/research-portfolio-p1-feasibility-20260913
python3 -m pytest -q p1/feasibility_adjudication/20260913/tests/test_sealed_support_and_conditional_power.py
python3 p1/feasibility_adjudication/20260913/code/sealed_support_and_conditional_power.py \
  --readonly-exposure-dir /Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure \
  --output-dir p1/feasibility_adjudication/20260913 --reps 2000 --seed 20260913
```

Tests cover direct weighted full-fit/FWL equality, 1000x treatment scaling invariance, known-covariance versus Monte Carlo variance, canonical-path/hash and forbidden-path denial, blank/future/effective-date/pre-announcement/ownership-unit/signed-sponsor/rank guards, and internally enumerated protected-input blocking. No bytecode artifact is retained. Empirical calculation remains blocked pending the row-filtered protected calendar/SUE/controls/session/horizon mask and a signed economic-sponsor crosswalk/cluster rule, plus the unresolved PI contract choices.

## Remediation appendix — 2026-09-13

The independent review in `review.md` remains intact and controls the description of the original implementation. This remediation does **not** implement the unresolved candidate A/B/C, equal-wave, stock×wave, full-contract, or empirical power procedure.

Changes made: production input parsing now requires the exact detached root and source SHA256 for all three exposure files; test fixtures alone can opt into a noncanonical path. Ownership must lie in `[0,1]`, blocking a 1000x unit corruption. The loader has a separate pre-announcement eligibility function that blocks a missing announcement map and rejects holdings reports after announcement; it was deliberately not run on current exposure, so no pre-announcement pass is claimed. Actual-design requirements are internally enumerated and require canonical protected-view paths; empty and partial dictionaries fail. A sponsor crosswalk must have signed schema/content, not merely exist. `power_results.csv` now has `NOT_AVAILABLE` rows for actual A/B/C complete-estimator power, MDE80/MDE90, timing equivalence, and boottest size/coverage.

The generic fixture adds slower and mixed scenarios and uses reset common random streams for matched scenarios. It no longer claims repeated-event, common-date, or heterogeneous-slope handling. Final receipts (all exit `0`, no bytecode/cache):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider p1/feasibility_adjudication/20260913/tests/test_sealed_support_and_conditional_power.py
PYTHONDONTWRITEBYTECODE=1 python3 p1/feasibility_adjudication/20260913/code/sealed_support_and_conditional_power.py \
  --readonly-exposure-dir /Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure \
  --output-dir p1/feasibility_adjudication/20260913 --reps 2000 --seed 20260913
```

Final coordinator micro-fix after referee re-review materialized iterable inputs inside the pre-announcement validator and added an iterator regression assertion. A subsequent whitespace-only cleanup produced the final code hash. Final SHA256: code `6fdf52bfed7eb3a32d336e8b85cd6816a8fdbc55e54c69232bdb0d1118f6239d`; tests `05f8c63ec83431608d7a15ab1b1edb43386f091936ed51a4451df4517950e3bb`; support output `34f848586e71fcc72f0d6cec9f74265980c30bacea61fecc67adbbcf818c884f`; power output `e5b9cb8d94acd4f917b7832e3c7c89d507c3cf347be05b8c7c4a936db9c28669`. Canonical source hashes: all `905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320`; Dimensional `c4acb697f4d8e2a13168deca58187ebfc9bcfcc73b086c77ed6cd6b925044967`; excluding Dimensional `383ea34668d74efcaf1da771dfa2e994960a7e56c2d28f99d829639ad259a9ba`.

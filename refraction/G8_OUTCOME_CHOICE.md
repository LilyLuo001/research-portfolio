# G8 primary outcome — the decision record

**Status: UNRESOLVED.** `network_exposure.first_stage_primary_outcome` is `null` in
`refraction/frozen_config.yaml` and stays null until this file is filled in and committed.
`g8_first_stage.verdict()` refuses to adjudicate G8 without the resolved choice, so the
ordering is enforced in code rather than by discipline.

Freeze 1 of 2026-08-28. Supersedes the composite phrase "abnormal volume / order imbalance",
which was two different outcomes wearing one name — and they do not take the same exposure.

---

## What is registered

| | preferred arm | fallback arm |
|---|---|---|
| Outcome | `sign(CR_{f,t}) × OIB_{i,t}` | `AbnVol_{i,t}` |
| Sign handling | the flow's sign enters the **outcome** | unsigned |
| Exposure | **\|CR_{f,t}\| × \|L_tilt^pre_i\|** | **\|CR_{f,t}\| × \|L_tilt^pre_i\|** |
| Timing | measured on the CR day (lag 0) | measured on the CR day (lag 0) |
| Test | one-sided, a₁ > 0, on the linear coefficient | same |
| Needs | signed trade classification | volume only |

Both arms take the **same** exposure, and that is the point. `signed CR × |L|` is registered
as **forbidden for the primary**:

* against **unsigned** abnormal volume it tests nothing — a positive and a negative creation
  of equal size predict opposite volume responses, which no mechanism claims;
* against the **sign(CR)-aligned** imbalance it counts the flow's sign twice, so the
  coefficient is a function of |CR| again but with the interpretation obscured.

`signed CR × |L|` survives only where it started: the **signed return corroboration**, whose
sign has meaning only under a timing model (see `G8_SIGN_PREDICTION.md`).

The preferred arm is preferred on economics, not convenience. Abnormal volume rises with any
attention shock; aligned order imbalance rises specifically when constituent flow moves *with*
the creation/redemption, which is the arbitrage channel and not a proxy for it.

## The rule that picks the arm

Evaluated **only** on G7's data-quality report, and **only before** any G8 treatment
coefficient exists. Use the preferred arm iff **all four** hold:

| criterion | floor | measured |
|---|---|---|
| `signed_trade_classification_available_share` | ≥ 0.90 | _fill from G7_ |
| `intraday_coverage_share_of_volume_sample` | ≥ 0.95 | _fill from G7_ |
| `cross_algorithm_daily_oib_sign_agreement` | ≥ 0.95 | _fill from G7_ |
| `cr_timestamp_audit_complete` (freeze 2) | true | _fill from the audit_ |

Otherwise: the fallback arm. Notes on each:

* **Availability at 0.90.** Trade signing fails on auctions, odd lots and crossed quotes.
  Below ~0.90 the signed sample is a selected subsample of the volume sample, and the two
  arms would no longer be measuring the same stocks.
* **Coverage at 0.95, deliberately higher.** This one exists so the *choice of outcome cannot
  move the sample*. If the arms ran on materially different constituent-days, a comparison
  between them would confound outcome with sample.
* **Cross-algorithm agreement at 0.95.** Meta-rule 2: signing is a high-error step, so two
  independent implementations must agree on the daily sign before the sign is used.
* **All-or-nothing.** A partial pass would leave room to argue afterwards about which
  criterion mattered — the exact move pre-specification exists to stop.

None of these mentions an outcome, a coefficient, or a p-value. That is checked by a test.

## Procedure

1. G7 emits the three measured shares; the freeze-2 audit is recorded.
2. Run `g8_preflight.choose_primary_outcome(g7_quality, config)`.
3. Paste its output below, set `first_stage_primary_outcome` in `frozen_config.yaml`, commit
   **both** in one commit, before any G8 estimation runs.
4. Only then estimate. `verdict()` cross-checks that the estimated exposure matches the arm
   recorded here.

## Recorded decision

```
NOT YET RESOLVED — G7 has not run.
chosen:   <arm name>
arm:      <preferred | fallback>
exposure: abs_CR_x_absL
checks:   <paste the checks dict>
failures: <paste, or empty>
decided:  <ISO timestamp>   basis: G7 data quality only
```

**If this block still says NOT YET RESOLVED, G8 has not been adjudicated and any coefficient
in circulation is unregistered.**

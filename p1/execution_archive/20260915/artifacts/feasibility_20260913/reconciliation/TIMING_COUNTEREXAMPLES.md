# Deterministic timing and aggregation counterexamples

These are algebraic fixtures, not P1 outcome estimates. They use no licensed or sealed inputs. The executable source is `code/contract_counterexamples.py`; tests are in `tests/test_contract_counterexamples.py`.

## A. Heterogeneous baseline shapes: amplitude is not pure timing

| Group | PRE `(early, T)` | POST `(early, T)` | Within-group normalized shape PRE/POST |
|---|---:|---:|---:|
| High dose | `(0.80, 1.00)` | `(0.96, 1.20)` | `(0.80, 1.00)` / `(0.80, 1.00)` |
| Low dose | `(0.40, 1.00)` | `(0.48, 1.20)` | `(0.40, 1.00)` / `(0.40, 1.00)` |

Each group is multiplied by 1.20; neither group's normalized timing changes. Yet the high-minus-low DID of raw slopes is `(0.08, 0.00)`. A common-reference test `q_h=beta_h-f_h beta_T` is also positive early whenever `beta_T=0`, regardless of `f`. Therefore raw differential response change cannot be called pure timing merely because its terminal differential is zero.

The proposed hierarchy is:

1. Report the raw equal-wave signed slope curve `theta_h` as the primary differential conversion-package response.
2. Report group-specific normalized relative-shape DID `kappa_h` only under an added normalized-shape counterfactual restriction, with joint reference uncertainty.
3. Use “pure timing” only if tier-specific counterfactual terminal and shape transport are justified, both tier-specific terminal package effects satisfy an approved equivalence margin, and the directional shape contrast is meaningful. Otherwise the result is a relative shape change or mixed amplitude/shape change.

Weak or sign-uncertain terminal references are a failure state, not a trimming rule. `+1d` is an operational terminal horizon, not fundamental value. Treating a fitted reference as fixed misstates uncertainty: covariance can increase or decrease a variance estimate, but cannot be omitted.

## B. Equal-wave target is not pooled information weighting

For residual doses `(-1, 1)` with wave effect 0 and `(-3, 3)` with wave effect 1:

```
pooled = sum(x_w y_w) / sum(x_w^2) = 18 / 20 = 0.9
equal-wave target = (0 + 1) / 2 = 0.5
```

Equal row mass per wave does not make residualized information equal. The contract therefore estimates wave-specific coefficients/influences first, fixes the eligible-wave set before responses, and averages those effects explicitly.

## C. Reused earnings events

One economic event appearing twice with influence weights `(0.5, 0.5)` has variance `(0.5+0.5)^2=1` when its shock is shared. Treating duplicated rows as independent incorrectly gives `0.5`. The proposed aggregation deduplicates only the shock/influence representation; it does not delete stack appearances or silently inverse-weight them.

## D. Estimated references

For a terminal reference 0.05 with standard error 0.10, a two-sided 95% confidence set includes zero. Normalized timing is therefore blocked. Even a non-weak reference must propagate reference/coefficient covariance jointly; treating a fitted reference curve as fixed **misstates** uncertainty, and the direction depends on covariance.

## E. Draft gate

The executable test reads the actual reconciled YAML. Its document status is `PROPOSAL_NOT_PI_APPROVED` and all `pi_approval` values are `false`, so the metadata-extract scope lint returns `FAIL_DRAFT_CANNOT_SELF_APPROVE`. Editing approval booleans inside a draft cannot change that result. Even a hypothetical future `PI_APPROVED` mapping with both purpose-scoped metadata booleans returns `AUTHORITY_VERIFICATION_REQUIRED`; this helper is not an access gate. An owner record, signed contract hash, and authorized protected view are external checks that this reconciliation does not implement. The outcome-access scope lint returns `FAIL_SEALED_OUTCOME_NOT_AUTHORIZED`. Neither route authorizes SCC work, a data purchase, or empirical treatment estimation.

# P1 method V2: bounded synthetic estimator interface

2026-09-21. Status: `METHOD_PROTOTYPE / HOLD_METHOD`. This is a small,
synthetic-only implementation of selected V1 algebra and design guards. It has
not read a price, quote, return, news signal, holdings record, or any other
empirical value. It is neither an approved confirmatory contract nor a
production-ready inference system.

## What changed from V1

| V1 issue | V2 interface | Status |
| --- | --- | --- |
| ETF and basket could be described without executable eligibility checks | `paired_response` requires a caller-supplied `ACTUAL_HOLDINGS` basket, live quote states, positive anchors, and identical evaluation-time uncertainty intervals at anchor/h/H | Implemented logical guard; no feed parser certified |
| A pooled slope would x²-reweight heterogeneous F* cells and could be mistaken for a company average | `fixed_common_support_weights` fixes proposed F* cells, issuer target weights, then ETF weights that sum to one within each repeated event; `fit_joint_standardized_slopes` fits cell-specific slopes and applies fixed cell weights linearly | Implemented synthetic interface; `PROPOSED_NOT_FROZEN` |
| Same news across ETF rows risks pseudoreplication | `fit_joint_standardized_slopes` retains each ETF--basket row and clusters the four-response score by `event_id` | Implemented only for synthetic event clustering |
| Ratio uncertainty could discard weak denominators | `fieller_set` inverts the joint numerator/denominator test and retains bounded, half-line, two-ray, all-real, and empty sets | Implemented algebra only |
| TOP--REST contrast might subtract two marginal intervals | `ratio_contrast_confidence_set` returns `NOT_IMPLEMENTED` rather than doing that | Deliberate blocker |
| Total change may be a composition change | `composition_decomposition` implements the symmetric accounting identity and rejects nonaligned/invalid support | Implemented logical algebra |

V1 remains the scientific rationale and is not overwritten. In particular,
leading prices do not identify ETF-to-stock causal transmission, H is a finite
reference response rather than true value, and D is not an information share.

## Proposed estimand and weights

For a paired ETF--actual-basket observation j of issuer news event e, let the
four caller-supplied cumulative responses be

`Y_j = (r_ETF(h), r_basket(h), r_ETF(H), r_basket(H))`.

Within each fixed common-support F* cell c and group g, V2 fits the weighted
conditional linear projection of each response on V1's prevalidated news
regressor `x_if,e = w_if,e * z_e` (with intercept), where the event's external
signal `z_e` is multiplied by its pre-event issuer weight in that ETF. The slope
vector is `beta_g,c`. V2 then applies declared fixed cell weights linearly to
these **cell-specific** slopes. It does not pool rows across c: such a pooled
regression would instead reweight cells by within-cell `x²`, changing the
estimand. The early paired
difference and terminal reference response are

`N_g,c = beta_ETF(h) - beta_basket(h)` and
`kappa_g,c = (beta_ETF(H) + beta_basket(H))/2`,

with `D_g,c = N_g,c / kappa_g,c` only as a ratio estimand with a Fieller set.
It is not a fraction of firms informed, a causal information share, or a
company-average response speed.

The **PROPOSED** F* standardizer is explicit. Each fit selects exactly one group
(`TOP` or `REST`) and renormalizes within that group; a combined TOP/REST call is
rejected. Each `(c, g)` has its own fixed,
predeclared issuer target; TOP and REST are not required to contain the same
issuers. When comparing concentration states, the appropriate group-specific
target must be held consistent across those states (or the comparison is
rejected as unsupported). Fixed issuer mass is divided equally over that
issuer's qualifying news events; each event's predeclared ETF weights sum to
one before issuer mass is applied. Thus same-news ETF rows remain separate
paired observations, yet an issuer is not upweighted merely for producing more
events. Fixed c weights then form the standardized projection. This is a
weighted conditional linear-projection target, not a statement about average
issuers. The interface rejects a mismatch with the caller's declared target
instead of silently changing it.

Neither the F* cells, issuer and ETF target weights, signal normalization,
TOP/REST definition, `h`, H, quote side, sessions, equivalence band, nor
critical-value/calibration rule is frozen. V1's 5/60 minute, TOP5, and ±10%
ideas remain `PROPOSED_NOT_FROZEN`; there is no default confirmatory analysis.

## Dependence and uncertainty boundary

The implemented score covariance is joint across all four slope coefficients
and clusters repeated ETF observations by the **same event**. It therefore does
not pretend that ETF rows for one announcement are independent. The test fixture
also checks that this covariance is PSD and, in its deliberately shared-shock
construction, exceeds the row-IID analogue.

This does **not** validate issuer×date multiway clustering, overlapping event
windows, cross-ETF/date graph dependence, a small-cluster correction, or an
empirical critical value. Those remain `NOT_IMPLEMENTED`; a real study must
validate an estimator against its actual permitted metadata/dependence design.

For a supplied joint 2x2 covariance of `(N, kappa)`, Fieller inversion retains
weak-denominator unbounded and disconnected confidence sets. Cross-group
`D_TOP - D_REST` confidence sets require inversion of a joint four-coefficient
test region. V2 intentionally does not use a finite grid (which can miss tails)
or subtract marginal ratio confidence intervals. Its interface returns
`NOT_IMPLEMENTED` pending a reviewed joint procedure.

## Composition accounting

For fixed aligned groups, weights p and conditional ratios D, V2 reports

`V1 - V0 = sum(mean(p) * (D1-D0)) + sum(mean(D) * (p1-p0))`.

The first term is within-group response change and the second is composition
change. This is accounting only, not a policy counterfactual. It cannot repair
within-group issuer replacement; that requires the fixed-support standardizer.

## Guards and known nonclaims

- A PCF, index, or proxy basket is rejected; the code cannot establish that a
  caller's claimed basket is truly historical holdings.
- Valid but unchanged quotes are accepted as live state. The stored intervals
  are target evaluation-time uncertainty, not raw exchange last-update times;
  ETF and basket must share the same target intervals while last updates may
  differ. Invalid/cancelled state, nonpositive anchors, or unresolved target
  intervals are rejected.
- Bid, ask, and mid are explicit caller labels. This does not establish NBBO or
  executable basket depth, and it cannot reconcile opposing quote-side results.
- No automatic treatment is supplied for reversals, terminal equivalence,
  platform stability, new news within H, session closure, corporate actions, or
  clock/source provenance. Their data-dependent gates remain outside this
  synthetic module.
- Passing tests only verifies designed branches and algebra. It is not empirical
  power, coverage calibration under the target design, theoretical proof, or
  evidence for the P1 hypothesis.

## Files and reproduction

Run only from `method/`:

```bash
python3 synthetic_tests.py
python3 -m py_compile estimator.py synthetic_tests.py
```

`synthetic_tests.py` uses a fixed seed and writes
`method/SYNTHETIC_TEST_RESULTS.json`. It checks fixed-F* mass ordering,
common-support and proxy/clock rejections, actual paired response handling,
event-cluster covariance PSD/ordering, nonfinite and non-PSD input rejection,
repeat-event dependence, the unequal-signal-variance counterexample to pooled
x² weighting, weak denominators, honest unresolved joint contrasts, and
composition separation. These are logical synthetic tests, not an empirical
power calculation.

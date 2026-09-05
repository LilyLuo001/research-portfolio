# Corrected calendar and taxonomy-bridge uncertainty

**Analysis status:** post-outcome exploratory; not part of confirmatory YAX
v1.1.  This memo responds only to RR2-M5 and secondary comment 1.4.  It does
not revise the manuscript or the protected design.

## Executive finding

The corrected March calendar should replace the known incomplete calendar as
the substantive descriptive baseline.  Restoring five basic-month March
samples changes the beta-by-Webb Q5--Q1 coefficient only from `-0.13107` to
`-0.13455`; the revised 9,999-draw interval is `[-0.22282, -0.04629]`.  The
frozen value remains necessary for chronology, but no longer needs to carry the
economic exposition.

The official one-to-many bridge is a real layer of age-allocation uncertainty,
but it is not necessary for the negative estimate.  Restricting the corrected
model to the 369 primary-support targets with no structurally possible split
inbound route makes the fixed-label estimate more negative, `-0.16736`
(`[-0.26840, -0.06633]`).  Recomputing the comparison on that clean support
gives `-0.14708` (`[-0.24283, -0.05134]`).  The already audited stable-Census-
2010 specification gives `-0.15222`.  These are support/taxonomy sensitivities,
not proof that the official common-proportion bridge is correct.

## The 490 and 495 counts are not nested samples

The apparent five-occupation expansion is a misleading subtraction.  The raw
route-expanded reconstruction contains **539** target occupations with
positive young and older stock over the same 66 preperiod months.

- The **490** stored preperiod occupations are the beta cell-builder support:
  positive stock in both age groups **and full beta-exposure coverage**.  Webb
  is applied later, leaving the 468-occupation beta-by-Webb primary support.
- The **495** continuous-mapping occupations are the 539-candidate subset with
  finite repaired AIOE and Webb.

The two architecture-specific supports overlap in 466 occupations.  Twenty-
four are in the 490 beta support but not the 495 AIOE-plus-Webb support; 29 are
in the latter but not the former; and 20 of the 539 raw balanced candidates are
in neither architecture-specific support.  Every one of the 29 AIOE-plus-Webb-only
occupations lacks finite beta, while 22 of the 24 beta-only occupations lack
Webb.  Therefore 495 does not mean that five occupations were added to the
headline sample.  `UNIVERSE_RECONCILIATION.csv` names every occupation and
records the membership reason.

## Where the split bridge enters

Within the 468-occupation beta-by-Webb support, one-to-many sources contribute
14.93 percent of young and 17.75 percent of older weighted stock during the
bridge-dependent 2017--2019 period.  Their role differs across the fixed beta
tails:

| early-period tail | young stock from split sources | older stock from split sources |
|---|---:|---:|
| Q1 | 17.48% | 17.13% |
| Q5 | 21.57% | 26.32% |

From 2020 onward the CPS occupation is observed directly in the Census-2018
taxonomy, so this allocation issue is confined to the event-study baseline and
other pre-2020 comparisons; it does not split postperiod observations.

Ninety-nine of the 468 primary targets have a structurally possible split
inbound route.  They carry 23.38 percent of fitted conditional information for
the corrected Q5 post coefficient.  If each occupation-month's information is
allocated in proportion to its split-source stock, 4.44 percent is assigned to
split stock.  The first number is a conservative touched-target diagnostic;
the second is explicitly a proportional attribution, not an identified
decomposition.

## What age-specific uncertainty can and cannot show

Official conversion rates are totals, not age-specific probabilities.  Using
the same rate for young and older source records preserves a source's age ratio
across its target components by construction.  The data and bridge do not
identify a correct replacement.

Unrestricted allocation across each source's officially allowed routes gives
the following sharp **stock-accounting** ranges for 2017--2019:

| fixed tail | official young/older stock ratio | allowed-route accounting range |
|---|---:|---:|
| Q1 | 0.1227 | [0.1031, 0.1480] |
| Q5 | 0.0951 | [0.0790, 0.1175] |

These ranges show that tail-specific preperiod levels are not point identified
without age-specific routing information.  They are not bounds on the
regression coefficient because the nonlinear fixed-effect estimator and the
other quintile cells also change.

The predeclared exposure-directed scenarios are deliberately narrower.  They
alter young versus older allocation odds toward the highest-beta target by a
factor `K` from 0.5 to 2, hold all model labels/scales fixed, and leave
ineligible routes at official weights.  Only 20 split sources, representing
6.88 percent of matched early stock, have complete nonconstant beta and Webb
scores across every allowed target.  Across this limited covered subset, the
coefficient ranges from `-0.12923` (`K=0.5`) to `-0.13907` (`K=2`), versus
`-0.13455` at `K=1`.  This shows modest sensitivity over the declared scenario
grid; it is not a global robustness result because most split-source stock is
not scenario-eligible.

## Implications for the revision

1. Use the corrected 113-month coefficient `-0.13455` as the substantive
   baseline and label `-0.13107` the frozen chronology benchmark.
2. Replace any “490 versus 495” sample-flow language with the 539/490/495
   reconciliation.  The two reported counts apply different exposure/control
   availability filters and are not nested.
3. Present the pure one-to-one and stable-Census-2010 estimates prominently.
   They show that the negative association does not depend on split routes,
   while still changing the target population.
4. State directly that common bridge weights do not propagate age-specific
   allocation uncertainty.  Report the accounting ranges and the limited
   tilt path; do not call either a correction or attach probabilities to them.
5. Treat the naive 410-occupation exact-code AIOE merge as an implementation
   error.  The machine-readable compatibility gate rejects exact-code equality
   between SOC-2010 AIOE and Census-2018 outcomes and requires a versioned
   bridge.  The repaired AIOE-plus-Webb support is 495, so the naive workflow
   loses 85 occupations.

## Reproducibility record

`run_bridge_uncertainty.py` reconstructed both baselines and all aggregates on
SCC without writing person records.  `EXECUTION_RECEIPT.json` records public
and private input hashes and every primary output hash.  The SCC self-check
rehashes all three licensed inputs, verifies the 490/539/495 identities,
baseline coefficients, adding-up constraints, scenario mass conservation, and
absence of person identifiers or raw weights in repository outputs.  Its status
is `PASS_BRIDGE_UNCERTAINTY_SELFCHECK`.

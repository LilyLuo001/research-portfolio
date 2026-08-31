# YAX Phase 2 decision memo

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

## Decision

**PATH-2B — Measurement-economic result.**

Phase 2 does not identify a clear worker-flow mechanism behind the frozen YAX
employment-stock gradient. It does establish that alternative AI-exposure
architectures frequently reverse the direction assigned to occupational moves
workers actually make. The flow-treatment extension should therefore stop,
while the realized-reallocation measurement result is a candidate third YAX
block subject to its common-support limitation.

## Weighting and linking

IPUMS CPS extract 10 adds `LNKFW1MWT` to the exact 9,262,480-row wide-extract
universe. The merge on `YEAR MONTH SERIAL PERNUM` is 100%; all longitudinal
identifiers agree exactly. Among 4,500,962 legitimate ages-22–65 adjacent
origins, CPSIDP links 4,124,467 (91.64%) and CPSIDV links 4,085,493 (90.77%).
The CPSIDV subset retains 98.98% of the official-weighted CPSIDP-linked
population. Retention is 98.77% for young versus 99.00% for older workers and
98.92% pre versus 99.05% post. Across beta quintiles it ranges from 98.70% to
99.23%.

The primary weight is the origin's `LNKFW1MWT` on a validated CPSIDV adjacent
link. It does not eliminate selection into valid links. Unweighted estimates
are sensitivities; `WTFINL` is labelled non-longitudinal. No long-gap or false
September→November 2025 link is used.

## Primary beta flows: FLOW-M5

| margin | official-weight beta Q5/Q1 coefficient | wild 95% CI | p-value |
|---|---:|---:|---:|
| employment exit | 0.1195 | [−0.0668, 0.3059] | 0.229 |
| occupational outflow | 0.0107 | [−0.1063, 0.1277] | 0.857 |
| entry destination | −0.0888 | [−0.2787, 0.1011] | 0.383 |

The point estimates for exit and entry face the stock-consistent directions,
but all three official-weight intervals include zero. The declared persistent
outflow sensitivity is −0.0246 [−0.2580, 0.2088]. The unweighted exit estimate
does exclude zero (0.1824 [0.0299, 0.3349]), whereas the official and ordinary
cross-sectional-weight estimates do not. That weighting dependence reinforces
the FLOW-M5 classification rather than licensing an unweighted mechanism
claim.

Stage 2B was stopped. No six-architecture treatment-effect grid was executed.
The appropriate mechanism classification is **ARCH-MU — unresolved**, because
there is no informative primary margin to carry across architectures.

## Realized transition architecture result

The independent descriptive test begins with 186,370 harmonized adjacent
occupational switches and retains 108,500 (58.2%) whose origin and destination
have finite exposure under all six architectures. This literal-common-support
loss is material and bounds external validity.

Within that sample:

- 53.28% of official-weighted realized transitions receive at least one
  positive and one negative directional classification across the six
  architectures;
- only 45.56% receive the same nonzero direction from all six;
- pairwise sign agreement ranges from 56.52% to 96.58%;
- pairwise correlations in pre-period-rank change range from 0.195 to 0.984;
- the mean within-transition max-minus-min rank change is 0.434;
- conflict rises to 54.46% under the declared persistence sensitivity, so the
  result is not driven by immediate A→B→A reversals.

Across all 76,636 possible unordered common-support occupation pairs, conflict
is 41.28%. Realized switches are 12.00 percentage points more conflict-heavy
(53.28%), so measurement disagreement is concentrated—not diluted—on
economically realized moves.

The one predeclared young/post comparison is null. Conflict rates are 49.59%
for young pre, 50.79% for young post, 53.23% for older pre, and 54.44% for
older post. The young×post difference-in-differences is −0.003 percentage
points, with a 95% interval of [−2.67, 2.66] percentage points. Thus exposure
architecture matters for interpreting worker reallocation generally, but the
diagnostic does not show that disagreement became uniquely more relevant for
young workers after January 2023.

## Manuscript recommendation

Do not present the flow estimates as a mechanism decomposition and do not add
them to the headline tables. A short appendix can report FLOW-M5 and the
longitudinal-weight correction transparently. The Phase-1 age profile may
enter the eventual manuscript as a bounded descriptive extension, with its
precision caveat.

The realized-transition result is the substantive candidate for a third block:
the same observed move can be labelled toward or away from AI exposure solely
because the exposure architecture changes. Any manuscript use must lead with
the 58.2% literal-common-support coverage and the null young/post difference.
The claim is measurement-economic, not causal.

Do not pursue digital complementarity inside the current YAX chapter before
owner review. It would create a fourth architecture after the flow gate has
already returned no clear mechanism. Preserve it as a separate future
feasibility branch if the chapter later needs a different economic question.

The current ceiling is a credible dissertation chapter and potentially a
field/measurement journal paper after strengthening the support/selection
analysis and integrating the literature. FLOW-M5 does not raise the project to
a top-field or general-interest causal contribution.

## Integrity

No BTOS, adoption, digital-capital, wage/hour, demographic-heterogeneity,
PCA/factor, major-to-career, or additional timing analyses were executed.

Long-gap CPS links were not used.

The immutable v1.1 confirmatory results and V4.1 manuscript baseline were not
altered.

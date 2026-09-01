# YAX — Architecture-Robust Inference Feasibility

**POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

## Conclusion

The existing score/influence infrastructure can technically support simultaneous
inference for a **vector of architecture-specific estimands**, provided every fit is
run on a declared common analytic sample and the same occupation-cluster Rademacher
multiplier is applied across all coordinates. It cannot turn estimates with different
treatment memberships or native supports into six noisy measurements of one common
parameter.

No new inferential battery was executed for this note.

## What is technically available

The frozen grouped-binomial/PPML implementation stores occupation-cluster influence
contributions and already uses 999 common Rademacher multipliers. Test C demonstrates
that common draws preserve paired covariance for beta versus alpha; the stored paired
covariance is `9.4666e-05`. The V3/V4 event-study code also implements a maximum-
absolute-studentized-statistic critical value and simultaneous bands. These pieces are
sufficient to support, in a future authorized run:

1. a max-|t| simultaneous confidence set for a declared vector of architecture-
   specific coefficients;
2. a familywise statement about which vector coordinates have signs robust to the
   simultaneous intervals;
3. joint confidence regions based on the common-draw covariance matrix; and
4. paired differences whose covariance is preserved by common occupation multipliers.

The draw must be common at the occupation-cluster level across every model, missing
clusters must contribute an explicit zero influence rather than receive a new draw,
and studentization and finite-draw quantiles must be declared before execution.

## The estimand obstacle

Exposure architectures change Q1/Q5 membership even on identical occupation support.
Native-support models also change the occupation population. Consequently,
`beta_m` and `beta_m'` generally index different treatment contrasts, and a native-
support difference additionally mixes measurement architecture with sample change.
Max-|t| adjustment controls simultaneous coverage of that heterogeneous vector; it
does not establish that the coordinates estimate a single causal effect.

There are two defensible future objects:

- **Common-support architecture vector:** identical outcome sample and controls, each
  architecture retaining its own frozen Q1–Q5 membership. This supports simultaneous
  statements about a vector of explicitly different contrasts.
- **Declared paired comparisons:** a small number of architecture differences on
  pairwise common support, interpreted exactly as Test C—statistical distinguishability,
  never economic equivalence when a confidence interval includes zero.

Native-support point estimates may be shown descriptively beside those objects, but
they should not enter the same joint “robustness” null without redefining the target.

## Stored-results limitation

Point estimates and marginal standard errors alone do not recover cross-model
covariance. A stored common-multiplier draw matrix or occupation-level influence
representation is required. YAX has that machinery and authenticated representations
for specific existing exercises, but it does not currently store a complete six-
architecture outcome draw matrix. Producing one would be a new inferential battery
and is outside Gate 3.

Thus architecture-robust inference is **technically feasible with conceptual limits**,
not already completed and not a methodological contribution.

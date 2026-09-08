# Gate 3 non-lambda architecture reconciliation

Status: **post-outcome exploratory; written before this current-contract run**.
The frozen v1.1 design and confirmatory results are unchanged. No output from
the run specified here has been inspected when this document is committed.

This block resolves L03, the current-contract empirical part of W05, and
preserves W06 by mechanically validating the already completed 113-month
lambda and D/S audit. It does not select an exposure definition using outcomes.

## 1. Fixed outcome and estimator contract

The outcome object is the protected Gate 3 calibration on the current
468-occupation BASE-03 support and 113 observed Basic CPS months from January
2017 through July 2026. Ages 22--25 are compared with ages 26--65, December
2022 is excluded as the transition month, and October 2025 is absent because no
CPS survey was fielded. Employment stocks were aggregated once with `WTFINL`.

Every fit is a grouped-binomial two-age model. The pooled specification has
occupation and calendar-month fixed effects; the family-month specification
has occupation and SOC2-family-by-calendar-month fixed effects. Categorical
models contain Q2--Q5 by post and standardized Webb-software by post, with Q1
omitted. Continuous models contain the exposure score and Webb-software, both
standardized with preperiod employment weights and interacted with post.

Inference uses 9,999 common Rademacher score-multiplier draws at both the
occupation and SOC2-family levels. Paired differences are formed before
applying the common multipliers. An interval containing zero means only that
the design does not detect a difference; it does not establish equivalence.

The full-support Rule-A beta categorical fit must reproduce the current pooled
coefficient `-0.13210945079219025` and family-month coefficient
`-0.021674952018246537` within `1e-8` before any result is published.

## 2. Non-lambda exposure definitions (L03)

The five inherited non-lambda alternatives are run separately:

1. AIOE administrative/equal-component mapping;
2. AIOE direct ability mapping;
3. AIOE source-employment-weighted mapping;
4. Webb artificial-intelligence exposure; and
5. OECD reversed AI-skills gap.

For each alternative, the analysis support is the intersection of its finite
score with the fixed 468-occupation outcome support. On that exact support and
the same preperiod weights, the runner constructs the alternative's quintiles,
its standardized continuous score, a fresh Rule-A beta anchor, and the common
Webb-software control. Both estimators and both functional forms are fit for
the alternative and its beta anchor. Thus every reported alternative-minus-
beta difference holds outcome cells, support, weighting, estimator, calendar,
and nuisance treatment fixed.

Because the three AIOE implementations have slightly different availability,
they are also fit on their complete common support. All three pairwise AIOE
implementation comparisons are reported there. AIOE variants are alternative
implementations of one construct; Webb AI and OECD are different constructs.
Neither group is mislabeled as an independent replication of the other.

## 3. Units and scaling (W05)

The published AIOE occupation index is standardized across source occupations
without employment weighting. After mapping to Census-2018 occupations, one
raw unit remains one unit of that published source-index scale; it is not a
percentage. YAX separately restandardizes every continuous exposure on the
analysis support using January-2017--November-2022 employment stock.

For every continuous model the output reports the raw weighted mean, standard
deviation, minimum and maximum; the coefficient and uncertainty for a one-
current-support-weighted-SD increase; and the algebraically transformed
coefficient and uncertainty for a one-raw-unit increase. These are scale
descriptions, not smallest effects of interest.

The previous four-row AIOE mapping decomposition is retained only as evidence
about its signed historical contract, not current outcome evidence. This run does not attribute a naive
exact-code merge or any other error to a published paper whose actual code has
not been inspected.

## 4. Lambda and primitive carry-forward (W06)

The fully rebuilt 113-month architecture audit is not rerun. Its receipt,
self-check, lambda results and memberships, lambda paired comparisons,
construction identity, D/S joint results, complete covariance, centered draws,
and illustrative contrasts are hash-validated. The validator requires:

- `lambda=.5` to reproduce literal Rule-A beta scores, membership, coefficient,
  and influence within the audit's `1e-10` tolerance;
- all five lambda values and all 468 memberships per value;
- all 30 paired lambda comparisons to use common draws;
- raw and standardized D/S terms, both covariance presentations, complete
  centered draws, and three scale-reconciled illustrative contrasts; and
- zero recorded model failures.

This is a preservation and validation step, not new outcome evidence.

## 5. Required outputs and refusal rules

Required outputs are model results, paired comparisons, complete occupation
and family influence vectors, treatment memberships and scaling, a W06
carry-forward validation with source hashes, a model-failure registry, and a
sanitized execution receipt. A public validator independently reconstructs all
point and paired intervals from stored influence vectors.

The runner refuses to publish if the protected object or input hashes move, if
support order changes, if a weighted scale or quintile contract collapses, if
a model fails, if full-support beta does not reproduce, or if any output is
empty. Results are descriptive sensitivities. They do not establish realized
AI adoption, a causal AI effect, or economic equivalence.

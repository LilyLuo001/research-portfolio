# YAX V3 understanding contract

Status: Gate 0 scientific contract, written before any new V3 substantive specification is run  
Date: 2026-09-06 (Asia/Shanghai)  
Chronology: post-outcome, referee-led revision; not a preregistration  
Parent repository state: `73ce268f18cc406ff751950703ddb46f54d2b0d3`

This document records the interpretation that governs V3. It states conclusions that follow from the estimating equations and the evidence that must be produced. It is not evidence that any new V3 analysis has run.

## 1. Observed estimating data and the mean-ratio estimand

The grouped-binomial criterion is evaluated on two continuous CPS-weighted employment stocks in each occupation-month, `N_y` and `N_o`, after the survey weight has entered the stock once. Conditional on `T=N_y+N_o`, the criterion is

\[
\ell_{ot}=N_{y,ot}\log p_{ot}+N_{o,ot}\log(1-p_{ot}),\qquad
\operatorname{logit}(p_{ot})=\log\{\mu_{y,ot}/\mu_{o,ot}\}.
\]

The coefficient therefore parameterizes a contrast in ratios of conditional mean employment stocks. It is not an observed log ratio in cells with a zero stock, a literal binomial likelihood for independent persons, an individual employment probability, or an employer hiring rate. Evidence required: cell-construction audit, weight-once and stock-conservation tests, one-sided/both-zero cell accounting, and equation/table-note consistency.

## 2. Meaning and ambiguity of family-by-month conditioning

Giving each SOC two-digit family its own young-relative monthly path asks whether detailed exposure comparisons carry residual information after arbitrary family-common young-relative evolution is absorbed. A coefficient movement is sensitivity to a different conditioning restriction and estimand. It is not an additive share explained by occupational composition. Family-common AI effects and unrelated family developments are observationally absorbed by the same nuisance terms, so the design cannot distinguish them. Evidence required: matched-contract pooled/family estimates, common-draw paired difference, support/information accounting, and explicit interpretation in the paper.

## 3. Information loss does not imply attenuation

Residualizing exposure against nuisance regressors reduces the available target information and normally enlarges uncertainty. It does not determine the sign or magnitude of the remaining covariance between residualized exposure and the outcome. The coefficient may move toward zero, away from zero, or change sign. Variance inflation is therefore not an explanation for a signed coefficient movement. Evidence required: residual-information, leverage, covariance, and paired-coefficient diagnostics under identical treatment labels and support.

## 4. National Q5-Q1 identification with incomplete family tails

When most families lack both Q1 and Q5, a common national conditional coefficient can remain identified through a connected graph of partial within-family comparisons involving Q2-Q4. It imposes common quintile-profile restrictions across families. It is not an employment-weighted average of independently observed family-specific Q5-Q1 tail effects. Connectivity alone is not sufficient under separation or zero target information. Evidence required: the full 22-by-5 occupation-count and employment matrix, a comparison graph, named direct-tail families/occupations, graph rank/connectivity, full-rank target information and finite target-estimability checks, supported pairwise contrasts, and a precise statement of the imposed common profile.

## 5. Static and dynamic quantities require numerical reconciliation

The submitted static pair (about `-0.1321`, `-0.0217`) and the calendar-weighted dynamic post-functional pair (about `-0.1199`, `-0.2074`) are materially different and cannot be reconciled merely by calling one nonlinear and one linear. V3 must place them on common support and labels, compute reference-relative and reference-invariant post-minus-pre functionals, test whether the static design is nested in the dynamic design, verify the static score moment at the dynamic fit, and project fitted dynamic stocks back through the static objective. This separates normalization, temporal weights, nuisance spaces, and functional-form restrictions.

## 6. Reference periods and joint equality tests

Within the same model and estimable contrast space, changing the omitted period is a nonsingular reparameterization. An equivalent joint equality restriction and any test using the fully transformed covariance are invariant to it; the statement does not extend across changes in weights, sample, nuisance space, or target. A post average relative to an unusual two-month reference can nevertheless differ sharply from a post-minus-pre average because it is a different linear functional. Evidence required: explicit transformation matrices, full covariance transformations, rank checks, and invariant statistics before and after rebasing.

## 7. Why separate age regressions do not mechanically decompose the headline

The headline is a nonlinear, jointly estimated contrast in conditional mean ratios with shared nuisance restrictions. Separate young and older regressions generally use different score equations and projections, so their coefficients need not add exactly to the headline. In a single-age model, unrestricted occupation-by-month effects are collinear with occupation exposure-by-post and absorb the target entirely. V3 will first provide exact aggregate stock identities, then label any separately estimated age models as companion estimands with feasible nuisance spaces rather than forcing an exact coefficient split.

## 8. One-sided zero cells versus finite fixed-effect estimates

A cell with positive total stock and one zero age stock has a finite contribution to the grouped-binomial criterion and should not be discarded. In a saturated group, however, all successes or all failures can drive a fixed effect to positive or negative infinity. Thus valid cell contributions do not establish existence of a finite joint optimum or finite nuisance estimates. Evidence required: family-month boundary counts, separation/existence checks, design rank and graph checks, profiled or alternative same-objective solver benchmarks, gradients, fitted means, and explicit treatment of any extended-real nuisance solution.

## 9. Simulation truth must be defined for each fitted target

Setting a structural AI effect to zero in a data-generating process does not imply that a misspecified pooled projection, a differently conditioned projection, or their difference equals zero. Other generated dependence or composition terms can project onto exposure. Size must be evaluated around each design's population or pseudo-true target. V3 will distinguish structural-null, projection-null, bias, coverage, confounding, and estimand mismatch and will not label rejection of a nonzero pseudo-true target as size distortion.

## 10. Distinct sources of uncertainty cannot be added mechanically

Household/sample-unit resampling concerns repeated CPS sampling conditional on released weights; occupation and family wild scores concern economic-shock dependence; regenerated treatments add first-stage construction variation; mapping sensitivity changes routed stocks and possibly labels. These targets overlap and are not orthogonal by default, so their variance estimates cannot simply be summed. Evidence required: a declared stochastic target for every interval, resampling-unit and held-fixed-object inventory, shared-draw covariance checks, and either a derived non-overlapping combination or separate reporting.

## 11. Collinearity and omitted-confounder sensitivity

Collinearity reduces residual variation and inflates uncertainty but cannot by itself explain why a coefficient moves in a particular signed direction. That movement depends on the joint outcome covariance structure. Likewise, linear Oster-style formulas rely on linear-model variance decompositions; inserting a grouped-binomial pseudo-R-squared without a derivation is invalid. V3 will report the regressor-level exposure/computer-use correlation, the computer-use coefficient and scale, the sampling covariance of the estimated AI and computer-use coefficients, residual information, and a formal sensitivity only if its assumptions and target are established. Otherwise it will record a reasoned inapplicability disposition rather than fabricate a bound.

## 12. Enrollment and linkage restrictions induce selection

Restricting currently enrolled or nonenrolled respondents conditions on a contemporaneous state that can itself respond to cohort and labor-market conditions. `SCHLCOLL` not-in-universe is not automatically nonenrollment, and the older comparison must be restricted to a comparable question universe if a common-eligible analysis is claimed. Longitudinal linkage similarly selects on rotation eligibility, continued residence, successful match, and positive longitudinal weight; selection may have either sign. Evidence required: actual variable-universe/codebook audit, national versus employed-occupation composition summaries, link eligibility versus attrition accounting, linked/unlinked balance, and explicitly assumption-dependent sensitivity or bounds.

## 13. ACS size and observed adoption do not solve identification automatically

Larger ACS samples can reduce sampling error and sparse-cell frequency, but occupation-exposure support and the family-quintile comparison graph remain determined by occupational scores and taxonomy. ACS also changes frequency, survey design, year availability, and the 2020/2024 comparability problem. Observed adoption can remain selected, ecological, and collinear with exposure; it does not itself provide exogenous assignment. Evidence required: current official release/replicate-weight verification, an ACS support-graph comparison, and an adoption feasibility design stating unit, timing, residual variation, mapping, and uncertainty before any extension is run.

## 14. Evidence states and completion

- A specification is complete only as a versioned contract; it is not an estimate.
- Code without a successful receipt is `IMPLEMENTED_UNRUN`.
- A successful run without substantive validation is `RUN_UNVALIDATED`.
- A failed attempt is recorded with logs and is not completion.
- A missing-input result is `BLOCKED_INPUT` only after an availability/access attempt and a resumable next step are recorded.
- A compute failure is `BLOCKED_COMPUTE` only with the command, resource request, log, effect on claims, and restart path.
- A proposed inapplicability or deferral is not resolved until the required approval exists.
- A `VERIFIED` empirical row requires the immutable specification, executable code, successful empirical receipt, numerical result, validation report, manuscript/response integration, hashes, and a named review.
- A cached aggregate rebuild is not a clean microdata re-estimation.

The delivery validator checks structural evidence linkage, not econometric truth. The final report will separately state whether all requests are accounted for, core analyses are verified, all requested empirical work was executed, and the package is submission ready.

## Review status

Initial author: primary execution agent. A separate-agent cross-check within the same execution team found all fourteen questions answered and suggested three precision edits, incorporated above; this is team self-review, not independent scientific verification. Independent scientific review is not yet complete.

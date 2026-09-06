# Major-comment analysis specification

Status: post-outcome exploratory; written before the round-2 results below were produced.

The current frozen and first-round artifacts are comparison baselines, not editable inputs. Every new model must store its support, treatment assignment, weighting rule, coefficient definition, uncertainty procedure, seed or deterministic algorithm, and input/output hashes.

## A. Broad occupational composition

Estimate the repaired-calendar beta Q5--Q1 grouped-binomial model under three nested conditioning sets:

1. the current occupation-by-age, occupation-by-time, age-by-time, quintile-by-young-by-post, and Webb specification;
2. add two-digit-occupation-family by young by post interactions;
3. add two-digit-occupation-family by young by month interactions, if the target retains nonzero residual information and the estimator converges.

For each model report the target coefficient and interval, nominal occupations, residual-treatment inverse-Herfindahl count, top-five information share, and the weighted Q1/Q5 support by broad family. These models change the conditioning estimand; they are not decompositions of the baseline coefficient.

Test equality of the four Q2--Q5 post coefficients jointly. Assess monotonicity with all three adjacent inequalities using a common-draw joint procedure; do not infer monotonicity from coefficient ordering or separate significance. Refit the tail contrast on occupations classified as Q1 or Q5 under every one of the original six implementations, retaining frozen classifications and disclosing the smaller target population.

## B. Influence and recovery-sensitive reference groups

Using the pre-existing absolute leave-one-occupation-out ranking, refit after jointly deleting the top 5, 10, and 20 occupations. Preserve the baseline treatment classifications for the first panel; separately label any recomputed-cut panel. Because the deletion ranking uses outcomes, call this an influence stress test rather than conventional robustness.

Construct a transparent down-weighting sensitivity that caps occupation contributions according to a declared rule that does not use coefficient sign. Report exactly what is capped: survey stock, objective contribution, or occupation score contribution. Do not describe joint deletion movements as additive shares of the baseline.

Run separately defined food-service and in-person-service exclusions using detailed occupation codes and, where defensible, industry codes. Do not call the bundled IND1990 leisure/hospitality definition clean. The interpretation branch is:

- large attenuation under broad-family controls or joint deletions: recenter the paper on broad occupational composition and the Q1 recovery reference;
- a persistent within-family coefficient: retain a detailed-score association, while still withholding causal and AI-specific language absent the time-placebo evidence.

## C. Precision and time dependence

Use the canonical primary draw set for the canonical primary interval. Other common-draw sets may be used for paired differences but must be labeled paired-analysis intervals rather than alternative primary intervals.

For each primary or paired comparison, report estimate, SE, 95-percent interval, and normal-theory 80-percent MDE, `(1.96 + 0.8416) * SE`. The MDE is a precision description, not a smallest effect of interest or an equivalence bound.

Report unweighted respondent-count distributions by occupation-month-age cell and boundary-cell shares. Refit after quarterly aggregation, stating how quarter fixed effects and the post transition are constructed. Implement a time-dependence sensitivity that preserves within-occupation time paths, preferably an occupation block/bootstrap or a time-series-robust occupation-score covariance. It must be distinguished from CPS design-based replicate-weight inference.

For pseudo-breaks, never contaminate a purported pre-AI null with the actual post-2022 period. The present extract begins in 2017. Therefore either (i) restrict to feasible fully pre-2020 placebo windows and state that 2015--2016 cannot be evaluated, or (ii) obtain earlier microdata before claiming the referee's complete 2015--2019 distribution. Store the exact months and support for every pseudo-break.

Re-run the historical precision simulation with a contemporaneous cross-occupation common component only if the original simulator can preserve the target estimand and calibration. Report the fraction of the realized/prospective gap closed by this addition, but do not claim a unique explanation.

## D. Architecture dependence and comparison targets

Compute the employment-weighted eigenvalue spectrum of the six standardized original scores on literal common support. Report cumulative explained variance without treating principal components as new exposure constructs.

Create a candidate-architecture census with source, primitive, outcome-independent admission criteria, and pass/fail reason. Implement the Brynjolfsson--Chandar--Chen exposure grouping in CPS only to the extent that its published rule is reproducible. Distinguish their primary Eloundou beta score and top-two-versus-bottom-three grouping from their proprietary title mapping, ADP outcome, hiring margin, and normalization.

## E. Writing constraints during this round

- Do not write that smaller external estimates establish architecture heterogeneity when paired intervals include zero.
- Do not use a permutation mean as a formal percentage decomposition.
- Do not call an outcome-ranked deletion a causal contribution.
- Use “alternative comparison” rather than “re-referencing” when Q5--Q1 is replaced by Q5--Q2 or Q5--Q4.
- Promote the repaired calendar to the substantive descriptive baseline while retaining the frozen result as the chronology benchmark.
- Put primitive D/S and representative two-score models before the F/G rotation; keep F/G supplementary unless new evidence supplies an independent economic interpretation.

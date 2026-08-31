# Online Appendix: Measurement Architecture and Early-Career Employment

This appendix distinguishes the frozen confirmatory analysis from analyses requested after outcome access. The confirmatory result set remains exactly the one sealed at `v1.1-confirmatory-results`. Every post-outcome result below is labelled supplementary and is absent from the confirmatory ledger.

## A. Exposure construction and occupational harmonization

The confirmatory design compares three AIOE aggregations with Eloundou alpha, beta, and broad exposure. Alpha counts E1 tasks; beta counts E1 plus one-half of E2; broad exposure counts E1 plus E2. Each native SOC score is mapped to Census 2018 occupations. Pre-2020 CPS occupations are bridged from Census 2010 using official conversion rates.

Rule A, the primary strict-support rule, requires complete mapped exposure mass and covers 88.70% of eligible employment. Rule B imputes within documented siblings; Rule C renormalizes scored components only when at least 95% of mapped mass is observed. These rules define different target populations and are therefore reported separately.

The four-row mapping decomposition holds the coefficient scale and Webb conditioning fixed. Correcting exposure on original support moves the coefficient from -0.01885 to -0.01920; expanding support moves it to -0.03156; excluding computer and mathematical occupations leaves -0.02940. The main mapping consequence is composition rather than score correction among already matched occupations.

## B. Confirmatory Test A: occupational content

**Analysis status: CONFIRMATORY — FROZEN v1.1.**

The six-by-eight matrix reports employment-weighted Pearson correlations with cognitive ability, manual and physical ability, routine-task intensity, required education, log wages, teleworkability, STEM share, and computer use. The original joint projections use all eight characteristics. Because AIOE and four correlates draw on O*NET, the original 95%–97% AIOE fit is not interpreted as validation against a true AI-exposure criterion.

### B.1 Source-split audit

**Analysis status: POST-OUTCOME SUPPLEMENTARY — NOT PART OF CONFIRMATORY v1.1.**

The sample is fixed at 348 occupations. Construction-linked correlates are cognitive ability, manual and physical ability, required education, and O*NET computer use. The less construction-linked set is Autor-Dorn RTI, OEWS wages, Dingel-Neiman teleworkability, and OEWS STEM share. AIOE R-squared is 0.945–0.966 on the linked set and 0.637–0.671 on the less-linked set. Corresponding R-squared values are 0.272 for alpha, 0.428 for beta, and 0.479 for broad exposure. The split weakens the original AIOE level but preserves the cross-family occupational-content contrast.

## C. Confirmatory Test B: continuous residual-treatment support

**Analysis status: CONFIRMATORY DESIGN DIAGNOSTIC — FROZEN BEFORE OUTCOME ACCESS.**

For AI exposure X, computerization C, and preperiod employment weight w, the diagnostic estimates a weighted projection and forms residual exposure x-tilde. Occupation shares are

\[
s_o=\frac{w_o\widetilde X_o^2}{\sum_j w_j\widetilde X_j^2},
\qquad
N_{eff}=\frac{1}{\sum_o s_o^2}.
\]

Across 30 pre-specified AI-by-computerization architectures, effective support ranges from 11.9 to 84.5 occupations; top-five shares range from 15.0% to 46.6%. This is an architecture-level support diagnostic. It is not regression leverage, realized coefficient influence, or the exact information decomposition of the categorical headline estimator.

## D. Exact headline conditional-information support

**Analysis status: POST-OUTCOME SUPPLEMENTARY — NOT PART OF CONFIRMATORY v1.1.**

The headline models were refit without changing their specifications. After absorbing the fixed effects under fitted quasi-likelihood information weights W, the target Q5 column is partialled against the other absorbed slopes:

\[
z=R_t-R_{-t}(R_{-t}'WR_{-t})^{-1}R_{-t}'WR_t.
\]

Occupation conditional information is

\[
H_o=\sum_{i\in o}W_i z_i^2,
\qquad
q_o=H_o/\sum_jH_j.
\]

The occupation contributions reproduce the target Schur complement to numerical precision. Across all 12 headline models, inverse-Herfindahl effective information ranges from 42.9 to 71.1 occupations and top-five shares from 15.8% to 24.9%.

For the four Rule-A architectures, rank correlations between continuous and headline shares are 0.71–0.74. Numerical levels and leading occupations are not interchangeable. Alpha/Webb moves from 17.4 continuous effective occupations to 56.1 headline effective-information occupations and shares only one of its top five occupations. Alpha/O*NET moves from 31.1 to 71.1 and shares none. The continuous diagnostic describes residual treatment architecture; the headline decomposition describes fitted conditional curvature for the reported coefficient. Neither is a realized influence, sign attribution, or leave-one-occupation-out sensitivity measure.

## E. Headline estimates and inference

**Analysis status: CONFIRMATORY — FROZEN v1.1.**

Each exposure measure forms its own model-period-employment-weighted quintiles over the 108 static estimation months. All 12 alpha/beta Q5-versus-Q1 coefficients are negative, ranging from -0.0971 to -0.2085 log points. The strict-support beta/Webb estimate is -0.1311 with cluster-robust SE 0.0444, one-step wild-score 95% interval [-0.2170, -0.0451], and p = .003. It implies that the young employment stock evolved 12.3% less favorably relative to the older-worker stock in Q5 than in Q1 over January 2023–July 2026.

### E.1 One-step wild-score algorithm

The grouped-binomial quasi-likelihood representation yields information weights W=Np(1-p). The slope matrix is absorbed against occupation and month effects under W. Occupation scores are summed within cluster, mapped through inverse information, and multiplied by one Rademacher sign per occupation in each of 999 draws. Pseudo-outcomes are not perturbed; the null is not imposed; and PPML and fixed effects are not re-estimated in each draw. The analytic occupation-cluster standard error is the fixed studentizer. P-values use the finite-sample correction (1 + exceedances)/1000. Confidence intervals use the 95th higher empirical quantile of the absolute studentized shift.

### E.2 Grouped-binomial quasi-likelihood representation

Let \(Y_{o1t}\) and \(Y_{o0t}\) denote the survey-weighted employment stocks for young and older workers, and let \(N_{ot}=Y_{o1t}+Y_{o0t}\). In the PPML mean model, occupation-by-month fixed effects give

\[
\mu_{oat}=\exp\{\delta_{ot}+\eta_{oat}(\theta)\},
\]

where \(\eta_{oat}(\theta)\) contains the occupation-by-age and age-by-month effects and the exposure interactions. Profiling \(\delta_{ot}\) from the two age-group score equations imposes \(\mu_{o1t}+\mu_{o0t}=N_{ot}\). Hence

\[
\mu_{o1t}=N_{ot}p_{ot},\qquad
p_{ot}=\frac{\exp\{\eta_{o1t}(\theta)\}}
{\exp\{\eta_{o1t}(\theta)\}+\exp\{\eta_{o0t}(\theta)\}}.
\]

The profiled slope score is

\[
\sum_{o,t}X_{ot}\left(Y_{o1t}-N_{ot}p_{ot}\right)=0,
\]

with expected curvature \(\sum_{o,t}N_{ot}p_{ot}(1-p_{ot})X_{ot}X_{ot}'\), after the remaining fixed effects are absorbed. This has the score and objective structure of grouped-binomial logit. It is used as a quasi-likelihood representation of the PPML estimating equations. The CPS stocks and totals are noninteger survey-weighted quantities; the representation does not assert literal binomial sampling or independent Bernoulli trials.

## F. Literal support alignment across six measures

**Analysis status: POST-OUTCOME SUPPLEMENTARY — NOT PART OF CONFIRMATORY v1.1.**

The native Rule-A/Webb support sets contain 495, 484, 485, 468, 468, and 468 occupations and are not identical. The single six-way intersection contains 444 occupations, covers 83.14% of model-period employment, and has SHA-256 `1e184b27678b7978d4b15e618db5b44f44b5e9ec1b50b69b53093ec62e0ce462`. All six common-support Q5–Q1 coefficients are negative, from -0.07386 to -0.14652. Five one-step wild-score intervals exclude zero; AIOE administrative equal has CI [-0.14915, 0.00143], p=.057. Each measure forms its own quintiles within the identical occupation set.

The paired beta-alpha comparison applies the same sign to each estimator's occupation contribution, preserving covariance. The paired difference is -0.03240, SE 0.03697, 95% interval [-0.10235, 0.03755], p = .403. The design does not detect a difference and does not establish economic equivalence.

The ex-ante paired 80% MDE is 0.03272 on the log-coefficient-difference scale. Its optional multiplicative translation is 3.326%. It is not an additive percentage-point threshold.

## G. Computerization and remotability

**Analysis status for main rows: CONFIRMATORY — FROZEN v1.1.**

Webb was fixed as primary before outcome access because it is a predetermined software-patent-to-task measure from a framework separating software, robots, and AI. It is not uniquely correct. Across Webb, two O*NET computer-use variables, RTI, and Frey-Osborne, strict-support beta estimates remain negative but range from -0.1001 to -0.2085.

The continuous beta coefficient changes from -0.03814 in the AI-only model to -0.03718 with Webb and remotability. This does not show that remote work is irrelevant, because Dingel-Neiman measures occupational feasibility rather than realized individual telework.

### G.1 Remotability interaction

**Analysis status: POST-OUTCOME SUPPLEMENTARY — NOT PART OF CONFIRMATORY v1.1.**

Exactly one continuous Rule-A beta/Webb/remotability interaction model was estimated. The AI-by-remotability coefficient is 0.00704, cluster-robust SE 0.01617, one-step wild-score 95% interval [-0.02471, 0.03880], p = .663. The design does not detect heterogeneity by occupational remotability; the interval does not establish homogeneity.

## H. Dynamics and pretrend assessment

**Analysis status for event study, placebo, and post-2025 split: CONFIRMATORY — FROZEN v1.1.**

The event study uses October 2022 as the reference month. The 2017–2019 placebo is 0.00142, 95% interval [-0.02040, 0.02324], p = .894. Six of 43 event/reference-era pointwise intervals exclude zero, concentrated in November–December 2023 and April–July 2026. The path is not a sharp January 2023 step. The frozen later-window difference is -0.01722 with p = .127; the design does not detect post-2025 acceleration.

### H.1 Legacy continuous joint pretrend test

**Analysis status: POST-OUTCOME SUPPLEMENTARY — NOT PART OF CONFIRMATORY v1.1.**

A maximum-absolute-t test covers all 65 non-reference pre-event coefficients using 999 common occupation-cluster multipliers. The observed maximum absolute t-statistic is 1.890; the bootstrap p-value is .636; the simultaneous 95% critical value is 3.075; and zero of 65 simultaneous intervals excludes zero. The test does not reject the joint null, but it does not prove parallel trends.

### H.2 Categorical headline event study

**Analysis status: POST-OUTCOME SUPPLEMENTARY — NOT PART OF CONFIRMATORY v1.1.**

The headline-aligned event study uses the beta/Rule-A/Webb occupation support and static Q1–Q5 classification. Q1 is omitted; Q2–Q5 enter month by month; Webb enters as a standardized month-specific interaction; October 2022 is the reference; and December 2022 is retained as the transition month. The joint max-|t| test of 65 Q5-versus-Q1 pre coefficients yields max-|t| 1.502, p=.929, simultaneous critical value 3.027, and zero simultaneous intervals excluding zero. The test does not prove parallel trends.

Forty of 42 post coefficients are negative. Eight negative pointwise intervals exclude zero: October–December 2023, December 2025, and April–July 2026. None is significantly positive. The path is intermittent and late-concentrated rather than an immediate January 2023 step.

## I. CPS survey uncertainty feasibility

**Analysis status: POST-OUTCOME SUPPLEMENTARY FEASIBILITY AUDIT — NOT PART OF CONFIRMATORY v1.1.**

The extract contains the final person weight, household identifiers, a person-panel identifier, and rotation group. It does not contain public strata, PSU, or replicate weights sufficient to reconstruct design-consistent first-stage uncertainty. No ad hoc household, person, or rotation bootstrap was executed. Occupation-cluster intervals condition on realized survey-weighted cells and do not separately propagate CPS sampling or calibration-weight uncertainty.

## J. Audit boundary

The original confirmatory result JSON has SHA-256 `4f7df33a...831`; the original confirmatory result ledger has SHA-256 `e900adb7...66b`. The supplementary analyses have their own declaration commit, analysis ledger, labels, stored distributions or sufficient representations, and artifact hashes. They are not appended to or used to rewrite the confirmatory result ledger.

## K. Quintile-weight temporal-window audit

**Analysis status: POST-OUTCOME SUPPLEMENTARY QUINTILE-WEIGHT SENSITIVITY — NOT PART OF CONFIRMATORY v1.1.**

The design freeze defined Q5–Q1 through employment-weighted exposure quintiles on each scenario's estimation support, kept tied scores together, and entered Q2–Q4 separately. It did not specify the calendar window supplying the production employment weights. The pre-outcome power engines used 2017-01–2022-11 cells because protected post-period outcomes were unavailable. The production helper, written after the tag, instead summed young-plus-older stocks over all 108 static estimation months from January 2017 through July 2026, excluding December 2022 and with October 2025 absent. The design verdict is therefore freeze ambiguity, not an explicit pre-period requirement or an explicit full-period rule.

The underlying exposure score is predetermined. The narrower concern is that full-period weighting makes the categorical map depend partly on realized post-treatment employment composition. One sensitivity therefore changes only the AI-quintile classification weights to the 66 available January 2017–November 2022 months. The primary 468-occupation support, exposure values, outcome cells, Webb control and its original standardization, fixed effects, estimator, post period, and inference remain unchanged.

The Q80 cutoff is unchanged at 0.537037, and the 91 Q5 occupations are identical (Jaccard 1.000). Q1 changes from 133 to 129 occupations (Jaccard 0.970). Nine occupations change any quintile. The pre-period-weighted coefficient is -0.12851, analytic occupation-cluster SE 0.04461, one-step wild-score 95% CI [-0.21599, -0.04103], p=.003. Relative to the historical -0.13107 estimate, the descriptive difference is +0.00257 log points. The pre-period-weighted exponential translation is -12.06% for the Q5-versus-Q1 young-relative employment-stock contrast.

On the fixed 444-occupation V4 intersection, all six pre-period-weighted estimates remain negative. Absolute coefficient changes are at most 0.00630 log points; Q5 Jaccard overlap ranges from 0.976 to 1.000. Five intervals exclude zero, while AIOE administrative equal remains marginal (p=.056).

The result is W1: weighting is immaterial in this application. It does not make either window retrospectively pre-specified. Because primary Q5 membership is identical, Q1 overlap is high, and the coefficient moves by only 0.00257 log points, no additional categorical event study is warranted.

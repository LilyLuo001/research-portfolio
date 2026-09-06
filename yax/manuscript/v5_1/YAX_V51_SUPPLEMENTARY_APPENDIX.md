# Online appendix to “What Is AI Exposure?”

## A. Six-measure correlation matrices

All entries use the frozen 463-occupation treatment-side reference file and pre-period employment weights. Weighted “Spearman” is the weighted Pearson correlation of deterministic average ranks.

### A1. Employment-weighted Pearson correlation

| | AIOE admin | AIOE ability | AIOE source | Alpha | Beta | Broad |
|---|---:|---:|---:|---:|---:|---:|
| AIOE admin | 1.000 | 0.984 | 0.996 | 0.295 | 0.833 | 0.890 |
| AIOE ability | 0.984 | 1.000 | 0.981 | 0.276 | 0.821 | 0.883 |
| AIOE source | 0.996 | 0.981 | 1.000 | 0.293 | 0.832 | 0.890 |
| Alpha | 0.295 | 0.276 | 0.293 | 1.000 | 0.643 | 0.346 |
| Beta | 0.833 | 0.821 | 0.832 | 0.643 | 1.000 | 0.941 |
| Broad | 0.890 | 0.883 | 0.890 | 0.346 | 0.941 | 1.000 |

### A2. Employment-weighted average-rank correlation

| | AIOE admin | AIOE ability | AIOE source | Alpha | Beta | Broad |
|---|---:|---:|---:|---:|---:|---:|
| AIOE admin | 1.000 | 0.987 | 0.993 | 0.274 | 0.844 | 0.874 |
| AIOE ability | 0.987 | 1.000 | 0.982 | 0.258 | 0.845 | 0.880 |
| AIOE source | 0.993 | 0.982 | 1.000 | 0.269 | 0.843 | 0.874 |
| Alpha | 0.274 | 0.258 | 0.269 | 1.000 | 0.567 | 0.369 |
| Beta | 0.844 | 0.845 | 0.843 | 0.567 | 1.000 | 0.961 |
| Broad | 0.874 | 0.880 | 0.874 | 0.369 | 0.961 | 1.000 |

## B. Full quintile profile and common-support stock results

The primary beta/Webb profile relative to Q1 is Q2 -0.08547, Q3 -0.04779, Q4 -0.09703, and Q5 -0.13107. Because Q3 is less negative than Q2 and its interval spans zero, the profile is not described as a dose response.

On literal 444-occupation support, the coefficients are -0.07386 (AIOE administrative), -0.10285 (AIOE ability), -0.10210 (AIOE source weighted), -0.10132 (alpha), -0.12896 (beta), and -0.14652 (broad). Common-multiplier one-sided simultaneous inference leaves the administrative-AIOE upper bound above zero.

## C. Paired precision

The beta-minus-alpha coefficient is -0.03240, paired SE 0.03697, 95% interval [-0.10235, 0.03755], and `p=.403`. The outcome-blind paired MDE of 0.03272 log points came from 999 synthetic donor/Rademacher draws on 468 occupations, 66 pre months, and 42 synthetic post months. Its prospective SE was 0.01167. The 3.17-fold realized-to-prospective SE ratio produces classification MDE-R2: the calculation is reproducible but remains appendix-only design history. No ex-post MDE replaces it.

## D. Longitudinal estimands

All longitudinal models use valid exact adjacent-month `CPSIDV` links, origin age, official origin `LNKFW1MWT`, January 2017–November 2022 as pre, January 2023 forward as post, December 2022 as transition, and no MISH 4→5 gap. Origin occupations before 2020 are route-expanded through the official Census bridge. Webb and beta treatment definitions are fixed from pre-period weights.

### D1. Employment exit

The risk set is employed origins. The outcome equals one when the respondent is nonemployed at `t+1`. Treatment is assigned from the origin occupation. Weighted event count `X_oat` and weighted risk `R_oat` enter a grouped conditional-Poisson rate model,

\[
E[X_{oat}]=R_{oat}\exp(\alpha_{oa}+\delta_{ot}+\lambda_{at}
+\sum_{q=2}^5\beta_q Q_{oq}Young_aPost_t+\theta Webb_oYoung_aPost_t).
\]

Conditioning on the occupation-month event total yields a grouped-binomial likelihood with offset `log(R_young/R_older)`. The target is the post change in the young-versus-older Q5/Q1 exit-rate ratio. It is not restricted to layoffs.

### D2. Occupational outflow

The risk set is employed origins linked to an employed destination with valid harmonized occupations. The outcome is a different occupation at `t+1`; exposure remains assigned from the origin. The estimator, risk offset, interactions, weight, and occupation-cluster wild-score inference match exit. December 2019 origins are excluded. The target is a relative change in the Q5/Q1 switch rate, not an employment exit.

The single persistence sensitivity requires a legitimate third adjacent observation and A→B→B. It conditions on observing the third interview and does not correct every coding error.

### D3. Entry destination

The origin risk set is nonemployed respondents linked to employment at `t+1`. No origin occupation or exposure is assigned. Destination occupations define exposure and weighted destination counts. The same saturated mean model is estimated without a risk offset; conditioning on destination-month totals produces a grouped-binomial computational form. The target is the post change in the young-versus-older allocation of entries toward Q5 rather than Q1. It is not an employment-finding probability and is not directly commensurate with the two origin-risk rate estimands.

The three flow coefficients—exit 0.1195, outflow 0.0107, and entry destination -0.0888—have intervals that include zero. They are separate conditional parameters and do not sum to the stock coefficient.

## E. Occupational coding

The link sample uses origins in MISH 1, 2, 3, 5, 6, and 7 with an exact next-month destination at MISH+1. CPS dependent interviewing imports prior industry and occupation information in eligible continuing interviews, but it is not used in MISH 5 and does not eliminate coding error. The design excludes the long rotation gap, omits December 2019→January 2020 from occupation-dependent results, reports a 9.865% immediate reversal rate, and repeats the organizing decomposition on persistent A→B→B switches.

## F. Reallocation agreement and hard benchmark

The full 15-pair raw and κ table is `YAX_V51_KAPPA_AGREEMENT.csv`. Official-weight Cohen κ ranges from 0.125 to 0.932; standard unweighted Fleiss κ is 0.501. These supplement, rather than replace, the raw 53.28% any-opposite-sign rate.

Broad benchmark families are first-two-digit SOC 2018 major groups assigned through the Census-2018 bridge. The 23 numeric groups form age×month×origin-family×destination-family strata. Within each stratum, the benchmark preserves official-weight detailed origin and destination marginals and destroys the observed detailed pairing. It uses 200,000 pseudo-units and 999 fixed-seed draws. The primary benchmark contains 30,170 strata, 84,192 detailed joint cells, and 98.31% of switch weight. Its 52.32% mean leaves a 0.96-point realized excess.

Conflict falls from 94.59% to 19.06% across frozen quintiles of absolute consensus movement. This remains an organizing decomposition only: because the consensus is built from the families whose signs enter conflict, part of the pattern is algebraically expected.

## G. Joint consensus/disagreement model

The exact plan is `YAX_V51_FG_JOINT_MODEL_PLAN.md`. On the literal 444-occupation support, `F`, `G`, and Webb are each standardized once with model-period stock weights and enter jointly as continuous young×post slopes. There are 108 static-model months. Common 999-draw occupation multipliers use seed `2026090501`.

`F=-0.04036` (CI [-0.06925, -0.01147]) and `G=+0.03089` (CI [0.00180, 0.05999]). Centered covariance is -0.00009825 and the joint max-|t| `p` is .008. This is the only new labor-outcome specification in V5.1.

## H. Dependence and design limits

The occupation×calendar-month inclusion–exclusion covariance leaves the primary and common-support inferential pattern unchanged. It is a model-based dependence sensitivity, not a survey correction. The public extract lacks the strata, PSU, and replicate-weight structure needed to reconstruct full CPS design-based variance for these custom cells.

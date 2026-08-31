# YAX Scope Expansion Phase 1 Decision Memo

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

## Decision

**AGE-A with a precision caveat; FLOW-B (strong, adjacent-month only); PATH 1.**

Proceed to a separately pre-declared CPS flow decomposition. Do not run it from
this Phase-1 state. The age result deserves eventual selective manuscript
inclusion, but the paper should not be reframed or rewritten until the owner
reviews this memo. BTOS/adoption validation should remain deferred while the
more direct CPS flow extension is frozen and tested.

The economic fact is narrower than a smooth experience gradient: the negative
relative post-2022 profile is concentrated at ages 18–25 and is most negative
at ages 22–25; it does not extend to ages 26–30. That makes the inherited
22–25 cutoff economically informative rather than arbitrary, but it does not
identify a junior-substitution mechanism.

## Age profile

One jointly estimated grouped-multinomial conditional-PPML model uses ages
51–65 as the reference. It contains occupation×age, occupation×month, and
age×month fixed effects, age-specific beta Q2–Q5×post interactions, and
age-specific Webb×post controls. The sample contains the primary 468 Rule-A
beta/Webb occupations and 108 static months; December 2022 is excluded and
post begins in January 2023. Beta quintiles use January 2017–November 2022
ages-22–65 employment weights. Q5 membership is identical to the historical
primary classification.

| age group | Q5-vs-Q1 post coefficient relative to 51–65 | cluster SE | one-step wild-score 95% CI | p | relative % |
|---|---:|---:|---:|---:|---:|
| 18–21 | -0.07445 | 0.06406 | [-0.19236, 0.04347] | .228 | -7.17% |
| **22–25** | **-0.09957** | 0.05295 | **[-0.20103, 0.00190]** | **.052** | **-9.48%** |
| 26–30 | 0.01502 | 0.03440 | [-0.05040, 0.08044] | .648 | 1.51% |
| 31–40 | 0.06449 | 0.02739 | [0.01419, 0.11479] | .016 | 6.66% |
| 41–50 | 0.03441 | 0.02334 | [-0.00911, 0.07793] | .126 | 3.50% |
| 51–65 | 0 (normalization) | — | — | — | 0% |

The original confirmatory estimate, -0.13107 for ages 22–25 versus pooled ages
26–65, appears in the figure only as a separately labelled benchmark. It is a
different comparison group and is not numerically pooled with the exploratory
model.

### Answers to the four age questions

1. **Is 22–25 uniquely negative?** It is the most negative point estimate, but
   not the only negative one: 18–21 has the same sign and less precision. The
   22–25 pointwise interval narrowly includes zero (p=.052), so “uniquely” is
   too strong as an inferential claim.
2. **Is the profile monotonic?** No. The negative gradient disappears at
   26–30, while 31–40 and 41–50 are positive relative to 51–65. There is sharp
   attenuation after age 25, not a smooth monotonic experience curve.
3. **Do 18–21 and 22–25 behave similarly?** Directionally yes (-7.2% versus
   -9.5%), but 18–21 is imprecise and is especially exposed to schooling and
   labor-force-entry composition.
4. **Does the negative pattern extend to 26–30?** No. The point estimate is
   0.0150, with an interval spanning -0.0504 to 0.0804.

**AGE-A rationale.** Ages 22–25 are clearly among the most negative groups and
the negative pattern attenuates completely after age 25. The preset AGE-A
shape criterion is therefore the closest fit. The caveat is important: this
is a concentrated youth profile, not a statistically clean monotonic gradient,
and the 22–25 pointwise p-value is .052. AGE-B is rejected because 26–30 is not
similarly negative; AGE-C and AGE-D contradict the observed ordering.

## CPS longitudinal feasibility

The actual extract contains `CPSIDV`, `CPSIDP`, `CPSID`, `SERIAL`, `PERNUM`,
`MISH`, interview month/year, age, employment status, occupation, industry,
class of worker, and cross-sectional weights. `CPSIDV` is unique within every
month in the basic extract and has no zero IDs, so it is the preferred key.
The extract contains neither an official longitudinal link weight nor a
same-employer identifier.

The legitimate structures are kept separate:

| structure/group | eligible origins | matched | match rate |
|---|---:|---:|---:|
| adjacent month, overall | 4,862,216 | 4,402,802 | 90.55% |
| adjacent month, ages 22–25 | 359,866 | **313,171** | **87.02%** |
| adjacent month, ages 26–65 | 4,141,096 | 3,772,322 | 91.09% |
| adjacent month, pre-2023 | 3,151,801 | 2,879,859 | 91.37% |
| adjacent month, post-2023 | 1,710,415 | 1,522,943 | 89.04% |
| MISH 4→5 after gap, overall | 774,257 | 570,429 | 73.67% |
| MISH 4→5 after gap, ages 22–25 | 57,786 | 34,134 | 59.07% |

Post-2023 adjacent matching is 2.33 percentage points below pre-2023 matching.
Young-worker matching is 4.07 points below ages 26–65. Match rates also rise
from 89.36% in beta Q1 to 91.59% in Q5. These are material observable selection
patterns and must accompany any future coefficient.

### Available adjacent-month event samples

| prospective margin | all events | age-22–25 events | pre events | post events | primary-support occupation coverage |
|---|---:|---:|---:|---:|---:|
| employment exit | 113,251 | 11,982 | 74,615 | 37,528 | 463 / 468 |
| occupational switch out | 205,540 | 19,261 | 131,621 | 72,042 | 465 / 468 |
| entry from nonemployment | 108,131 | 12,461 | 72,605 | 34,693 | 462 / 468 |
| switch into occupation | 205,540 | 19,261 | 131,621 | 72,042 | 465 / 468 |

The event counts are ample, including Q1/Q5 young transitions. They are not
power calculations and no AI-flow coefficient was estimated.

### Switching noise and weights

Among 3,090,795 matched employed-to-employed pairs, raw `OCC` changes 6.89%,
`OCC2010` changes 6.57%, and the feasibility-only modal Census-2018 code
changes 6.66%. Among first switches observable in three consecutive months,
9.86% immediately reverse A→B→A. Only 26.26% of modal switches stay within the
same SOC major group. The raw-code change rate jumps to 30.85% across
2019-12→2020-01; OCC2010 reduces it to 7.90%, while modal Census-2018 remains
11.49% versus 6.61% in other months. Switching is usable only with a declared
harmonized definition, exclusion/sensitivity for the taxonomy boundary, and
explicit coding-noise limitations.

`WTFINL` is cross-sectional and `EARNWT` is an earnings weight; neither is an
official longitudinal weight. Phase 1 uses them only for sample-size
diagnostics. Any next stage must target the linked sample explicitly, report
unweighted estimates as primary, and present cross-sectional-weight and
attrition adjustments only as clearly labelled sensitivities.

**FLOW-B rationale.** Validated IDs, 90.6% adjacent matching, 313,171 matched
young origins, and five-figure young event counts make a narrow adjacent-month
analysis credible. The missing longitudinal weight, lower young/post/Q1 match
rates, 9.9% immediate reversals, and taxonomy-boundary spike prevent FLOW-A.
Exit is the cleanest margin; entry destination allocation is feasible but has
a different estimand; switching is feasible only with the restrictions in
`YAX_FUTURE_FLOW_ANALYSIS_PLAN.md`. Long-gap links should not be used.

## Joint recommendation: PATH 1

AGE-A plus strong FLOW-B meets PATH 1. The next research question is:

> Where does the concentrated under-25 employment-stock gradient come from—entry, exit, or occupational switching?

Actual CPS flow regressions should proceed only after the future plan is
reviewed, narrowed if necessary, committed, and frozen. The age figure is worth
eventual manuscript inclusion because it shows the 22–25 cutoff is not simply
masking an equally negative 26–30 result. It should remain descriptive
heterogeneity, not evidence that AI substitutes for junior workers.

## Publication-ceiling assessment

- **Labour Economics:** Phase 1 improves fit materially. A disciplined flow
  decomposition with transparent linkage limits could support a strong
  submission; the age profile alone is useful but not ceiling-changing.
- **ILR Review:** Also plausible, particularly if entry/exit evidence is tied
  carefully to early-career labor-market institutions and the measurement
  contribution remains central.
- **ReStat:** Not raised by Phase 1 alone. A new, robust flow fact plus a more
  compelling source of identifying variation would be needed.
- **JHR:** The flow extension could make the paper more relevant, but the
  current observational exposure design and lack of longitudinal weights still
  constrain the ceiling.
- **Journal of Labor Economics:** Not supported by the present evidence. The
  age profile and feasibility audit do not provide a causal mechanism or
  research design at that standard.

No V5 manuscript was created, and the V4.1 title, introduction, and clean
manuscript were not changed.

**No CPS flow treatment-effect regressions were executed in Phase 1.**

**No BTOS, adoption, PCA/factor, education, gender, alpha/E2, or additional-outcome analyses were executed.**

**The immutable v1.1 confirmatory results and V4.1 manuscript baseline were not altered.**


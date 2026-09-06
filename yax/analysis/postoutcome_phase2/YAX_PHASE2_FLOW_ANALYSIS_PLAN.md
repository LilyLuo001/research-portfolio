# YAX Phase 2 flow-analysis plan

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

This plan governs Phase 2 only. It does not amend the immutable v1.1 design,
confirmatory results, V4/V4.1 manuscript baseline, or Phase-1 commit
`0aefec9cf8837f33a09f4307c472ebc2ad75403a`. It must be committed before any
AI-flow coefficient is computed.

## 1. Gate and scope

Execution is authorized only if the Phase-1.5 receipt reports
`PASS_DEFENSIBLE_CPSIDV_WITH_OFFICIAL_WEIGHT`. A failed compatibility audit
ends Phase 2 before flow estimation.

The analysis uses only adjacent basic-month CPS links, occupation and
employment status, the six existing AI-exposure architectures, and Webb's
software-patent exposure. It does not use BTOS, adoption, BEA data, digital
capital, wages, hours, CPS ORG, demographic heterogeneity, PCA/factors, new
indices, alternative treatment dates, alternative young-age definitions, or
long-gap links.

## 2. Population, calendar, and links

- Young respondents are ages 22–25 at the origin interview. Older respondents
  are ages 26–65 at origin. Destination age never reclassifies the origin.
- A legitimate origin has MISH 1, 2, 3, 5, 6, or 7. The destination must be
  exactly one calendar month later, share the origin's nonzero `CPSIDV`, and
  have MISH equal to origin MISH plus one.
- MISH 4→5 eight-month returns are excluded. September→November 2025 is not
  adjacent; the missing October 2025 sample leaves September without a
  destination.
- The static pre-period is January 2017–November 2022. December 2022 is a
  transition month and is excluded from static pre/post models. Post-period
  origins begin January 2023 and end at the last origin with an observed exact
  next month.
- December 2019→January 2020 remains in employment-exit analysis because the
  outcome does not use occupation at destination. It is excluded from every
  occupational-switch, occupational-outflow, and realized-transition result.

The primary analysis weight is the origin's official `LNKFW1MWT` on a
successful CPSIDV link. Every model is repeated unweighted. Origin `WTFINL`
may be shown once as a non-longitudinal sensitivity, labelled accordingly; it
is not interpreted as a link-selection correction. No propensity weight is
constructed.

## 3. Occupation and exposure rules

The treatment taxonomy remains Census 2018. For records from 2020 onward, raw
`OCC` is the Census-2018 occupation. Before 2020, at-risk and event weights are
expanded over the existing Census-2010→2018 bridge; the published route weight
multiplies `LNKFW1MWT`. No modal route is used for a coefficient.

An occupational switch is a change between valid, nonzero harmonized
`OCC2010` codes across two employed interviews. Treatment of an incumbent is
still the origin's Census-2018 exposure, route-expanded as above. This keeps a
stable equality definition without creating a new exposure measure.

Primary exposure is Eloundou beta under Rule A strict support, with Webb as
the existing comparison technology. Beta quintiles are the exact V4.1
classifications formed from January 2017–November 2022 young-plus-older
employment weights. Before execution, the Q5 code list and its hash must equal
`YAX_V41_QUINTILE_MEMBERSHIP.csv`. Webb is standardized once on the same
primary support using pre-period at-risk employment weights.

The primary occupation support is the beta-Rule-A/Webb finite intersection
with positive pre-period at-risk weight in both age groups. The receipt must
name the number of contributing occupations and every further outcome-driven
zero-event loss; no silent common-support change is allowed.

## 4. Primary estimators (Stage 2A)

Let \(a\) be young or older, \(o\) an origin/destination occupation, and \(t\)
the origin month. Let \(Post_t\) start in January 2023. All coefficients below
are associations among validated linked CPS observations.

### 4.1 Incumbent employment exit

The risk set is employed origins. The event is employment at \(t\) followed by
nonemployment at \(t+1\); it is never called a layoff. Let \(R_{oat}\) be the
weighted risk and \(X^{exit}_{oat}\) the weighted event count. Estimate a
grouped conditional-Poisson rate model

\[
E[X^{exit}_{oat}]=R_{oat}\exp(\alpha_{oa}+\delta_{ot}+\lambda_{at}
+\sum_{q=2}^5\beta^{exit}_q Q_{oq}Young_aPost_t
+\theta^{exit}Webb_oYoung_aPost_t).
\]

With two age groups, conditioning on the occupation-month event total gives a
grouped-binomial likelihood with offset
\(\log(R_{o,young,t}/R_{o,older,t})\), occupation and month fixed effects, and
the four beta-quintile plus Webb interactions. The target is
\(\beta^{exit}_5\), a young-versus-older post change in the Q5/Q1 exit-rate
ratio.

### 4.2 Incumbent occupational outflow

The risk set is employed origins that are successfully linked to an employed
destination with valid harmonized occupation codes. The event is a different
`OCC2010` at \(t+1\). Use the same conditional-Poisson rate model and origin
exposure as for exit. Exclude December 2019 origins. The target
\(\beta^{outflow}_5\) is a Q5/Q1 relative switch-rate change.

Exactly one persistence sensitivity is allowed. A primary A→B switch is
persistent only when the respondent has another legitimate adjacent
observation and remains employed in B at \(t+2\). The sensitivity conditions
on observing that third interview, uses the first-link origin weight, and is
explicitly not claimed to correct selection into the second link. No other
persistence rule is searched.

### 4.3 Entry destination

The sample is linked nonemployed origins who are employed at \(t+1\). No
origin occupation or AI exposure is assigned. Destination counts are expanded
over bridge routes when necessary. Estimate

\[
E[C^{entry}_{oat}]=\exp(\alpha_{oa}+\delta_{ot}+\lambda_{at}
+\sum_{q=2}^5\beta^{entry}_q Q_{oq}Young_aPost_t
+\theta^{entry}Webb_oYoung_aPost_t),
\]

where \(o\) is the destination. Conditioning on each destination-month count
gives the same grouped-binomial computational form without a risk offset.
Age×month effects condition on the total entry margin by age and month. The
target \(\beta^{entry}_5\) is the post change in young-versus-older entry
allocation to Q5 rather than Q1. It is not an employment-finding probability.

Occupational inflow from another occupation is optional and may be reported
only as a clearly separate destination-allocation quantity. It is not needed
for the Stage-2A gate.

### 4.4 Inference and reporting

Use occupation-cluster sandwich inference and 999 Rademacher wild-score draws
with fixed seeds declared in the receipt. Report the coefficient in log
points, \(100[\exp(\beta)-1]\), analytic clustered SE, wild-score 95% CI and
p-value, raw events, weighted events, raw risk/entrant counts, weighted risk,
contributing occupations, and Q1/Q5 age-period composition. Report descriptive
weighted flow rates beside the models. Do not translate the three coefficients
into shares of the stock effect without a separately proved accounting
identity; none is authorized here.

## 5. Stage-2A margin gate

A stock-consistent signal requires a two-sided 95% wild-score CI excluding
zero in the following direction: positive for exit/outflow or negative for
entry. A significant coefficient in the opposite direction is retained and
treated as conflicting evidence, not relabelled.

- **FLOW-M1 (entry-dominant):** entry is the only stock-consistent signal.
- **FLOW-M2 (exit-dominant):** exit is the only stock-consistent signal.
- **FLOW-M3 (switching/reallocation-dominant):** outflow is the only
  stock-consistent signal.
- **FLOW-M4 (mixed):** at least two stock-consistent signals, or a combination
  of stock-consistent and statistically opposite signals.
- **FLOW-M5 (no clear margin):** no target CI excludes zero.

FLOW-M5 stops Stage 2B. Under M1–M3, only the named margin may be extended to
the six architectures. Under M4, extension is limited to the statistically
distinguishable margins and the decision memo must avoid naming a single
mechanism.

## 6. Stage 2B conditional architecture extension

If the gate allows it, repeat only the authorized margin under the six
existing Rule-A architectures: AIOE administrative/equal, AIOE
ability-direct, AIOE OEWS-weighted, Eloundou alpha, beta, and broad. Preserve
the link sample, months, ages, official weight, estimator, bootstrap, and
pre-period quintile construction. Report native support and one literal
six-measure common-support sensitivity. Classify the result as ARCH-MR
(dominant margin robust), ARCH-MN (mechanism non-invariant), or ARCH-MU
(imprecise/unresolved). This stage is never a search across all margins.

## 7. Stage 2C realized-transition diagnostic

This descriptive measurement test is predeclared independently of Stage-2A
significance and may run if switching quality and weight compatibility pass.
Its primary sample consists of actual adjacent employed-to-employed
`OCC2010` switches, excludes December 2019 origins, and requires finite origin
and destination exposure under all six existing architectures.

For each architecture, use the existing `occ2010_sensitivity_all_years`
route-weighted lookup—no new exposure index. Compute
\(\Delta X=X_{destination}-X_{origin}\). Compute employment-weighted percentile
ranks \(R_m\) from January 2017–November 2022 ages-22–65 employment only and
then \(\Delta R=R_m(destination)-R_m(origin)\). Post outcomes never define a
rank.

There is no invented neutral band. Exact zero is a tie; positive and negative
values determine direction. Report official-weight and unweighted:

1. all-six same-direction rate, any-tie rate, and conflict rate (at least one
   positive and one negative architecture);
2. pairwise sign agreement among non-ties and pairwise correlations of
   \(\Delta R\);
3. within-transition standard deviation and max-minus-min \(\Delta R\);
4. conflict across every ordered pair of common-support occupations versus
   conflict weighted by realized switches.

Repeat the diagnostic once using the declared persistence filter. A large
change downgrades the conclusion.

After those tables, run one comparison only: the official-weight conflict
indicator's young×post difference-in-differences (young 22–25 versus older
26–65; pre through November 2022 versus post from January 2023), with an
origin-occupation-cluster wild-score CI. Report the four underlying cell rates.
This is descriptive and not a causal AI estimate.

## 8. Fixed outputs and figures

Stage 2A writes `YAX_PHASE2_PRIMARY_BETA_FLOW_RESULTS.csv` and
`YAX_PHASE2_FLOW_MARGIN_DECISION.md`. Stage 2C writes
`YAX_PHASE2_REALIZED_TRANSITION_AGREEMENT.csv`, pairwise sign/correlation
matrices, and a persistence table. Stage 2B writes a cross-architecture table
only when authorized.

Figure A is fixed as a three-row forest plot of the beta Q5 coefficient for
exit, outflow, and entry. Figure B is fixed as the official-weight pairwise
sign-agreement heatmap. No alternative display will be selected after results.

The final decision memo returns PATH-2A, PATH-2B, PATH-2C, or PATH-2D and lists
every new outcome regression actually executed. No V5 manuscript is created.

## 9. Stop conditions

Stop before effects if the official weight cannot be used defensibly with
CPSIDV, the minimal extract does not merge exactly, or exposure-related
retention is severe. Stop switching analyses if taxonomy/coding noise dominates
the harmonized adjacent-month definition. Stop Stage 2B under FLOW-M5. Any
contradiction with frozen stock facts must first be audited for an
implementation inconsistency.

At the time this plan is committed, no Phase-2 AI-flow coefficient or realized
transition architecture result has been computed.

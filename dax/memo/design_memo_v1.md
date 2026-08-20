# Dynamic AI Exposure (DAX): pre-registered design memo v1

**Status:** v2 draft — PRIMARY DESIGN AMENDED 2026-08-18; not pre-registered

**Draft date:** 2026-08-06; amended 2026-08-18 (D1, D3, D4, F2)

**Gate:** `DAX-GATE1-memo`

**Outcome-data status:** SEALED until the signed tag `v1.0-preregistered`

This memo translates the DAX proposal and Amendment v1.1 into an executable
design. The PI approved all 17 bracketed `[PI-DECISION]` defaults and all six
non-numeric confirmations on 2026-08-06, and counter-signed four amendments on
2026-08-18 (section 11.2). They are frozen design choices, but the tag remains
prohibited until the evidence checklist, power task, independent red-team, and
rendered review are complete.

**What changed on 2026-08-18, in one paragraph.** The primary specification is
no longer a stacked event study. Executing the previous section 3.2 against
this memo's own registry left two estimable events where the power engine
requires three, and the rule was non-monotone in evidence quality. The primary
is now a continuous cumulative-dose design on the monthly index of section 2,
with no event selection; the stack survives as secondary corroboration. The
power pass bar, previously derived from the sample it judged, is now a frozen
external constant. The primary estimand is stated explicitly as an incumbent
margin, and an entrant-margin companion is registered alongside it. Five
registry rows were demoted to `pending_second_date_locator` under a rule now
enforced by the validator rather than applied by hand.

**Review status.** The independent cross-vendor red team of 2026-08-06 reviewed
the superseded discrete design. Its `CONDITIONAL_GO` does **not** transfer to
this draft, and the corresponding evidence-checklist item has been returned to
unchecked. A fresh adversarial pass over this version is required before
Gate 1.

## 0. Binding scope and feasibility conditions

The estimand concerns the U.S. occupation-level *full-task displacement
frontier*: the wage-bill share of tasks for which AI substitution becomes
privately cost-effective. It is not a net general-equilibrium employment
effect and does not treat technical feasibility as realized adoption.

The signed 2026-07-10 feasibility decision binds this memo:

1. W4 capture of accessible historical model snapshots must finish before the
   applicable 2026-10-23 and 2026-12-11 shutdown dates.
2. Retired vintages enter only through cited stand-ins, stand-in uncertainty
   enters the EIV analysis, and `gpt-4.5-preview` is excluded because no
   qualified stand-in was filed.
3. GDPval is referenced by task ID for internal research. No GDPval task text
   or derived task content enters W10a unless redistribution rights are
   clarified.

Primary task bundles, wages, and weights use 2021 O*NET/OEWS vintages. A 2019
wage baseline and annually updated O*NET bundles are robustness/decomposition
variants, not replacements for the frozen primary index.

## 1. Event registry

### 1.1 Inclusion rule

An event enters the registry only if it changes at least one of: accessible
model capability, input/output/reasoning-token price, or the set of model
snapshots available for measurement. Every date and price requires two
locators. Announcement-only events without API availability are recorded but
do not receive an exposure dose until the API-effective date.

### 1.2 Machine-readable registry and source-complete core events

The frozen registry source is `dax/memo/event_registry_v1.csv`. It records
analysis status separately from evidence status: a `candidate` is chronology,
not permission to estimate an event. `python dax/memo/validate_event_registry.py`
fails if IDs or dates are malformed, either locator is absent, sources repeat,
or an event marked `eligible` lacks verified status. The validator does not
pretend to read source content; rows marked `pending_second_date_locator`
remain ineligible until a second source independently dates API availability.

| Event ID | API-effective date | Classification | Evidence 1 | Evidence 2 | Status |
|---|---|---|---|---|---|
| `GPT4_LAUNCH` | 2023-03-14 | capability | OpenAI, [GPT-4](https://openai.com/index/gpt-4-research/) | OpenAI, [GPT-4 technical report](https://cdn.openai.com/papers/gpt-4.pdf) | date verified; price-history row pending W2 |
| `GPT4O_LAUNCH` | 2024-05-13 | capability + price | OpenAI, [Hello GPT-4o](https://openai.com/index/hello-gpt-4o/) | OpenAI, [GPT-4o product release](https://openai.com/index/gpt-4o-and-more-tools-to-chatgpt-free/) | lead price event; official release states API cost was 50% lower than GPT-4 Turbo |
| `O1_PREVIEW` | 2024-09-12 | capability | OpenAI, [Introducing o1-preview](https://openai.com/index/introducing-openai-o1-preview/) | OpenAI API [changelog](https://developers.openai.com/api/docs/changelog) (September 2024) | date verified |
| `GPT41_LAUNCH` | 2025-04-14 | capability + price | OpenAI, [Introducing GPT-4.1 in the API](https://openai.com/index/gpt-4-1/) | OpenAI API [changelog](https://developers.openai.com/api/docs/changelog) (April 2025) | date and launch prices verified |

The current registry contains 21 dated chronology rows through 2026-08-06:
four currently eligible core events, sixteen candidates, and the binding
`gpt-4.5-preview` exclusion. Four candidates are explicitly pending a second
independent date locator. Candidate status is resolved before Gate 1; W5 later
applies the signed dose threshold without adding or deleting chronology rows.
The mechanically fillable event-by-event table is frozen in
`event_table_shell_v1.csv`. W5 may fill only its blank window, crossing-count,
dose-distribution, and effective-weight fields after applying Decisions 1--3;
it may not change event IDs, dates, thresholds, or column definitions.
At the Gate-1 freeze, any candidate still lacking two independent dated
locators or a source-complete dated price row is mechanically reclassified
`source_failed` and excluded from the primary event set. It remains in the
chronology with the failed source fields and exclusion reason; it cannot be
restored after outcomes open except through a dated deviation memo.
This rule includes every unresolved `conflict_b`: W2 must select the price row
supported by two independent dated locators and archive the conflicting rows,
or the event becomes `source_failed`; averaging or choosing the lower price is
prohibited. If W4 cannot recover either a qualifying historical snapshot or a
feasibility-approved cited stand-in, the event is likewise excluded as
`measurement_failed` and retained only in the descriptive chronology.
Registry price status `relative_price_verified` means that two locators verify
a relative price change but W2 has not yet attached the absolute pre/post price
rows needed for dose construction; it is therefore not source-complete at
Gate 1 unless W2 supplies those rows. `pending_w2` has no verified price change,
and `n_a` is allowed only for a capability-only event whose price is unchanged.

### 1.3 Registry completion queue

Candidate rows now cover GPT-4 Turbo/DevDay, GPT-4o mini, full o1, o3-mini,
o3/o4-mini, GPT-5-family launches through GPT-5.6, and located price changes.
They remain non-filed analysis events until the CSV records two date locators
and W2 attaches dated prices. W2 emits the source-complete price-history panel;
W1 imports its event IDs without changing the rules below.

The current official deprecations page contains both a historical 2025-09-26
row saying `gpt-4-1106-preview` shut down on 2026-03-26 and a newer
2026-04-22 row listing an October 23, 2026 shutdown for the same slug. The
signed feasibility adjudication uses the newer row for capture planning. The
memo preserves both locators as a provenance conflict; W4 must test actual
availability before budgeting the row.

**[PI-DECISION 1]** *(re-scoped under D1, 2026-08-18)* **Event eligibility.**
Originally this threshold governed inclusion in the primary stacked analysis.
The primary specification no longer selects events, so it now governs *separate
reporting*: an event with at least one percentage point of occupation wage-bill
dose at the median occupation is named in the descriptive chronology and
receives its own leave-one-event-out diagnostic. Smaller events still enter the
DAX dose path in full. **No event is dropped from the dose path on account of
its size**, which is the substantive change — the old rule discarded small
events from estimation, and the continuous design does not.

## 2. DAX construction objects fixed for the design

For task `t`, occupation `o`, month `m`, mapping `k`, cost variant `v`,
deployment parameter `delta`, and failure-cost rule `g`, define

`pi_eff = 1 - delta * (1 - pi)`

and crossing indicator

`A_tom = 1[c/pi_eff + f*(1-pi_eff)/pi_eff < w]`.

`DAX_om` is the frozen-2021 wage-bill share of occupation tasks with `A_tom=1`.
`DeltaDAX_oe` is the share newly changing from zero to one at event `e`. A task
cannot cross twice in the primary monotone chronology. If a measured capability
regression or price increase reverses feasibility, the reversal is retained as
a signed change in a separate non-monotone diagnostic and does not erase its
first crossing.

Primary grid:

- mapping: GDPval, Tolan-style, Eloundou-style;
- cost: API list, `0.6 * list`, open-weight marginal;
- `delta`: 1.0, 0.8, 0.6;
- failure multiple by O*NET consequence tier: 0.25, 1, 4 times task wage;
- failure sensitivity: zero, half, primary, and double tier multiples;
- cost accounting: billed tokens and completion-only effective tokens for
  reasoning models;
- wage vintage: 2021 primary, 2019 alternative.

The flip rate is the share of occupation-event cells whose crossing status
changes anywhere across the failure-cost grid. The already-proposed trigger is
strictly greater than 20%. Crossing this trigger halts W5 before outcome work
and returns the threshold design to the PI; it does not authorize choosing the
best-performing grid point.

## 3. Continuous cumulative-dose protocol

**Design change, D1, PI-approved 2026-08-18.** This section previously
specified a stacked common-event design with clean windows. Executing that
specification against this memo's own registry left two estimable events from
the four currently eligible rows, and one if the registry is completed as
planned; the power engine refuses to run below three. The rule was also
non-monotone in evidence quality, so completing the registry made
identification worse and the project's own W2 sourcing work self-defeating.

The cause was not an implementation error. A stacked event study with clean
windows presumes discrete, well-separated shocks; with 21 events across 41
months the treatment is effectively continuous, and every discrete repair
either collapsed to a single event or manufactured purity by ignoring events
that actually occurred. The full option comparison is reproducible via
`python dax/memo/validate_window_survival.py --options` and recorded in
`dax/memo/PI_DECISION_D1_2026-08-18.md`.

### 3.1 Unit, dose, and comparison

The analysis unit is person-month in IPUMS-CPS. The treatment is the DAX level
`DAX_om` of the person's reference occupation in the reference month, assigned
through the employment-weighted many-to-many CPS to O*NET-SOC crosswalk.

There is no event selection, no stacking, and no clean-window rule. Every
source-verified event contributes to the dose path

`DAX_ot = DAX_o,0 + sum over events e with API-effective month <= t of DeltaDAX_oe`

and identification comes from occupations accumulating dose on different
profiles across the same calendar months. Comparison is a continuum rather than
a control arm: conditional on the controls in section 9.1, the contrast is
between occupations whose dose rises faster and those whose rises more slowly.
Occupations with zero cumulative dose sit at the low end of that continuum.

**Consequence for W2, stated because it reverses the previous incentive.**
Under the superseded rule, each newly verified event shortened clean windows
and reduced the estimable set. Under this design each newly verified event adds
dose variation and can only increase identifying variation. Registry and price
work now improves the design monotonically.

### 3.2 Parameters of the dose path

The Decision numbers below are retained rather than renumbered so the PI
approval record of 2026-08-06 stays aligned. Where D1 changed a decision's
role, that is stated explicitly rather than silently reinterpreted.

Decision 1 (section 1.3) is re-scoped rather than repeated here: it now selects
which events are *separately narrated*, not which enter the dose path. Every
source-verified event contributes dose regardless of size.

**[PI-DECISION 2]** *(retired from the primary under D1)* **Window and
stacking parameters.** The primary specification has no windows, so this
decision no longer binds it. The rule survives unchanged as the governing
parameter of the secondary stacked corroboration in section 9.4, at the
four-month compound setting. The number is **not** reused for anything else.

**[PI-DECISION 3] Minimum occupation dose.** Unchanged in substance and now
applies only to descriptive treated-bin summaries: a treated occupation-event
cell requires `DeltaDAX >= 0.01`. The continuous regressor retains all positive
doses, including those in `(0, 0.01)`.

**[PI-DECISION 4]** *(reversed under D1)* **Dose accumulation.** The superseded
design used the event increment `DeltaDAX_oe` as the primary regressor and the
level as a control, in order to isolate new information at a discrete event.
With no discrete events the reasoning inverts: the primary regressor is the
cumulative **level** `DAX_ot`, which is the object the index in section 2
actually constructs, and the within-month increment is reported alongside it as
a secondary specification. This reversal is the substantive econometric content
of D1 and is flagged here so no reader infers it from the equations alone.

**[PI-DECISION 5]** *(retired under D1)* **Earlier crossers.** This decision existed
to say whether previously-treated occupations could serve as controls inside a
later clean window. There are no clean windows and no control arm, so the
question does not arise. What survives from it is the monotonicity convention:
a task that has crossed stays crossed in the primary path, and a measured
capability regression or price increase is recorded as a signed change in the
separate non-monotone diagnostic rather than erasing the first crossing.
Occupations with high pre-period dose are not excluded; pre-event DAX level
enters as a registered control and a robustness sample excludes occupations
already above the median dose at 2023-02.

### 3.3 What the secondary stack retains

The compound-event state algorithm of the superseded draft is retained
verbatim for the secondary specification: order components by exact
API-effective timestamp then event id, define the pre state immediately before
the first component and the post state immediately after the last, recompute
crossings on those two states, and set the composite `DeltaDAX` to the
wage-bill share moving from zero to one. It is a correct piece of machinery
that the primary design simply no longer needs.

## 4. Identifying conditions and estimands

**IC-1 — Conditional parallel trends in a continuous, time-varying dose.**
For every pair of calendar months and every pair of dose paths in the common
support, the expected change in untreated potential outcomes is equal across
paths, conditional on occupation effects, calendar-month effects,
industry-by-month effects, frozen static-exposure decile interacted with month,
occupation interest-rate sensitivity, and the registered baseline covariates.
This is the continuous-treatment condition of Callaway, Goodman-Bacon and
Sant'Anna (2024); it is strictly stronger than the two-period version, because
it must hold at every month rather than only across a single window.

**IC-2 — No dose-correlated interference.** Conditional on the same controls,
spillovers from high-dose to low-dose occupations do not vary with dose.
Mobility-network spillover estimates are auxiliary and do not repair a
violation.

**IC-3 — Mapping timing exclusion for the secondary IV.** Conditional on
controls, errors in the Tolan and Eloundou doses are independent of the GDPval
mapping error and of untreated outcome innovations. Shared structural errors,
such as all three mappings equating benchmark performance with production
success, violate this condition and are not removed by instrumenting.

**IC-4 — Frozen entry mix (entrant companion only).** The entry-occupation
distribution `pi_go`, estimated once over 2021-11 to 2023-02, is independent of
post-2023 innovations in entrant employment conditional on cell and month
effects. If entrants systematically divert away from exposed occupations after
the pre-period, that diversion is an outcome and must not enter the regressor;
freezing `pi_go` in the pre-period is what enforces this, and the assumption
that the frozen mix remains a valid *instrument* for exposure, rather than a
description of realised entry, is the companion's central identifying
requirement.

### Estimands

**Primary (incumbent margin).** The change in employment probability and in
unconditional weekly hours associated with a 0.10 increase in occupation DAX
level, among young workers with a prior occupational attachment, over the
observed common-support population. Reported pooled, by 12-month calendar
block, and as a binned nonparametric dose response.

**Companion (entrant margin).** The change in the employment rate of an
entrant cohort associated with a 0.10 increase in the frozen entry-mix-weighted
DAX of the occupations that cohort typically enters.

The two estimands partition the 22-25 population and answer different
questions. They are reported side by side. Neither is presented as a robustness
check on the other, and a disagreement between them is a finding about which
margin adjusts, not a specification problem to be resolved in favour of the
stronger result.

**Why not a single pooled estimand.** Merging the two would require imputing an
occupation for people who never held one. That is fabrication, and it would
produce a coefficient that means neither margin. It is rejected under every
budget.

## 5. Mapping hierarchy and measurement quality

GDPval is primary. Tolan and Eloundou mappings are independent robustness
constructions. All task matches retain similarity, coverage, confidence,
adjudication status, and a top-quartile match-quality flag. Unmatched tasks
remain explicit and their wage-bill share is reported.

The pre-existing survive-all-three rule is binding: the point-estimate sign is
consistent across all three mappings and the relevant test rejects at the 10%
level under at least two mappings.

**[PI-DECISION 6] Mapping tiebreaker default.** If all signs agree but sampling
precision differs, report GDPval as primary and the median standardized point
estimate across mappings as the descriptive synthesis. The tiebreaker never
overrides a sign conflict or the survive-all-three failure rule.

**[PI-DECISION 7] Human-validation targets.** Audit 10% of mapping-C annotations
stratified by occupation family, score decile, and ambiguity flag. Require
weighted Cohen's kappa of at least 0.70 and at least 90% agreement on the binary
crossing-relevant label before W5. Failure returns the rubric for redesign
before index construction.

## 6. Index validation and behavioral first stage

### 6.1 Public index validation

**[PI-DECISION 8] Convergent-validity threshold.** The primary GDPval/list/
`delta=1` DAX level must have occupation-level Spearman rank correlation of at
least 0.50 with the frozen Felten-Eloundou-Webb ensemble at one or more
pre-registered benchmark months, with Kendall correlation reported. This is a
moderate convergence requirement: lower suggests construct failure, while a
near-one requirement would eliminate the intended dynamic/cost distinction.

Event alignment, capability-versus-price decomposition, crossing-order
stability, and comparison with published usage indices are reported without
post-hoc pass thresholds except those explicitly added by PI signature.

### 6.2 Usage-share first stage

The named human team alone runs frozen code on real OpenAI aggregates. The
agent-developed pipeline sees synthetic data only.

The first-stage unit is frozen O*NET task-or-IWA cell by event by calendar
month. For cell `i` and month `t`, within-month usage share is the number of
classified eligible ChatGPT messages assigned to `i` divided by all classified
eligible messages in the same negotiated product population and calendar
month, before cell suppression. For event `e`, the pre-event mean is the simple
arithmetic mean of that share over every surviving clean pre month for which
the cell is observed; the complete-case rule in Section 8 requires observation
in all required pre and post months. The normalized outcome is
`100 * (share_iet / premean_ie - 1)`.
If `premean_ie=0`, the normalized outcome is undefined and the cell is excluded
from the normalized first stage rather than regularized. Its raw share path is
reported as an auxiliary diagnostic, along with the excluded task-mass share.

**[PI-DECISION 9] Minimum behavioral effect.** Success requires the pooled
post-crossing coefficient on that normalized outcome to be at least 5, meaning
a 5% relative usage-share increase, with its 90% confidence interval excluding
zero. Event-time coefficients remain required diagnostics. Asking-to-Doing
composition is a mechanism outcome; default materiality is a two
percentage-point increase in Doing share, reported with uncertainty but not a
separate gate.

A positive first stage supports dateable translation from feasibility to
behavior. A null does not disprove technical feasibility; it localizes adoption
away from measured ChatGPT message channels or indicates that unit economics is
not the binding adoption margin.

## 7. CPS sample, outcomes, and power specification

### 7.1 Population and the estimand this sample supports

Population: U.S. persons ages 22-25 in monthly IPUMS-CPS, November 2021
through the latest frozen month, using person weights. Dose is assigned at the
CPS occupation code after employment-weighted crosswalking to O*NET-SOC.

A person's reference occupation is the most recent valid CPS occupation
observed for the same `CPSIDP` strictly before the reference month and no more
than 15 calendar months earlier. That reference is held fixed for the person's
contribution in that month. This preserves respondents who are unemployed at
the time of measurement and prevents a post-treatment occupation change from
redefining treatment. A registered robustness check caps the lookback at nine
months.

**[D4 Part 1, PI-approved 2026-08-18] The estimand is stated, not implied.**
The lookback rule excludes every person with no prior occupational attachment.
For ages 22-25 that is, specifically, labour-market entrants. Therefore:

> The primary estimand is the effect of AI exposure on the employment and
> hours of young workers **who already hold an occupational attachment**. It
> is an incumbent margin. It is not an effect on labour-market entry. Persons
> with no pre-period occupation observation are outside the estimand by
> construction, not missing data.

The count, weighted share, and lookback-duration distribution of excluded
persons are reported in the main text, not an appendix.

The proposal's 13% benchmark is drawn from literature in which the effect
operates substantially through reduced **hiring**. That benchmark and this
primary estimand are therefore not the same object. A null on the incumbent
margin is not evidence against an entrant-margin finding, and the memo does not
present it as such.

### 7.2 Entrant-margin companion (registered secondary, PI-approved 2026-08-18)

Because the mechanism the paper is benchmarked against operates at entry, the
entrant margin is studied directly rather than disclaimed.

This is not an inference from the abstract. The source paper reports that the
divergence "operates primarily through reduced hiring of young workers rather
than increased separations" — so the incumbent margin the primary design
measures is, by the benchmark literature's own account, the margin on which the
effect is *weaker*. A design that measured only incumbents would be benchmarked
against an effect it is structurally unable to see. That is the case for the
companion, and it is why D4 Part 2 was approved rather than disclaimed.

Sample: persons ages 22-25 with no valid occupation observation in the
lookback window — exactly the complement of the primary sample, so the two
partition the age range without overlap.

Dose: entrants have no occupation, so occupation dose cannot be assigned to
them. Instead each monthly entrant cohort is assigned the
**entry-mix-weighted DAX**

`EDAX_gt = sum_o pi_go * DAX_ot`

where `pi_go` is the frozen probability that an entrant in demographic-education
cell `g` first appears in occupation `o`, estimated **once** from the
pre-event window 2021-11 to 2023-02 and never re-estimated. Freezing `pi_go`
in the pre-period is what keeps the weights exogenous to the treatment: if
entrants divert away from exposed occupations after 2023, that diversion is
the outcome, and it must not be allowed to move the regressor.

Specification: cell-by-month panel, outcome the employment rate of the entrant
cohort, regressed on `EDAX_gt` with cell effects, calendar-month effects, and
the registered controls, clustered on the entry-mix cell.

Estimand: the effect of exposure of an entrant cohort's typical entry
occupations on that cohort's employment rate.

Registered limitations, stated in advance: `pi_go` is measured with error and
the resulting attenuation is bounded by the same EIV machinery as the primary
(section 10.1); the entry-mix regressor has less independent variation than
occupation-level dose, so this companion is expected to be less powered and
carries its own power table; and it cannot support headline claims unless it
meets the same frozen standard in section 7.4. A companion that fails its
power standard is reported as informative and explicitly non-confirmatory.

### 7.3 Outcomes

Primary: (1) employment indicator; (2) unconditional usual weekly hours, coded
zero for the non-employed. Secondary: log hourly wage among the employed, and
conditional weekly hours. Auxiliary: occupation switching, unemployment reason,
search duration. The college-attainment split is secondary, receives its own
power table, and cannot support headline claims.

**[PI-DECISION 10] Multiplicity default.** Unchanged: Holm across the two
primary outcomes at two-sided 5%, unadjusted intervals reported alongside
adjusted p-values, Benjamini-Hochberg at 10% applied separately to the
secondary and auxiliary families. The entrant companion forms its own family
and is corrected within itself; it is not pooled with the primary family,
because pooling would let a companion result borrow the primary's error budget.

### 7.4 Power standard

**[PI-DECISION 11]** *(numeric part superseded by D3, PI-approved 2026-08-18)*
The original bar was `min(6.5pp, 0.5 x baseline_employment_gap)`. The gap term
was estimated from the analysis sample, so it moved with the event set:
dropping a single event loosened the bar by 185% while the estimator got 19%
worse. A standard that moves with the specification it judges cannot fail.

The standard is now a frozen absolute constant:

`ceiling = max_mde_fraction x relative_decline x baseline_level`

where **`relative_decline = 0.13` is a relative decline in EMPLOYMENT
(headcount), not in payroll.** "Payroll" names the data source, not the
outcome: the estimate comes from ADP administrative payroll records. The
project's own proposal states it unambiguously — "U.S. payroll data, by
contrast, show a 13 percent relative employment decline among workers ages
22-25 in the most AI-exposed occupations" (`docs/DAX_ERE_Proposal_v3.md:12`,
citing Brynjolfsson, Chandar and Chen 2025, "Canaries in the Coal Mine? Six
Facts about the Recent Employment Effects of Artificial Intelligence",
`docs/DAX_ERE_Proposal_v3.md:100`). Because it is a *relative* decline, the
absolute percentage-point benchmark is `0.13 x baseline employment rate`, which
is what the formula above computes.

**Unresolved: which version's figure.** The same paper has been revised and the
headline figure has moved — 0.13 in the version the proposal cites, and later
revisions reportedly at 0.16 and 0.19. Freezing is one-way and a larger figure
loosens the pass bar, so the choice is a PI decision and
`freeze_power_standard.py` refuses to run until it is recorded. See
`PI_DECISION_D3_2026-08-18.md`.

With `max_mde_fraction = 0.5`, and
`baseline_level` the pooled person-weighted pre-event level of the outcome
(employment rate; mean unconditional hours) computed **once** over
2021-11 to 2023-02 and never recomputed. The window ends the month before the
first eligible event, so the constant cannot contain post-treatment
information, and it requires neither a dose definition nor an event set.

The constant lives in `dax/memo/power_calcs/power_standard.json` with its
provenance and a `status` field. Until it is `FROZEN`, both power engines
report minimum detectable effects and return `adequately_powered: null`. They
do not guess and they do not pass.

Recomputation after the event set, mapping, dose definition, or sample changes
is forbidden. Failure does not authorise sample or specification search: it
triggers the proposal's informative-power limitation and PI reconsideration,
exactly as the original Decision 11 provided.

**Unit of estimation versus unit of simulation (M5, resolved 2026-08-18).**
The *estimator* is person-month: section 9.1 is estimated on person records,
and the registered person covariates `X_i` enter there. The *power simulation*
operates on occupation-month cell moments, because cell moments are what the
frozen pre-event fixture provides and because the variance of `beta` is driven
by the occupation cluster structure rather than by within-cell person
variation. These are not the same object and the memo does not pretend they
are.

No ordering between the cell and person-level MDE is asserted. Omitting `X_i`
can raise residual variance, but aggregation also removes within-cell outcome
variation and changes weights and leverage; without additional assumptions
those forces do not sign the difference. The cell result is therefore only a
smoke-test/planning calculation and can neither pass nor fail Gate 1.

The Gate-1 calculation runs the person-month estimator directly on the frozen
pre-event extract, with post-event outcomes simulated against W5's real dose
panel. Its occupation-clustered rejection rates and MDEs are the only power
result used for the gate.

The power simulation must model the continuous design on pre-event moments
only, preserving occupation cluster sizes, person weights, crosswalk dose
dispersion, the dose path, and the observed employment-hours covariance. The
engine refuses to run if the moment file contains any month at or after the
first event.

**[PI-DECISION 12] Dispersion flag.** Unchanged: flag a CPS code as low
quality when the weighted within-code standard deviation of O*NET dose exceeds
0.10 or the maximum mapping weight is below 0.50, and re-estimate on the
complement as a registered robustness check.

## 8. Suppression, privacy, and minimum estimability

Suppressed OpenAI aggregate cells are missing by design and are never filled
with zero, midpoint, model prediction, or neighboring-cell values. Primary
first-stage estimation uses only cells observed in every required event-time
period. An inverse-observation-probability weighted sensitivity analysis may
use only publicly described suppression predictors and is labeled secondary.

**[PI-DECISION 13]** *(scope clarified under D1)* **Minimum estimability.**
This condition governs the **OpenAI usage first stage only**. It was written
for the first stage and the pre-D1 power engine wrongly enforced clause (c),
the three-event minimum, as a global gate on the CPS power calculation; under
the continuous primary there is no event count to gate on, and the continuous
engine does not apply it. Clause (c) continues to bind the first stage, where
events are genuinely the unit of estimation. Interpret the first stage
only if: (a) observed cells cover at least 70% of the wage-bill-weighted crossed
task mass; (b) at least 50 occupation/task cells remain; (c) at least three
eligible events remain; and (d) no single event contributes more than 50% of
the effective estimation weight. For event `e`, that weight share is
`sum_i w_ie * x_tilde_ie^2 / sum_j sum_i w_ij * x_tilde_ij^2`, where `w` is
the event-normalized CPS person weight and `x_tilde` is the primary continuous
dose-by-post regressor residualized on the complete frozen nuisance design.
Otherwise report selection and MDEs without an effect interpretation.

Only the PI and named RA may open or run code on real usage aggregates. The
repository stores schemas, synthetic data, frozen code, and aggregate cleared
diagnostics only—never cell-level NDA data or derivatives.

## 9. Econometric implementation and diagnostics

### 9.1 Primary estimating equation

For person `i` in occupation `o`, industry `j`, and calendar month `t`:

`y_iojt = beta * (DAX_ot / 0.10) + alpha_o + tau_t + gamma_jt + delta_{d(o),t} + X_i'theta + e_iojt`

where `alpha_o` are occupation effects, `tau_t` calendar-month effects,
`gamma_jt` industry-by-month effects, `delta_{d(o),t}` frozen
static-exposure-decile-by-month effects, and `X_i` the registered person
covariates. Standard errors cluster on the original CPS occupation code.
`beta` is the coefficient per 0.10 DAX increment.

Occupation effects absorb level differences and month effects absorb the
common time path, so `beta` is identified by the interaction of
occupation-specific dose magnitude and timing with the calendar. This is the
sense in which the design is a continuous difference-in-differences rather
than a cross-sectional exposure regression.

### 9.2 The degeneracy diagnostic

If every occupation's dose path were proportional to a single common path,
`DAX_ot = theta_o * f(t)`, the design would collapse to one exposure-times-post
contrast and the timing variation would contribute nothing. This is a
measurable property of the dose matrix, not a matter of opinion, and it is
reported before any estimate:

**Required diagnostic — dose-profile reporting.** Report the
effective rank of the demeaned occupation-by-month dose matrix and the share
of its variation in the leading singular component. A leading share above 0.95
with effective rank 1 is a degenerate design: report it as such, interpret
`beta` as a single exposure contrast, and do not present event-time language.
The threshold is a reporting trigger, not a pass/fail gate, and no estimate is
withheld on the basis of it.

**Consequence, pre-registered (M6, resolved 2026-08-18).** Deciding what a
degenerate design means *after* seeing the leading share would be a
specification choice made with knowledge of the data, so the consequence is
fixed now. If the design is degenerate:

1. The paper does not claim to identify a *dynamic* exposure effect. The
   headline claim becomes a cross-sectional exposure contrast estimated with
   panel controls, and every use of "timing", "event", or "dynamic" is struck
   from the claims about `beta`.
2. The DAX index's contribution over existing static measures is then argued on
   the **crossing chronology** — which tasks cross when, and at what price —
   not on the regression, since a degenerate dose matrix means the regression
   is using little more than a static ranking.
3. The Decision 8 convergent-validity result becomes load-bearing rather than
   descriptive: if DAX is behaving as a static measure, its rank correlation
   with the Felten-Eloundou-Webb ensemble is the evidence that it is measuring
   the intended construct at all.
4. The degeneracy statistic is reported in the abstract-level summary, not
   buried in diagnostics.

A design that is degenerate is still publishable. It is a different paper, and
saying which paper in advance is the point.

This is a required diagnostic rather than a numbered PI decision: it triggers
reporting language, never inclusion or exclusion, so it commits the PI to no
threshold. The 17 approved decisions are unchanged in number and membership.

### 9.3 Required diagnostics

- **placebo-lead pre-trend test** over 2021-11 to 2023-02 (see Decision 14);
- event-time-style plot in calendar time: `beta` estimated separately by
  12-month block, with the pre-event blocks shown;
- binned dose-response using bins frozen from the pre-event dose distribution;
- common-support and leverage plots by occupation and by decile;
- with and without industry-by-month effects;
- within-static-decile dose and industry-composition correlation;
- leave-one-occupation-out and leave-one-decile-out estimates;
- leave-one-event-out re-derivation of the dose path, which under the
  continuous design perturbs the path rather than deleting a stack;
- Rambachan-Roth sensitivity at M-bar 0.5, 1, and 2 plus the
  relative-magnitudes restriction, with M-bar 1 as headline;
- placebos: FOMC dates, permuted mappings, backward-shuffled price histories,
  and a dose path shifted forward by 12 months.

**[PI-DECISION 14]** *(re-specified 2026-08-18 — the previous form was not
computable)* **Pre-trend test.**

The superseded text required "a joint test of all pre-event dose coefficients".
Under the continuous design the regressor is cumulative `DAX_ot`, which is
**identically zero for every occupation** throughout 2021-11 to 2023-02: the
first eligible event is 2023-03. A regressor with no variance has no
coefficient, so that test could never have been run. It is replaced, not
weakened.

The pre-trend test is a **placebo lead on eventual exposure**. Let
`D_o = DAX_o,2024-12`, the occupation's cumulative dose at a frozen horizon,
which is a fixed occupation characteristic and therefore *does* vary in the
pre-period. Restricted to pre-event months only, estimate

`y_ot = phi * D_o * (t - t_0) + alpha_o + tau_t + gamma_jt + e_ot`

and test `phi = 0`. This asks the question that matters: were occupations
destined for high exposure already on different trajectories before any
exposure existed? A non-zero `phi` is the violation of IC-1, and unlike the
superseded test it is estimable.

The design passes the conventional pre-trend diagnostic only if `phi` has
p >= 0.10 and no single pre-period block interval excludes zero after Holm
correction. The horizon 2024-12 is frozen here so that `D_o` cannot be chosen
after seeing the result; the test is also reported at 2023-12 and 2025-12 as
registered robustness, with the 2024-12 version as headline.

The pre-event window is approximately sixteen months, which is short. This
diagnostic is therefore weaker here than in a long pre-period, HonestDiD
sensitivity remains mandatory regardless of the result, and the shortness is
reported as a limitation rather than absorbed silently.

### 9.4 Secondary stacked corroboration

The discrete stacked design of the pre-D1 draft is retained as corroboration
under the compound rule at four months. It is reported with its own power
statement, its estimable-event count, and an explicit statement that it is not
confirmatory. Where primary and secondary disagree, both are reported and the
disagreement is discussed; the specification that produces the larger or more
significant estimate is not selected.

## 10. EIV, cross-mapping IV, and deployment calibration

### 10.1 Errors-in-variables simulation

For each mapping, perturb task success probability using distributions
calibrated to human disagreement and item-level score dispersion, redraw at
least at task and occupation-correlated levels, and rederive crossings.

**[PI-DECISION 15] EIV acceptable bounds.** Before outcome work, require median
absolute crossing-date shift no greater than one month, 90th-percentile shift
no greater than three months, no more than 10% of occupation-event cells
changing dose bin, and implied linear attenuation no worse than 0.80. In each
EIV draw, construct the exact frozen stack and residualize both the unperturbed
dose-by-post regressor `x_true` and perturbed regressor `x_obs` on the same
nuisance matrix with the same event-normalized weights. The draw-specific
attenuation factor is the weighted slope
`Cov_w(x_obs_tilde,x_true_tilde) / Var_w(x_obs_tilde)`: the coefficient obtained
from outcome-on-observed-dose when the true coefficient is one and no sampling
noise is added. The 0.80 bound applies to the median factor across draws; report
its 5th--95th percentile interval. Exceeding any bound does not permit selecting
a quieter mapping; it triggers redesign or an explicitly weakened estimand.

### 10.2 Cross-mapping IV

Instrument GDPval `DeltaDAX` separately and jointly with Tolan and Eloundou
doses. Report reduced forms, first stages, overidentification diagnostics, and
the IV/OLS ratio as a reliability diagnostic.

**[PI-DECISION 16] Weak-instrument rule.** Interpret IV magnitudes only when the
heteroskedasticity/cluster-robust effective first-stage F statistic is at least
10. Otherwise report weak-instrument-robust intervals and treat IV as
uninformative.

### 10.3 Post-first-stage delta calibration

A raw ratio of observed to predicted usage jumps is not, by itself, a valid
estimate of `delta`, because `delta` changes `pi_eff`, crossing sets, and
predicted event jumps nonlinearly. DAX v1.1 therefore uses the pre-registered
minimum-distance estimator

`delta_hat = argmin_{d in [0,1]} sum_e weight_e * (J_obs_e - J_pred_e(d))^2`,

where `J_pred_e(d)` is recomputed through the full crossing pipeline and
weights are inverse estimated variances of observed jumps. Bootstrap resamples
the eligible usage cells and events. This calibration is post-first-stage and
cannot change this paper's primary grid `{1.0, 0.8, 0.6}`.
Estimate each jump variance with a pre-registered two-way pigeonhole bootstrap:
1,000 draws independently resample eligible task/IWA cells and eligible events
with replacement, rerun the frozen first stage, and use the sample variance of
the resulting event-specific jump. Set weight to the reciprocal of that
variance, winsorized at the frozen 1st and 99th percentiles; a zero or
non-estimable variance excludes that event from calibration and is reported.

**[PI-DECISION 17] Calibration reporting.** Search a 0.01 delta grid on `[0,1]`,
report the minimizer and percentile 95% bootstrap interval, and label estimates
boundary-limited when the minimizer is 0 or 1. Do not report delta_hat if the
minimum-estimability condition fails.

## 11. Frozen output and deviation policy

W5 must emit the full mapping × cost × delta × failure-grid panel, crossing
chronology, event table, flip-rate report, EIV diagnostics, capability-only
counterfactual, distributional variant, and live-vintage decomposition. No
configuration may be dropped because it performs poorly.

Any post-tag change to an event, window, dose, threshold, mapping hierarchy,
sample, outcome family, or estimability rule requires a dated deviation memo
approved by the PI before execution. First-run results are retained and
reported. The `analysis/outcomes/` guard remains fail-closed.

### 11.2 Deviation log

All four entries below are pre-tag amendments to a draft. None was made with
access to outcome data: the seal was closed throughout, `dax/data_raw/` held no
extract, and every quantity consulted was either date arithmetic on the frozen
registry or a power statistic on a synthetic fixture stamped
`NOT_EVIDENCE_SYNTHETIC_SMOKE_TEST`. No estimated treatment effect existed or
was examined.

| Date | Ref | Change | Counter-signed |
|---|---|---|---|
| 2026-08-18 | D1 | Primary specification changed from a stacked event study to a continuous cumulative-dose design; stack demoted to secondary. Decisions 1, 4, 5 re-scoped/reversed/retired; Decision 2 moved. | 2026-08-18 |
| 2026-08-18 | D3 | Power pass bar changed from `min(6.5pp, 0.5 x baseline_gap)` to a frozen absolute constant computed once over the pre-event window. | 2026-08-18 |
| 2026-08-18 | D4 | Primary estimand named as an incumbent margin; entrant-margin companion registered as a secondary design with a frozen pre-period entry mix. | 2026-08-18 |
| 2026-08-18 | F2 | Five event rows demoted to `pending_second_date_locator`; `date_conflict` column added; the release-dating rule is now enforced by `validate_event_registry.py` rather than applied by hand. | 2026-08-18 |

Decision numbering is never reused for a different purpose without saying so.
Where D1 changed a decision's role, the original number is retained and the
change is stated at the point of use, so the 2026-08-06 approval record
remains readable against this draft.

## References and source register

- Callaway, Goodman-Bacon, and Sant'Anna (2024), continuous-treatment DiD.
- Callaway and Sant'Anna (2021), multiple-period DiD.
- Rambachan and Roth (2023), parallel-trends sensitivity.
- DAX proposal and execution plan in `docs/`.
- Signed feasibility evidence in `dax/memo/feasibility_note.md` and
  `dax/memo/w05_legwork_2026-07-10.md`.
- OpenAI API [changelog](https://developers.openai.com/api/docs/changelog) and
  [deprecations](https://developers.openai.com/api/docs/deprecations), retrieved
  2026-08-06.

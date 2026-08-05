# Dynamic AI Exposure (DAX): pre-registered design memo v1

**Status:** PI DEFAULTS APPROVED 2026-08-06 — EVIDENCE PENDING; not pre-registered

**Draft date:** 2026-08-06

**Gate:** `DAX-GATE1-memo`

**Outcome-data status:** SEALED until the signed tag `v1.0-preregistered`

This memo translates the DAX proposal and Amendment v1.1 into an executable
design. The PI approved all 17 bracketed `[PI-DECISION]` defaults and all six
non-numeric confirmations on 2026-08-06. They are frozen design choices, but
the tag remains prohibited until the evidence checklist, power task,
independent red-team, and rendered review are complete.

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

**[PI-DECISION 1] Event eligibility default.** Require at least one percentage
point of occupation wage-bill dose at the median occupation for an event to be
included in the primary stacked analysis. Smaller events remain in the DAX
panel and descriptive chronology but are not separately estimated. This avoids
nearly unidentified event coefficients while leaving the index complete.

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

## 3. Stacked common-event dose-response protocol

### 3.1 Unit, dose, and comparison

The analysis unit is person-month in IPUMS-CPS, with DAX doses assigned through
the employment-weighted many-to-many CPS occupation to O*NET-SOC crosswalk.
The event-specific treatment is continuous `DeltaDAX_oe`. The comparison set
for event `e` contains occupations in the same frozen static-exposure decile
with zero crossing dose at `e` and no crossing inside that event's clean
window.

### 3.2 Four stacking parameters

**[PI-DECISION 2] Window default.** Use event time `[-6,+6]` months, then trim
each side at the midpoint to the adjacent eligible AI event. Retain an event
only if at least three uncontaminated pre months and three uncontaminated post
months remain. This preserves useful dynamics while making overlap rules
mechanical.

**[PI-DECISION 3] Minimum occupation dose default.** Define a treated
occupation-event cell as `DeltaDAX >= 0.01`; retain smaller positive doses in
continuous-dose estimation but exclude them from treated-bin summaries. One
percentage point is economically interpretable and limits classification noise
near zero.

**[PI-DECISION 4] Dose accumulation default.** The primary event coefficient
uses the event increment `DeltaDAX_oe`, not the cumulative DAX level. Current
DAX level and prior cumulative dose enter as pre-event state controls. This
isolates the new information at the event while respecting that exposure stock
persists.

**[PI-DECISION 5] Earlier-crossers default.** Earlier-crossing occupations stay
eligible if they receive a new positive increment at the current event and
have no other crossing inside the current clean window. They cannot serve as
zero-dose controls. Occupations with only prior exposure may serve as controls
within static decile after conditioning on pre-event DAX level. Report a
robustness sample excluding all prior crossers.

Each event contributes person weights normalized to sum to one within event,
so large CPS months or longer surviving windows do not mechanically dominate
the stack. Standard errors cluster by the original CPS occupation code.

## 4. Identifying conditions and estimands

**IC-1 — Conditional strong parallel trends for a continuous dose.** For every
eligible event, event time, and two doses in the common support, the expected
change in untreated potential outcomes is identical across doses conditional
on frozen static-exposure decile, occupation fixed effects, calendar-month
fixed effects, industry-by-month fixed effects, occupation interest-rate
sensitivity, pre-event DAX level, and the registered baseline covariates.

**IC-2 — No event-window dose-correlated interference.** Conditional on the
same controls, spillovers from high-dose occupations to comparison occupations
do not vary with event dose inside the clean window. Mobility-network spillover
estimates are auxiliary and do not repair violation of IC-2.

**IC-3 — Mapping timing exclusion for secondary IV.** Conditional on controls,
errors in Tolan and Eloundou doses are independent of the GDPval mapping error
and untreated outcome innovations. Shared structural errors—such as all
mappings equating benchmark performance with production success—violate this
condition and are not removed by IV.

Primary estimand: the change in employment probability and unconditional
weekly hours associated with a 0.10 increase in event-specific DAX dose,
averaged over eligible events and the observed common-support population.
Event-specific and binned nonparametric estimates accompany the pooled linear
dose response.

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

**[PI-DECISION 9] Minimum behavioral effect.** Success requires a post-crossing
increase of at least 5% relative to the cell's pre-event mean within-month
usage share, with the pooled 90% confidence interval excluding zero. Asking to
Doing composition is a mechanism outcome; default materiality is a two
percentage-point increase in Doing share, reported with uncertainty but not a
separate gate.

A positive first stage supports dateable translation from feasibility to
behavior. A null does not disprove technical feasibility; it localizes adoption
away from measured ChatGPT message channels or indicates that unit economics is
not the binding adoption margin.

## 7. CPS sample, outcomes, and power-analysis specification

Population: U.S. persons ages 22–25 in monthly IPUMS-CPS, November 2021 through
the latest frozen month, using person weights. Dose assignment occurs at the
CPS occupation code after employment-weighted crosswalking to O*NET-SOC.

Primary outcomes:

1. employment indicator;
2. unconditional usual weekly hours, coded zero for non-employed persons.

Secondary outcomes: log hourly wage among employed persons and conditional
weekly hours. Auxiliary outcomes: occupation switching, unemployment reason,
and search duration. The college-attainment split is secondary, receives its
own power table, and cannot support headline claims.

**[PI-DECISION 10] Multiplicity default.** Control family-wise error across the
two primary outcomes with Holm at two-sided 5%. Report unadjusted confidence
intervals plus adjusted p-values. Apply Benjamini-Hochberg at 10% separately to
secondary and auxiliary families.

The W1 power task must simulate the exact stacked structure using pre-event
CPS moments only. It must preserve occupation cluster sizes, person weights,
crosswalk dose dispersion, event windows, and the observed covariance between
employment and hours. Simulated effects are injected after event time zero;
the code cannot estimate treatment effects on real post-event outcomes before
Gate 1.

**[PI-DECISION 11] Power standards.** Use two-sided alpha 0.05 and 80% power.
Report MDEs for a 0.10 DAX dose and benchmark them against the 13% payroll
decline cited in the proposal. The preferred design is adequately powered only
if the employment MDE is no larger than 6.5 percentage points or one-half of
the corresponding baseline employment gap, whichever is smaller. Failure does
not authorize sample/specification search; it triggers the proposal's
informative-power limitation and reconsideration by the PI.

Every output reports CPS-to-O*NET dose dispersion. **[PI-DECISION 12]** Flag a
CPS code as low-quality when the weighted within-code standard deviation of
O*NET dose exceeds 0.10 or the maximum mapping weight is below 0.50. Re-estimate
on the complement as a registered robustness check.

## 8. Suppression, privacy, and minimum estimability

Suppressed OpenAI aggregate cells are missing by design and are never filled
with zero, midpoint, model prediction, or neighboring-cell values. Primary
first-stage estimation uses only cells observed in every required event-time
period. An inverse-observation-probability weighted sensitivity analysis may
use only publicly described suppression predictors and is labeled secondary.

**[PI-DECISION 13] Minimum estimability default.** Interpret the first stage
only if: (a) observed cells cover at least 70% of the wage-bill-weighted crossed
task mass; (b) at least 50 occupation/task cells remain; (c) at least three
eligible events remain; and (d) no single event contributes more than 50% of
the effective estimation weight. Otherwise report selection and MDEs without
an effect interpretation.

Only the PI and named RA may open or run code on real usage aggregates. The
repository stores schemas, synthetic data, frozen code, and aggregate cleared
diagnostics only—never cell-level NDA data or derivatives.

## 9. Econometric implementation and diagnostics

The primary pooled model interacts continuous event dose with event-time
indicators and includes occupation, event-stack, calendar-month, and
industry-by-month effects, plus registered controls. Every linear estimate is
paired with nonparametric dose bins determined from the pre-event dose
distribution and frozen before outcomes are opened.

Required diagnostics:

- joint test of all pre-event dose coefficients;
- binned dose-response plot for every primary parametric result;
- common-support and leverage plots by event;
- with/without industry-by-month fixed effects;
- within-static-decile dose/industry-composition correlation;
- leave-one-event-out estimates;
- Rambachan-Roth sensitivity at M-bar 0.5, 1, and 2, plus the
  relative-magnitudes restriction; M-bar 1 is headline;
- FOMC dates, between-event pseudo dates, permuted mappings, and
  backward-shuffled price histories as placebos.

**[PI-DECISION 14] Pre-trend default.** A design passes the conventional
pre-trend diagnostic only if the joint pre-event test has p >= 0.10 and no
single pre-period adjusted confidence interval excludes zero after Holm
correction. This diagnostic is not proof of IC-1; HonestDiD sensitivity remains
mandatory regardless of the test result.

## 10. EIV, cross-mapping IV, and deployment calibration

### 10.1 Errors-in-variables simulation

For each mapping, perturb task success probability using distributions
calibrated to human disagreement and item-level score dispersion, redraw at
least at task and occupation-correlated levels, and rederive crossings.

**[PI-DECISION 15] EIV acceptable bounds.** Before outcome work, require median
absolute crossing-date shift no greater than one month, 90th-percentile shift
no greater than three months, no more than 10% of occupation-event cells
changing dose bin, and implied linear attenuation no worse than 0.80. Exceeding
any bound does not permit selecting a quieter mapping; it triggers redesign or
an explicitly weakened estimand.

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

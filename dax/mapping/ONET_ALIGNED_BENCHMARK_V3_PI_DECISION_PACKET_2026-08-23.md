# DAX Mapping A v3: O*NET-aligned benchmark PI decision packet

**Date:** 2026-08-23

**Status:** `DESIGN_PREFLIGHT_COMPLETE_NEED_PROSPECTIVE_PI_SIGNATURE`

**Base commit:** `3159b62f7f4d32c8e3bca5df22ce30d367145b1d`

This packet implements the PI's methodological direction at the design level
only. The proposed primary direction is an O*NET-aligned bridge benchmark. A
strict direct-task design is retained as a separate lower bound. Mapping A v2
is historical and unvalidated; its USD 60 budget remains unspent and its locked
test remains sealed. No production benchmark item, model inference, W5,
identification, power, or outcome operation occurred.

## A. Exact proposed v3 estimand

Let `o` be an occupation, `t` an O*NET task, `m` a model vintage, and `r` a
prospectively equivalent benchmark instance. Let `omega_ot` be the authorized
task mass of task `t` in occupation `o`, normalized only over the full eligible
occupation task frame—not over the successfully benchmarked subset.

For a frozen task boundary and quality standard, define:

- `Y_tmr=1` only when the **complete required deliverable** passes its frozen
  completion criterion and independent scoring rule;
- `p_tm = Pr(Y_tmr=1)` across frozen equivalent instances and repetitions;
- `h_ot` as qualified-human completion time without AI;
- `a_tmr` as human active assistance during an AI workflow;
- `v_tmr` as review/checking time, `u_tmr` as retry/rework time, and `e_tmr`
  as residual human completion time;
- `c_tmr` as metered model plus tool monetary cost; and
- `L_t[1-p_tm]` as the prospectively valued expected consequence of failure.

The human and AI-workflow costs are

```text
C^H_ot  = w_o * h_ot
C^AI_otm = E_r[c_tmr + w_o*(a_tmr + v_tmr + u_tmr + e_tmr)]
            + L_t*(1 - p_tm).
```

For a prospectively signed minimum full-task reliability `p_star`, the task
crossing indicator is

```text
Z_otm = 1[p_tm >= p_star AND C^AI_otm <= C^H_ot].
```

The central treatment is

```text
DAX_om = sum_t omega_ot * Z_otm / sum_t omega_ot.
```

The denominator remains the eligible occupation task mass. Missing,
non-evaluable, or unmeasured tasks are not silently dropped or renormalized.

In plain language, `DAX_om` is the occupation's task-mass share for which the
specified model/workflow can deliver the entire O*NET-aligned work product at
the required quality and reliability, after pricing model/tool use, human
assistance, review, retries, residual work, and expected failure losses, at no
more than the human-only cost.

### Boundary between full and partial performance

- A draft, recommendation, component, or intermediate artifact is not full-task
  success unless the frozen task definition says that artifact is the complete
  work product.
- AI-assisted success is measured separately from unaided model success. Human
  assistance, review, retry, and residual work are observed and costed rather
  than hidden in a binary success label.
- Partial completion may support a separately named minutes-saved descriptive
  measure. It does not count as a central crossing merely because it is useful.
- `p_star`, scoring cutoffs, failure-loss rules, and whether the central
  production workflow is autonomous or AI-assisted are unsigned PI choices.
  None is selected here.

This preserves the substantive full-task cost-effective displacement estimand;
it does not relabel generic AI exposure as displacement.

## B. O*NET-aligned benchmark architecture

The private sampling frame is the authorized O*NET task universe. The current
repository records 19,259 task records, of which 15,274 have usable frozen
task-mass/wage-allocation inputs. Eligibility and duplicate/link rules must be
resolved before sampling; these counts are not themselves a sampling approval.

Each private benchmark definition must contain:

| Field | Prospective rule |
|---|---|
| Private O*NET source | Exact task identifier and version, stored privately; public artifacts carry no raw task ID. |
| Family | Occupation family, task type, modality, and authorized weighting stratum. |
| Required inputs | Concrete files, records, facts, constraints, or sensory state needed at task start. Missing professional context must be supplied or declared unavailable. |
| Allowed tools | Named software, search, code, calculator, reference sources, APIs, or no-tools rule. Versions and network permissions are frozen. |
| Deliverable | Observable work product at approximately the same boundary as the O*NET activity. |
| Completion criterion | Necessary conditions for whole-task completion, including format, correctness, compliance, and usability. |
| Scoring rubric | Objective tests where possible; otherwise dimension-level evidence and anchored ratings. |
| Failure criterion | Critical errors, omissions, unsafe outputs, unusable format, and timeout/abstention rules. |
| Review | Who may score, blinding, number of ratings, adjudication trigger, and retained audit evidence. |
| Professional context | Assumed role, knowledge, authority, client/system state, and what is not being simulated. |

An item author may not merely paraphrase the O*NET sentence. The author must
specify a real work product and inputs while keeping the activity at the same
boundary. A narrow activity cannot be expanded into a project, proposal,
multi-day engagement, or composite deliverable. Conversely, an O*NET activity
whose natural unit is a complete inspection or statement cannot be reduced to
one convenient substep and still be called the full task.

`dax/mapping/onet_benchmark_v3_contract.py` enforces definition/evaluation
separation and prevents non-evaluable tasks from being zero-filled.

## C. Sampling alternatives and decision dimensions

Sampling must precede model results and use known, nonzero inclusion
probabilities. Candidate options are not ranked by expected model success.

| Option | Proposed size (unsigned) | Design | Statistical consequence | Operational consequence / selection-bias risk |
|---|---:|---|---|---|
| S1: balanced construct pilot | `n=120` source tasks | Draw within major-family × modality/task-type strata with known probabilities; use only to validate task-boundary, evaluability, inputs, and scoring protocol. | Not powered as the production occupation-level estimator; yields early construct and workflow failure rates. | Lowest initial burden. Deliberately balanced selection is not population representative unless weighted; it must not become the production sample merely because models do well. |
| S2: stratified PPS production sample | `n=384` source tasks | Stratify by major occupation family, task type, and evaluability class; sample with probability proportional to authorized task mass or signed wage-bill relevance. | Under SRS, binary worst-case half-width is about ±5 percentage points at 95%; survey design effects, repeated instances, and family estimates widen it. Use design weights and finite-population correction. | Moderate construction/capture burden. PPS can thin rare/low-mass families; strata/minimums must be frozen. Frame exclusions and unavailable systems can bias the identified subset. |
| S3: two-phase probability design | Phase 1 `n=1,067`; Phase 2 `n=384` | Phase 1 classifies construct/evaluability on a representative draw. Phase 2 fully constructs/scorers a predeclared subsample using inclusion probabilities, cost and strata—never model success. | Phase 1 worst-case SRS half-width is about ±3 points for evaluability shares; Phase 2 retains the ±5-point planning scale for performance. Requires two-phase weights and variance. | Higher review but contains construction costs. Misclassification/nonresponse and incorrect two-phase weights are key risks; outcome-adaptive enrichment is forbidden. |
| S4: census of eligible frame | Up to all `15,274` task-mass-usable records, after task/frame reconciliation | Construct every task classified as benchmark-evaluable and retain all other mass as non-evaluable. | Removes benchmark sampling error within the classified frame but not item, scoring, or classification error. | Prohibitive workload and historical-call burden; feasibility filtering may still create an externally invalid digital subset. |

The proposed sizes are planning alternatives, not signed production choices.
The `n=384` and `n=1,067` figures come from worst-case simple-random binary
precision; they are not reverse-engineered from observed model performance.
Clustering, repeated instances, family estimates, unequal weights, and
classification error change the required final size.

Decision dimensions are: target population; task-mass versus wage-bill target;
precision for total and family estimates; required family/modality contrasts;
design effect; item/repetition hierarchy; treatment of duplicate O*NET tasks;
historical-model call burden; and maximum expert workload. The existing 90%
gate is a **CPS/O*NET crosswalk mapped-component-mass gate**. It is not a
signed benchmark sample-coverage requirement. The v2 80% task-mass and 70%
family validation thresholds govern frozen v2 and are not silently inherited
by v3. A v3 coverage rule therefore requires a new prospective PI decision.

## D. Model-evaluable taxonomy and bounds

Classification occurs before task construction or model scoring.

| Class | Meaning | Full-task benchmark treatment |
|---|---|---|
| Directly executable digital | Inputs and deliverable are natively digital and available in the frozen harness. | Evaluable. |
| Executable with provided files/data | Legitimate completion requires supplied files/data that can be lawfully and reproducibly included. | Evaluable if input validity passes. |
| Executable with simulated construct-valid inputs | Real inputs cannot be used, but a frozen simulation preserves the decision, artifact, difficulty, and quality construct. | Evaluable only after construct-validity review; report separately. |
| Requires unavailable proprietary system | Completion depends on inaccessible software, data, permissions, or workflow state. | Non-evaluable, not zero. |
| Requires physical-world action | Success is the physical act or depends materially on unrepresented sensorimotor interaction. | Non-evaluable for full-task capability. A digital subtask is a different estimand. |
| Requires interpersonal interaction | Success depends materially on live reciprocal behavior, trust, negotiation, care, or instruction. | Non-evaluable unless an independently validated interaction simulation is prospectively approved. |
| Otherwise non-evaluable | Legal, safety, observability, context, or construct failure not captured above. | Non-evaluable with reason. |

For occupation `o`, let `L_om` be identified crossing mass and `U_o` all
non-evaluable or otherwise unidentified mass. Without an approved model for
missing mass:

```text
lower_om  = L_om
center_om = NOT IDENTIFIED
upper_om  = L_om + U_o.
```

The upper bound assumes all unidentified mass crosses; the lower bound assumes
none does. A model-based center may be reported only after a separate,
prospective missing-mass model and validation rule are signed. It must not be
called observed DAX. Evaluability-classification error must also be propagated.

## E. Benchmark-construction protocol

### E1. Task definition (before any model is named or run)

1. Draw the source under the signed sampling design and store its inclusion
   probability, task-mass variables, O*NET version, and private task ID.
2. Classify evaluability using only task/context requirements. Two independent
   reviewers resolve uncertain/proprietary/physical/interpersonal boundaries
   under an unsigned rater rule to be approved.
3. Have a qualified domain author specify the work product, start state,
   professional role, inputs, allowed tools, quality constraints, and failure
   consequences. Added information may instantiate underspecified context; it
   may not add unrelated subtasks or remove essential operations.
4. Obtain realistic inputs from public/licensed sources, deidentified project
   materials with authorization, or reproducible synthetic generation.
   Record licenses, transformations, seeds, generators, and expert validity
   review. Do not use confidential/proprietary files without a data agreement.
5. Freeze output format only when it reflects the occupational work product.
   Do not choose a format because a target model handles it well.
6. Control difficulty using source complexity variables (input volume,
   ambiguity, number of constraints, domain depth, allowed time, error cost),
   not pilot model success. Freeze a difficulty band and rejection rule.
7. Create multiple equivalent instances by a registered template/generator.
   Equivalence requires the same operations, deliverable, constraint count,
   difficulty band, and rubric. Preserve seeds and hashes.
8. Conduct leakage checks against public benchmark text, web-searchable answer
   strings, model training disclosures where available, and repository/history
   exposure. Replace compromised items under a predeclared rule without seeing
   comparative model results.
9. Freeze definition JSON, files, rubric, environment, and hashes. Only then
   create an evaluation manifest.

### E2. Model evaluation (separate lineage)

Evaluation records reference the frozen definition hash. They record requested
and returned model IDs, endpoint, parameters, tool/network policy, repetitions,
outputs privately, token use, latency, metered cost, errors, scorer version,
and score. A definition change creates a new version and invalidates earlier
comparability; it is never patched in place after seeing a model output.

## F. Scoring and validation protocol

| Benchmark family | Preferred objective evidence | Rubric evidence when needed |
|---|---|---|
| Structured data/calculation | Schema, unit, reconciliation, formula, tolerance, and deterministic reference checks. | Materiality, assumptions, auditability. |
| Code/system configuration | Unit/integration tests, static checks, sandbox behavior, reproducible build. | Maintainability, security judgment, requirement coverage. |
| Document/report/analysis | Required facts/citations, numerical reconciliation, constraint and format checks. | Reasoning quality, decision usefulness, completeness, professional standard. |
| Design/media/artifact | File validity, dimensions, required elements, accessibility checks. | Fidelity, usability, professional quality under anchored examples. |
| Research/retrieval | Locator resolution, source/date match, factual and citation entailment. | Synthesis, source quality, uncertainty handling. |
| Simulated communication | Required information and prohibited-action checks. | Responsiveness and domain appropriateness; simulation validity must be separate. |

The minimum full-task completion threshold, critical-dimension vetoes, human
rater count, reliability statistic/floor, adjudication trigger, replicate rule,
and contamination exclusion threshold are pending PI choices. They cannot be
chosen after observing historical-model performance.

General validity requirements:

- objective checks dominate where the work product permits them;
- rubric criteria are anchored to observable output evidence and critical
  failures, not general impressions;
- model self-grading can be a diagnostic but never the sole validity criterion;
- scorers are blinded to model identity and economic/outcome data where
  feasible;
- inter-rater reliability and disagreement/adjudication rates are reported;
- scorer code, reference outputs, rubric version, environment, and hashes are
  reproducible; and
- contamination, memorized answer, and answer-key leakage checks are retained.

Desk work using public/synthetic task materials, code tests, and expert review
of artifacts may be possible without recruiting research participants, subject
to BU's institutional determination. Collecting human completion times,
human-with/without-AI performance, identifiable expert ratings, or interaction
behavior may constitute human-subjects research or otherwise require IRB/data
governance review. The project must obtain the applicable institutional
determination before recruitment. No recruitment occurred here.

## G. GDPval's remaining role

GDPval is an external benchmark and construction precedent, not the central
transport layer. Permitted prospective uses are:

- convergent validity after both benchmarks are independently scored;
- model-vintage sanity checks on broad capability trends;
- descriptive capability-family comparisons clearly separated from DAX; and
- examples of professional inputs, deliverables, and rubric design, subject to
  its unresolved license/redistribution status.

A GDPval whole-task score cannot be copied, scaled, or averaged into an O*NET
task probability without new held-out validation of performance transfer at
the same task boundary. `F` remains descriptive/sensitivity evidence only.

## H. Historical-model capture plan and urgency

For the planning assumptions used only to compare designs—two equivalent
instances, three repetitions, and no perturbations—define the per-model call
vectors:

```text
K_S1 = 120   * 2 * 3 =    720
K_S2 = 384   * 2 * 3 =  2,304
K_S3 = 384   * 2 * 3 =  2,304  (Phase 1 classification makes no model call)
K_S4 = 15,274 * 2 * 3 = 91,644
```

Each technically available registry row requires the applicable `K_S*` calls;
blocked/excluded rows require zero calls unless a new signed rule makes them
eligible. These multipliers and sizes are planning proposals, not authorization.
For each direct row, estimated API cost is `K_S* × rho_m`, where `rho_m` is the
metered cost of that frozen item/token profile at the model's signed price.
For each stand-in row it is `K_S* × rho_host`. Exact row-level rates are not
currently supported across the registry because the project has unprobed rows,
unconfigured stand-in hosting, and a documented 2x price-table conflict.
Blocked/excluded rows cost zero unless prospectively unblocked.

Project-known status comes from `dax/capability_panel/vintage_registry.json`
and the 2026-08-21 free-probe receipt: no account metadata probe was made; 14
direct rows remain unprobed, two stand-in providers are unconfigured, five
aliases lack an approved snapshot rule, and one model is bindingly excluded.

| Event / exact measurement target | Provider | Project-known status / technical possibility | Expected calls | Documented capture risk |
|---|---|---|---:|---|
| GPT4 launch / `meta-llama/Llama-3.1-405B-Instruct` | open-weight compatible | Approved stand-in; provider unconfigured; conditional | `K_S*` if configured | No OpenAI API retirement; hosting availability/cost unresolved. |
| GPT4 Turbo preview / `gpt-4-1106-preview` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Capture before 2026-10-23 per project adjudication. |
| GPT4 Turbo GA / `gpt-4-turbo-2024-04-09` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Capture before 2026-10-23. |
| GPT4o launch / `gpt-4o-2024-05-13` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Capture before 2026-10-23. |
| GPT4o-mini / `gpt-4o-mini-2024-07-18` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Capture before 2026-10-23. |
| o1 preview / `deepseek-ai/DeepSeek-R1` | open-weight compatible | Approved stand-in; provider unconfigured; conditional | `K_S*` if configured | No OpenAI retirement; cross-workload parity limitation retained. |
| o1 full / `o1-2024-12-17` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Capture before 2026-10-23. |
| o3-mini / `o3-mini-2025-01-31` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Project group note: capture before 2026-12-11; reverify exact row. |
| GPT4.5 preview / no target | none | Binding exclusion; technically not eligible | `0` | No qualified stand-in. |
| GPT4.1 / `gpt-4.1-2025-04-14` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Capture before 2026-12-11. |
| o3 / `o3-2025-04-16` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Project group note: capture before 2026-12-11; reverify exact row. |
| o4-mini / `o4-mini-2025-04-16` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Exact retirement deadline not documented in current project evidence; urgent probe. |
| GPT5 / `gpt-5-2025-08-07` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Capture before 2026-12-11. |
| GPT5.1 / `gpt-5.1-2025-11-13` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Project older-GPT5 group note points to 2026-12-11; exact row needs revalidation. |
| GPT5.2 / `gpt-5.2-2025-12-11` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Same group risk; exact row needs revalidation. |
| GPT5.4 / `gpt-5.4-2026-03-05` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Project note says older 5.4 snapshots before 2026-12-11; exact row needs revalidation. |
| GPT5.4-mini / no approved dated target | OpenAI | Blocked alias; not technically authorized | `0` | Snapshot rule needed; alias drift risk. |
| GPT5.4-nano / no approved dated target | OpenAI | Blocked alias; not technically authorized | `0` | Snapshot rule needed; alias drift risk. |
| GPT5.5 / `gpt-5.5-2026-04-23` | OpenAI | Account probe required; unverified possible | `K_S*` if available | Project note says older 5.5 snapshots before 2026-12-11; exact row needs revalidation. |
| GPT5.6-sol / no approved dated target | OpenAI | Blocked alias; not technically authorized | `0` | Snapshot rule needed; current alias is not a historical capture. |
| GPT5.6-terra / no approved dated target | OpenAI | Blocked alias; not technically authorized | `0` | Snapshot rule needed. |
| GPT5.6-luna / no approved dated target | OpenAI | Blocked alias; not technically authorized | `0` | Snapshot rule needed. |

As of 2026-08-23, the first documented deadline is 2026-10-23. The execution
DAG should therefore be:

```text
PI decisions -> sampling + task/rubric construction -> benchmark freeze
       -> historical model capture -> scoring/capability estimates ----+
                                                                    join -> frontier -> W5
benchmark freeze -> human duration/governance -> duration estimates ---+
```

Duration need not delay capability capture because the frozen task definition
identifies the unit for both branches. Duration is required before the economic
frontier, not before model output capture. Paid inference remains prohibited
until the benchmark and budget are signed.

## I. Expected construction and inference costs

An honest dollar expectation is not yet identified because sample size,
instances, repetitions, perturbations, token caps, expert rates, review rules,
provider access, and several price lines are unsigned or unresolved. Filing a
single budget now would manufacture precision. The packet instead freezes the
cost equations and illustrative workloads for PI budgeting.

Construction workload:

```text
H_construct = N_items * (H_author + H_domain_review + H_rubric_QA + H_leakage_QA)
H_score     = N_captured_outputs * N_human_raters * H_rating
Cost_human  = sum_role H_role * approved_rate_role.
```

The following planning table makes the alternatives comparable. Construction
assumes 3.5 expert-hours per fully constructed item; the S3 Phase-1 screen
assumes 0.25 hour per source. Inference assumes two instances, three
repetitions, no perturbations, and the 16 registry rows that are direct-but-
unprobed or approved-stand-in-but-unconfigured. The USD sensitivity assumes
5,000 noncached input and 1,000 output tokens per call and applies the
project's documented low/high direct rate examples (`$0.15/$0.60` through
`$30/$60` per million). It excludes hosting, tools, human scoring, retries,
and unresolved price changes.

| Design | Construction workload | Calls per model | Calls across initial 16 rows | Direct-API price sensitivity only |
|---|---:|---:|---:|---:|
| S1 `n=120` pilot | 420 expert-hours | 720 | 11,520 | about `$16–$2,419` |
| S2 `n=384` PPS | 1,344 expert-hours | 2,304 | 36,864 | about `$50–$7,741` |
| S3 `1,067 -> 384` two-phase | about 1,611 expert-hours | 2,304 | 36,864 | about `$50–$7,741` |
| S4 `n=15,274` census scale | 53,459 expert-hours | 91,644 | 1,466,304 | about `$1,980–$307,924` |

If five blocked aliases later receive signed routes, multiply the relevant
per-model calls by 21 rather than 16; the excluded GPT4.5 row remains zero.
If all 1,067 S3 phase-1 tasks were later fully constructed, the scale would be
6,402 calls per model, 102,432 over 16 rows, and roughly `$138–$21,511` under
the same illustrative token/rate assumptions. None of these calls or dollar
ranges is an authorization or budget recommendation.

Metered inference cost is

```text
sum_calls[((input-cached)*input_rate + cached*cached_rate
           + output*output_rate) / 1,000,000] + tool charges.
```

Before budget signature, a no-inference preflight should pin current price
lineage, resolve the documented 2x price-table conflict, tokenize frozen items,
and calculate a high-case cap by model. The historical USD 650 W4 estimate and
the USD 60 v2-labeling budget do not automatically authorize this new benchmark.

## J. Governance and human-review requirements

- Keep O*NET task IDs, constructed instances, model outputs, expert ratings,
  and duration records in owner-only private storage until licensing/privacy
  rules permit release; ship hashes, schemas, and aggregate receipts.
- Obtain license/data-use review for O*NET distributions, input files,
  proprietary systems, GDPval precedents, and third-party reference material.
- Obtain BU IRB or institutional determination before recruiting people for
  duration, performance, or AI-assistance studies; obtain consent and a data
  retention plan if required.
- Require domain-qualified item authors and independent reviewers. Required
  counts, credentials, reliability thresholds, and adjudication rules remain
  prospective PI decisions.
- Blind reviewers to model identity and DAX outcomes where possible; preserve
  conflicts and adjudication rather than overwriting them.
- Pre-register safety exclusions for tasks whose evaluation would require
  unlawful access, dangerous action, real patient/client intervention, or
  uncontrolled physical execution.
- Maintain the existing outcome seal until measurement design, benchmark,
  model capture, scoring, duration, and W5 rules are frozen.

## K. Comparison against Alternatives A/B/C/D

| Design | Estimand and measurement unit | Assumptions / identification | Expected coverage and validity risk | Complexity, cost, interpretation, and departure |
|---|---|---|---|---|
| A: strict direct-task substitution | Existing full-task frontier; unit is an independently equivalent GDPval/O*NET task pair. | Exchangeable inputs, operations, deliverable, quality, duration, cost, and failure consequence; independent D adjudication. | Very sparse, selected coverage. Lowest semantic false-link risk, but hidden context differences remain. | Moderate per link but high cost per covered mass. Most interpretable lower bound; new sparse-coverage/partial-identification amendment. |
| B: capability-family exposure | Latent family capability by occupation task loading; not full-task displacement. | Stable ontology, measurement invariance, common-item calibration, and out-of-domain predictive validation. | Broad semantic coverage but high risk of false economic transfer; family involvement does not identify task success/time saving. | Moderate/high measurement-model cost. Interpretable as capability exposure only; major estimand departure if central. Descriptive/sensitivity role only. |
| C: atomic decomposition | Either assembled full-task success or partial minutes saved; unit is an atomic component/task graph. | Complete reproducible decomposition, valid dependencies/assembly operator, component performance transfer, component duration and review time. | Potentially broad apparent coverage; high false-link and external-validity risk if generic atoms or dependencies are wrong. | Highest ontology, human-duration, and validation cost. Mechanistic but complex; major methodology deviation and possible estimand change. Not primary. |
| D: O*NET-aligned benchmark | Existing full-task cost-effective frontier; unit is a frozen benchmark instance at the O*NET task boundary. | Probability sampling, construct-valid instances, equivalent repetitions, objective/independent scoring, and sample-to-task/occupation external validity. | Coverage determined by signed sample and evaluability bounds, not semantic retrieval. Lower cross-unit false-link risk; principal risks are construct validity, digital selection, and sampling error. | Highest new data-construction and historical-capture burden, but direct interpretation. Major measurement/data-source amendment. Preferred prospective primary direction, not yet implementation-approved. |

Strict-D mass is never renormalized to the full occupation. It may provide a
conservative identified subset, occupation lower bound, and falsification:
O*NET-aligned performance should not be systematically less coherent than
performance on genuinely equivalent direct links. The single plausible D among
108 qualitative candidates for six new sources is evidence that D is not
logically empty, not evidence of prevalence or transport validity.

## Preregistration/deviation analysis

| Aspect | Classification | Consequence |
|---|---|---|
| Full-task cost-effective crossing estimand | Preservation of original substantive estimand | Keep full deliverable, human cost, AI/tool cost, failure and review costs explicit. |
| Measuring at O*NET task boundary | Measurement redesign caused by discovered unit mismatch | Major prospective amendment before implementation. |
| Constructed O*NET-aligned instances/files/rubrics | New data construction | Freeze provenance, licenses, generators, context and version hashes. |
| Probability sample and coverage rule | New sampling decision | PI must sign frame, strata, weights, precision/sample-size rule, and missing mass treatment. |
| Completion threshold and human scoring | New scoring decision | PI must sign thresholds/rater/reliability/adjudication rules before results. |
| Generalizing sampled instances to tasks/occupations | New external-validity assumption | Validate instance representativeness and propagate sampling/item uncertainty. |
| Historical model routes/stand-ins | Existing registry plus new benchmark application | Reconfirm availability, snapshot rules, price lineage and stand-in caveats. |
| Capability-family central treatment | Major estimand deviation | Not selected; descriptive only unless separately amended and validated. |
| Strict-D robustness | New sparse lower-bound implementation | Prospective amendment; does not replace central sample. |

The redesign is motivated and preserved by: v1 had zero accepted mappings and
approximately 0.19% coverage; v2's preliminary development diagnostic was
`0/60 D`, `24/60 F`, `36/60 N`; and the separate source-side qualitative audit
found one plausible D among 108 candidates for six new O*NET sources. The
redesign occurs while outcomes remain sealed and before W5, identification,
power, or outcome analysis.

## L. Exact prospective PI decisions required before implementation

No line below is approved until dated and signed.

### PI decision form 1 — estimand and workflow boundary

| Decision | PI entry |
|---|---|
| Central capability mode: autonomous full-task or specified AI-assisted workflow | `NEED_HUMAN` |
| Minimum full-task reliability `p_star` and whether critical failures veto crossing | `NEED_HUMAN` |
| Failure-loss definition `L_t` and human review/retry/residual-time costing | `NEED_HUMAN` |
| Whether partial minutes saved is reported only descriptively or as a separately named secondary estimand | `NEED_HUMAN` |

### PI decision form 2 — sample and coverage

| Decision | PI entry |
|---|---|
| Eligible O*NET frame and duplicate/link handling | `NEED_HUMAN` |
| Sampling option S1/S2/S3/S4 or signed hybrid | `NEED_HUMAN` |
| Target precision/design effect or cell minimums that determine sample size | `NEED_HUMAN` |
| Task-mass versus wage-bill target and authorized weighting variables | `NEED_HUMAN` |
| V3 task-mass and occupation-family coverage/reporting gate | `NEED_HUMAN` |
| Non-evaluable classification-review rule and whether any model-based center will be developed | `NEED_HUMAN` |

### PI decision form 3 — construction, scoring, and governance

| Decision | PI entry |
|---|---|
| Item-author/reviewer qualifications and number of independent reviews | `NEED_HUMAN` |
| Instance count/equivalence rule and difficulty-control rule | `NEED_HUMAN` |
| Scoring threshold, critical dimensions, reliability floor, and adjudication trigger | `NEED_HUMAN` |
| Contamination exclusion/replacement rule | `NEED_HUMAN` |
| BU governance/IRB determination and private-data retention/release plan | `NEED_HUMAN` |

### PI decision form 4 — historical capture and budget

| Decision | PI entry |
|---|---|
| Exact included registry rows and disposition of five blocked aliases | `NEED_HUMAN` |
| Repetitions, perturbations, token/output caps, timeout and failure policy | `NEED_HUMAN` |
| Benchmark-freeze deadline relative to the documented 2026-10-23 retirements | `NEED_HUMAN` |
| Frozen price lineage, per-model high-case cap, total inference budget, and stop rule | `NEED_HUMAN` |
| Stand-in hosting/provider and whether stand-ins remain central or sensitivity-only | `NEED_HUMAN` |

### PI decision form 5 — auxiliary designs

| Decision | PI entry |
|---|---|
| Strict-D sampling/adjudication rule and lower-bound presentation | `NEED_HUMAN` |
| GDPval convergent-validity analyses permitted | `NEED_HUMAN` |
| Capability-family descriptive outputs permitted and labeling restrictions | `NEED_HUMAN` |

**PI name/signature:** `NEED_HUMAN`

**Date:** `NEED_HUMAN`

**Decision version/commit:** `NEED_HUMAN`

## M. Recommended next step

The scientifically defensible next step is a **no-model, outcome-blind
construct-validity pilot on the prospectively drawn S1 `n=120` tasks**, after
the PI signs the task boundary, sampling frame, evaluability rules, author and
review qualifications, and the rule for rolling valid pilot items into a
production probability sample. The pilot should ask only whether independent
domain reviewers can reproducibly construct and score an instance at the same
O*NET work-product boundary. It must not inspect model performance or optimize
the protocol for apparent AI success.

If that construct gate passes under a prospectively signed rule, the preferred
production planning option is S3: classify `n=1,067` probability-drawn tasks
and fully construct a predeclared `n=384` two-phase subsample with retained
inclusion probabilities. Valid S1 items may roll into the relevant probability
sample only if their selection probabilities and unchanged definitions permit
it. The benchmark, price/call cap, and scoring rule should then be frozen early
enough to capture the 2026-10-23 historical snapshots. Human duration may
continue in parallel and join only before the economic frontier.

This recommendation is based on construct validity, explicit missing-mass
bounds, and historical-capture risk. It is not based on expected coverage or
model success, and it is not a PI signature, recruitment approval, or spending
authorization.

# Mapping A v3 prospective decision packet — 2026-08-23

**Status:** `NEED_PROSPECTIVE_PI_DECISION`; no production method selected.

**Hard boundary:** Mapping A v2 remains unchanged and unvalidated. This packet
does not spend the USD 60 labeling budget, open the locked test, fit the v2
classifier, relabel any v2 pair, or change a v2 threshold, feature, candidate
rule, taxonomy, transport equation, or receipt.

## 1. What the v2 diagnostic actually says

The preliminary single-Codex diagnostic remains `D=0`, `F=24`, `N=36`, and
`U=0` over 60 development/calibration pairs. Manual cause coding and mechanical
unit diagnostics point to a cross-level measurement failure, not a reason to
relax `D`.

### 1.1 Structural counts

Primary causes are mutually exclusive; the remaining counts overlap.

| Cause | Pairs | Interpretation |
|---|---:|---|
| Capability family without task substitutability | 24 | All `F` pairs share a material skill or workflow, but the GDPval completion does not perform the O*NET task end to end. |
| Work-modality mismatch | 27 | A physical, interpersonal, or in-situ O*NET activity is paired with an artifact-producing, spreadsheet, report, policy, or software GDPval task. |
| Wording/domain false friend | 9 | Shared words, occupation context, or a generic analytical verb retrieve a different work product. |
| Granularity mismatch | 60 | Every GDPval record is a composite benchmark assignment; every sampled O*NET record is one shorter occupational activity. |
| End-to-end deliverable versus narrow activity | 60 | GDPval scores the complete deliverable and rubric; O*NET describes an activity embedded inside a job. |
| One-to-many decomposition required | 60 | Each GDPval assignment contains multiple operations, artifacts, constraints, or checks. |
| Many-to-one aggregation in the measurement | 60 | One GDPval score aggregates those components, so the score cannot identify performance on one O*NET component. |
| Pair-level retrieval failure | 36 | These are the unchanged `N` judgments. This does not prove that no better candidate exists elsewhere. |
| Occupation-context mismatch | 36 | The `N` pairs do not preserve the source task's operative setting and constraints. |
| Taxonomy definition alone too strict | 0 | No inspected pair was near-direct except for the fact that the `D` definition demanded the same actual task. |

The median O*NET statement is 14 words; the median GDPval prompt is 276 words
and its median rubric is another 780 words. The median prompt-to-statement ratio
is 19.01. Length is not itself scientific proof, but here it mechanically
documents the abstraction gap.

Sanitized archetypes make the distinction concrete:

- a narrow physical preparation/cleaning/loading activity retrieves a
  managerial proposal, spreadsheet, or workflow document in the same domain;
- a repair-cost activity retrieves budgets and quotations that use costing
  skills but do not estimate a repair;
- patient interviewing retrieves intake templates, handover records, and care
  plans that use patient information but do not conduct the interview;
- lexical false friends match different meanings of words such as “layout” or
  different status-review activities.

The development-only source audit confirms that `D` is not logically empty.
Across six prospectively selected sources and all 108 candidates in the union
of dense top-10, lexical top-10, and RRF top-10, one plausible `D` was found:
an O*NET machinery/equipment CAD-drawing activity paired with a GDPval task
requiring component CAD models and engineering drawings. The other qualitative
judgments were 55 `F` and 52 `N`. These are not prevalence, recall, PPV, or
validation estimates. They show only that direct matches can occur when the
work product and abstraction level happen to align, while five of six audited
sources had none in the inspected candidate union.

### 1.2 Dominant explanation

The dominant cause is **granularity and measurement-unit mismatch**, expressed
as end-to-end benchmark deliverables versus narrow occupational activities.
Retrieval false links compound the problem, especially for physical and
interpersonal tasks, but retrieval alone is not the full explanation: many of
the best candidates are genuinely family-related and still cannot support
quantitative task substitution. The diagnostic provides no evidence that the
taxonomy should be weakened.

## 2. Audit of the underlying units

Let `o` denote an occupation, `t` an O*NET task, `j` a GDPval task, `a` an
atomic capability/component, and `m` a model vintage.

| Object | Actual unit | What is observed | What is not observed |
|---|---|---|---|
| O*NET task `t` | A named occupational activity linked to one or more O*NET-SOCs | statement, occupation link, relevance/time-share and consequence inputs | benchmark instance, model success probability, task-specific AI cost, component durations |
| GDPval task `j` | A composite professional assignment ending in one or more rubric-scored artifacts | prompt, files, rubric, occupation/sector label | which atomic components drive success, O*NET task identity, component-level performance |
| GDPval capability `q_jm` | Model-vintage performance on the complete GDPval assignment | whole-assignment success/capability and uncertainty | performance on a particular O*NET activity inside or adjacent to the assignment |
| Desired DAX treatment `DAX_om` | Occupation-month wage/task-mass share crossing the cost-effective full-task displacement frontier | requires `pi_tm`, AI cost, human task wage/duration, failure cost, and O*NET task weight | cannot be obtained from semantic similarity or whole-GDPval performance alone |

They are not at the same abstraction level. The missing bridge is an estimable
cross-level measurement operator, not another cosine threshold. A complete
bridge needs:

1. `R_ja`: which atomic components GDPval task `j` requires and their roles;
2. `S_ta`: which components O*NET task `t` requires and their roles;
3. `theta_am`: model-vintage capability on component `a`, linked across
   benchmark and occupational contexts;
4. `G_t(.)`: a prospectively fixed task-assembly rule converting component
   performance into full O*NET-task success `pi_tm`;
5. `h_ta`: human active minutes by O*NET component, rather than unallocated
   duration of the whole GDPval deliverable;
6. `c_tam`: AI token/tool/review cost by component and model vintage; and
7. an external-validity calibration for domain, tools, input files, quality,
   orchestration, and failure consequences.

V2 attempts to move directly from `q_jm` to `pi_tm`. A semantic relation—D or
F—does not by itself estimate this operator.

## 3. Prospective Mapping A v3 alternatives

No option is selected here, and none is ranked by expected coverage.

### Alternative A — direct-task substitution

- **Estimand:** the existing full-task displacement frontier, but only for
  O*NET tasks with independently verified benchmark-equivalent tasks.
- **Mapping unit:** O*NET task `t` to GDPval task `j`.
- **Assumptions:** `D` means exchangeable work product, operations, inputs,
  domain constraints, quality criterion, and task boundary; model success,
  AI cost, human duration, and failure consequences transfer after named
  adjustments.
- **Candidate generation:** full-pool dense/lexical/structured retrieval,
  augmented prospectively with verb-object-artifact and input/output schema
  matching. Occupation can be a feature, never a hard blocker.
- **Taxonomy:** `D_exact`, `D_adjustable`, `N`, `U`; `F` remains a noncentral
  diagnostic. `D_adjustable` requires a pre-specified quantitative adjustment,
  not annotator intuition.
- **Transport:** for audited `D_exact`, `pi_tm=q_jm`; for multiple replicate
  benchmark items, combine using a prospectively calibrated replicate model,
  not simple renormalization. Unmapped `t` stays unidentified. An adjustable
  link uses `pi_tm=L(q_jm,x_t,x_j)` learned only from bridge experiments.
- **Model capability:** whole-task GDPval capability enters only through an
  exchangeable direct link.
- **Duration:** use `h_j` only when the human task boundary is also
  exchangeable; otherwise collect `h_t`. AI cost must be recomputed for the
  O*NET-equivalent instance.
- **Uncertainty:** relation adjudication, bridge adjustment, model score,
  duration, and cost are jointly resampled; unmatched task mass stays explicit.
- **False-positive risk:** lowest of the three core options if equivalence is
  strictly enforced; still vulnerable to hidden input/quality differences.
- **Coverage risk:** very high and scientifically real; partial identification
  or a deliberately narrow estimand may result.
- **Interpretability:** highest for full-task displacement.
- **Feasibility/cost:** moderate per audited link but potentially high per unit
  of covered task mass because direct links are sparse.
- **Deviation status:** new v3 methodology and partial-coverage rule require a
  prospective PI amendment, although the economic estimand is retained.

### Alternative B — capability-family transport

- **Estimand:** occupation exposure to model-accessible latent capability
  families, not the share of full tasks that AI can privately displace.
- **Mapping unit:** GDPval task `j` to capability `a`, and O*NET task `t` to
  capability `a`; no direct `j -> t` claim.
- **Assumptions:** a stable capability ontology exists; capability loadings are
  measurement-invariant across GDPval and O*NET contexts; benchmark tasks
  identify each latent capability; and family scores are comparable across
  model vintages.
- **Candidate generation:** expert ontology plus structured extraction of
  operations, artifacts, tools, and quality criteria; retrieve within atomic
  capability descriptions rather than whole-task text.
- **Taxonomy:** `required_core`, `required_supporting`, `incidental`, `absent`,
  `uncertain` for each task-capability link.
- **Transport:** estimate family capability `theta_am` from multiple GDPval
  items, then define a new exposure, for example
  `CAX_om=sum_t omega_ot * sum_a lambda_ta * theta_am`. This is not `DAX_om`
  and cannot be inserted into the old crossing equation under a new name.
- **Model capability:** item-response or hierarchical measurement links
  multiple GDPval items to each `theta_am`.
- **Duration:** GDPval duration does not transfer. O*NET task/component minutes
  are required if the estimand includes time-weighted capability exposure.
- **Uncertainty:** ontology links, factor/loadings, item scores, context drift,
  task weights, and duration are propagated hierarchically.
- **False-positive risk:** medium to high if broad families hide different
  artifacts, difficulty, tools, or contexts.
- **Coverage risk:** lower semantic coverage risk, but coverage does not equal
  full-task displacement coverage.
- **Interpretability:** clear as capability exposure; misleading if described
  as cost-effective task substitution.
- **Feasibility/cost:** moderate to high; requires ontology construction,
  multiple items per capability, and measurement-invariance tests.
- **Deviation status:** major prospective preregistration deviation because it
  changes the treatment estimand and likely the interpretation of all
  downstream coefficients.

### Alternative C — atomic task decomposition

- **Estimand:** either (C1) probability/cost of complete O*NET-task execution
  assembled from required components, or (C2) expected human active minutes
  saved through partial component automation. C1 and C2 are distinct and must
  be chosen prospectively.
- **Mapping unit:** atomic component `a`, with `R_ja` and `S_ta` bridge matrices.
- **Assumptions:** decompositions are complete and reproducible; dependency and
  ordering structure is observed; component capability transfers across
  context after calibration; and the assembly operator reflects serial,
  parallel, bottleneck, and review work.
- **Candidate generation:** parse prompts, rubrics, reference-file operations,
  deliverables, and O*NET statements into a controlled verb-object-artifact-
  tool-criterion schema, followed by expert reconciliation.
- **Taxonomy:** `same_atomic_operation`, `same_output_different_context`,
  `prerequisite`, `supporting`, `unrelated`, `uncertain`.
- **Transport:** for C1, a registered task graph `G_t({theta_am})` produces
  `pi_tm`; a simple product or minimum is not accepted without evidence. For
  C2, `saved_minutes_tm=sum_a h_ta*s_tam - review_minutes_tm`, bounded at
  `[0,h_t]`.
- **Model capability:** component-level scores are estimated from decomposed
  GDPval rubric items or new bridge items; whole-assignment scores are used as
  validation constraints, not automatically copied to components.
- **Duration:** allocate human active minutes to components with qualified
  annotations or time-motion data; include orchestration, checking, retries,
  and integration.
- **Uncertainty:** resample decompositions, component links, task graphs,
  capability, durations, dependencies, and review/failure costs.
- **False-positive risk:** high if generic atoms such as “analyze” or “write”
  are matched without artifact/domain constraints.
- **Coverage risk:** potentially lower, but only if decomposition reliability
  is demonstrated; otherwise apparent coverage is synthetic.
- **Interpretability:** high for partial time savings when components are
  observable; more complex for full-task displacement.
- **Feasibility/cost:** highest of the three core options due to ontology,
  decomposition, component measurement, and time allocation.
- **Deviation status:** major prospective methodology deviation; C2 also
  changes the estimand from full-task displacement to partial time savings.

### Alternative D — build an O*NET-aligned bridge benchmark

- **Estimand:** the existing full-task displacement frontier on a sampled,
  explicitly defined set of O*NET tasks.
- **Mapping unit:** multiple benchmark instances created directly for each
  sampled O*NET task; semantic transport becomes an external-validity problem
  within task rather than across unrelated units.
- **Assumptions:** constructed instances represent real occupational inputs,
  quality standards, tools, and failure consequences; sampling/task weights
  support the intended occupation-level inference.
- **Candidate generation/taxonomy:** no GDPval-to-O*NET candidate retrieval;
  instead audit each instance as representative, marginal, or invalid for `t`.
- **Transport:** estimate `pi_tm` directly from multiple O*NET-aligned items,
  with hierarchical shrinkage only under prospectively tested exchangeability.
- **Capability/duration:** model performance and token/tool cost are measured on
  those items; qualified humans provide task-instance completion times and
  human-with/without-AI time trials.
- **Uncertainty:** benchmark sampling, item difficulty, human/model variation,
  task representativeness, duration, and cost all propagate to `DAX_om`.
- **Risks:** lower semantic false-link risk; high construct-validity and sample-
  coverage risk if the new instances are unrealistic or too few.
- **Interpretability:** high if instance validity is documented.
- **Feasibility/cost:** very high; requires task materials, licensing/privacy,
  humans, model runs, and likely governance review.
- **Deviation status:** major new measurement-data-source amendment.

## 4. When an F relation can have economic meaning

An `F` judgment establishes only that a material capability or workflow is
shared. It can support quantitative transport only if three separate evidentiary
layers are satisfied:

1. **Capability involvement:** blinded experts reproducibly identify the same
   operation, artifact, tool, and quality dimension in `j` and `t`.
2. **Performance transfer:** within an independently held bridge sample,
   model-vintage performance on `j` predicts performance on O*NET-aligned `t`
   after task difficulty, domain, tools, files, output format, and quality are
   controlled. Calibration must hold out of family/domain and across vintages.
3. **Economic/time transfer:** human-without-AI minutes, human-with-AI minutes,
   model/tool cost, checking/retry time, and failure consequences are measured
   for `t`. Similar model accuracy does not imply similar time savings or
   privately cost-effective substitution.

Exact assumptions required for F-based central treatment are:

- conditional exchangeability of model performance within the named family;
- measurement invariance and common-item calibration across GDPval and O*NET;
- overlap in difficulty, inputs, tools, artifacts, and quality criteria;
- a registered functional form for context adjustment and task assembly;
- no unmeasured family-by-domain or model-vintage interaction after adjustment;
- separately validated O*NET task/component durations and review time;
- AI inference/tool cost and failure loss assigned at the O*NET task boundary;
- calibrated uncertainty wide enough to include transport and context error.

Without all three layers, `F` may inform an upper-bound or descriptive
capability sensitivity only. It cannot support the current central full-task
crossing indicator.

## 5. Evidence that would distinguish the alternatives

1. Build a small, prospectively sampled set of O*NET-aligned bridge items across
   physical, interpersonal, analytical, and technical tasks.
2. Have qualified humans independently validate direct equivalence, atomic
   decompositions, capability-family membership, and task representativeness.
3. Measure several model vintages on both GDPval and bridge items to estimate
   direct-link and family-level out-of-domain calibration.
4. Run qualified-human completion and human-with-AI time studies on the bridge
   tasks, recording quality, review, retry, orchestration, and failure time.
5. Test whether a registered family model predicts held-out O*NET item
   performance and time savings; semantic agreement alone is insufficient.
6. Compare A/B/C/D on the same pre-outcome bridge sample using construct
   validity, calibration error, uncovered task mass, and uncertainty width—
   never by selecting the option that happens to maximize coverage.

## 6. Decisions requiring a prospective PI amendment

Every v3 option requires a signed decision before new labels or measurement:

- **A:** approve intentional sparse/partial coverage, revised taxonomy and
  direct-link transport, and the treatment of unidentified task mass.
- **B:** approve a new capability-exposure estimand, ontology, measurement
  model, and revised causal interpretation.
- **C:** choose C1 versus C2, approve component ontology/decomposition,
  assembly/time-saving equation, and duration protocol.
- **D:** approve a new benchmark/data source, sampling frame, licensing/privacy
  plan, human/model budget, and external-validity gate.
- **Any F central use:** separately approve the bridge-study design and numeric
  calibration/transport acceptance rules before observing its results.

No choice is made automatically in this packet.

## 7. Value of the USD 60 formal v2 validation

Spending the USD 60 now would add a more precise description of F/N frequencies
and could confirm that rare D links exist. It would not identify the missing
cross-level operator, validate F performance transfer, provide O*NET task
durations, or show that human time savings transfer. With 0/60 D in the first
diagnostic and only one plausible D across 108 candidates for six new sources,
the frozen v2 classifier is likely to have too little positive support for its
intended calibration.

Therefore the formal v2 run would currently add meaningful information mainly
as a falsification/measurement-documentation exercise, not as a credible path
to production approval. The USD 60 remains unspent.

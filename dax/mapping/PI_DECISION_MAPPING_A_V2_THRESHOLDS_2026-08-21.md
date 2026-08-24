# PI decision packet: Mapping A v2 validation thresholds — 2026-08-21

**Decision state:** `PI_APPROVED_PROSPECTIVELY` at decision commit
`4577fecab7b4e142cb28d78d4aec0800637c7b05`. This packet was written without
opening any development, calibration, or locked-test relation labels and
without inspecting validation metrics. It authorizes no Mapping A production
use. Locked-test labels must remain sealed until the method, metrics, and all
numeric choices below are committed and signed.

The binding selections are PPV >=0.95; FPR <=0.05; candidate recall@40 >=0.95;
adjudication <=0.20; task-mass-weighted coverage >=0.80; independently binding
family coverage >=0.70; PI-15 transport bounds; and conservative `U` treatment
as non-`D`. The machine-readable copy is
`mapA_v2_binding_thresholds_20260821.json`.

## 1. Fixed measurement definitions

All metrics are computed separately on calibration and locked-test splits.
Locked-test results are opened only once after the signed thresholds are
recorded. Report both unweighted and 2021 task-mass-weighted versions where a
task mass exists; the signed gate must state which version is binding.

| Metric | Frozen definition before labels open |
|---|---|
| Direct-substitute PPV | Adjudicated `D` pairs among pairs that the frozen classifier/calibrator predicts as `D`. Report numerator, denominator, and a binomial confidence interval. |
| Direct-substitute false-positive rate | Pairs predicted `D` but finally adjudicated `F`, `N`, or `U`, divided by all finally adjudicated non-`D` pairs. Counting `U` against the method is the conservative rule; changing that treatment requires a signed choice below. |
| Candidate recall at `k` | Among all adjudicated `D` relations found by reviewing the complete 220-target pool for sampled O*NET tasks, the share appearing in the frozen candidate union by rank `k`. Report the grid `k={5,10,20,40,80,220}`; the PI selects one binding `k` and floor prospectively. |
| Adjudication rate | Pairs sent to the third-family adjudicator because the first two labels disagree or either is `U`, divided by all independently double-labeled pairs. Report disagreement and `U` components separately. |
| Task-mass coverage | Sum of 2021 O*NET task mass for source tasks with at least one accepted `D` relation divided by total eligible task mass. Unresolved tasks remain uncovered; `F` never counts toward central coverage. |
| Occupation-family coverage | The same task-mass coverage computed separately within every observed two-digit major SOC family. Report the minimum, p10, median, and full family table; a binding rule must identify the statistic it constrains. |
| Transport sensitivity | Recompute mapping-only coverage and weights under dense-only, lexical-only, combined retrieval, relation-label resampling, and lower/center/upper transport. Report task coverage changes and, when W4 becomes available, crossing-date/bin and attenuation diagnostics. No outcome is used. |

## 2. Existing signed rules and external methodological support

The literature supports measuring false links, missed links, retrieval recall,
and downstream uncertainty. It does **not** supply context-free numerical
cutoffs for the O*NET-to-GDPval semantic mapping. The candidate menus below are
therefore transparent PI risk choices, not claimed scientific constants.

| Metric | Existing project rule | External justification | Stricter choice | Looser choice |
|---|---|---|---|---|
| PPV | No v2 numeric rule. PI Decision 7 governs reliability, not PPV. | Fellegi–Sunter formalizes the tradeoff between false links and missed links. Saito–Rehmsmeier shows why precision/recall is informative with rare positives. Neither supplies a universal PPV cutoff. | Reduces contamination and false transport; may sharply reduce coverage and increase unresolved mass. | Raises coverage and lowers annotation burden; admits more non-substitutable tasks into central exposure. |
| False-positive rate | No v2 numeric rule. | Fellegi–Sunter treats false-link and missed-link error as separate losses; the acceptable balance depends on downstream cost. | Protects against spurious exposure/crossings; increases false negatives and unresolved tasks. | Recovers more candidate relations; raises attenuation/bias risk from false direct substitutes. |
| Candidate recall | No v2 numeric rule. Full 220-pair scoring is already frozen. | Christen defines pairs completeness as the share of true matches retained by indexing; high completeness protects against irreversible candidate loss. No universal floor or `k` is supplied. | Requires a larger candidate set and more annotation; lowers missed-relation risk. | Reduces annotation cost; can make later PPV look good by omitting hard true relations. |
| Adjudication rate | PI Decision 7 requires 10% stratified human audit, weighted kappa >=0.70, and binary agreement >=90%; no adjudication ceiling. | Agreement/reliability methods justify reporting disagreement, but a high adjudication rate can reflect either rubric ambiguity or appropriately conservative routing. No universal ceiling was located. | Forces a clearer rubric and cheaper production; may punish valid ambiguity and conceal uncertainty if routing is discouraged. | Preserves conservative escalation; raises cost and signals the mapping may not scale. |
| Task-mass coverage | Historical v1 protocol used a 0.70 occupation coverage floor. PI Decision 13 requires >=70% weighted crossed mass downstream. Neither is automatically identical to v2 pre-transport task-mass coverage. | Entity-resolution work recommends reporting both error and coverage; missing links can bias downstream analysis. No universal economic task-mass floor exists. | Improves representativeness; may be infeasible with only 220 benchmark tasks or encourage unsafe mapping if quality gates are not conjunctive. | Permits honest partial coverage; increases selection risk and weakens claims about the whole labor market. |
| Occupation-family coverage | Historical v1 used a 0.70 per-occupation coverage floor; v2 major-family aggregation is a new denominator and needs approval. | Stratified reporting exposes heterogeneous missingness that an aggregate can hide. No universal family floor exists. | Prevents headline coverage from being driven by a few well-represented families; may fail the method because GDPval has uneven domain support. | Allows aggregate progress despite thin families; narrows external validity and requires family exclusions/disclosure. |
| Transport sensitivity | PI Decision 15 already signs downstream EIV diagnostics: median crossing shift <=1 month, p90 <=3 months, <=10% dose-bin changes, attenuation >=0.80. Applying them to v2 requires a signed operational link. | Lahiri–Larsen shows linkage errors affect regression analysis; Enamorado–Fifield–Imai propagates record-linkage uncertainty rather than treating links as certain. Neither provides DAX-specific bounds. | Produces a more stable exposure measure; may reject a scientifically informative but noisy mapping. | Preserves more mappings; makes estimates more dependent on retrieval/transport assumptions. |

Primary methodological locators:

- Fellegi and Sunter (1969), *A Theory for Record Linkage*,
  https://doi.org/10.1080/01621459.1969.10501049
- Christen (2012), *A Survey of Indexing Techniques for Scalable Record
  Linkage and Deduplication*, https://doi.org/10.1109/TKDE.2011.127
- Saito and Rehmsmeier (2015), *The Precision-Recall Plot Is More Informative
  than the ROC Plot When Evaluating Binary Classifiers on Imbalanced
  Datasets*, https://doi.org/10.1371/journal.pone.0118432
- Lahiri and Larsen (2005), *Regression Analysis With Linked Data*,
  https://doi.org/10.1198/016214504000001277
- Enamorado, Fifield, and Imai (2019), *Using a Probabilistic Model to Assist
  Merging of Large-Scale Administrative Records*,
  https://doi.org/10.1017/S0003055418000783

## 3. Prospective menu — no default is selected

Choices are intentionally shown before label access. A PI may select a listed
value or write another value with a rationale. Every quality and coverage gate
is conjunctive; good coverage cannot compensate for failed PPV/FPR/reliability.

| Decision | Prospective choices |
|---|---|
| Binding PPV floor | `>=0.90` / `>=0.95` / `>=0.98` / other: ____ |
| Binding FPR ceiling | `<=0.10` / `<=0.05` / `<=0.02` / other: ____ |
| Candidate recall | binding `k`: 10 / 20 / 40 / 80; floor `>=0.90` / `>=0.95` / `>=0.98` / other: ____ |
| Adjudication | diagnostic only / redesign trigger `>0.30` / `>0.20` / `>0.10` / other: ____ |
| Task-mass coverage floor | `>=0.70` / `>=0.80` / `>=0.90` / other: ____ |
| Family rule | minimum family coverage `>=0.50` / `>=0.70` / `>=0.80`; or p10 family coverage `>=____`; other: ____ |
| Transport rule | adopt signed PI-15 downstream bounds when measurable / specify mapping-only bound: ____ / other: ____ |
| Binding weighting | unweighted / task-mass weighted / both must pass |
| `U` in FPR denominator | count as non-`D` (conservative) / exclude with signed rationale: ____ |

## 4. Recorded PI decision — Mapping A thresholds

- Candidate-generation/taxonomy/transport approved **for blind validation only**: YES
- PPV floor: 0.95
- FPR ceiling: 0.05
- Candidate-recall `k` and floor: 40 / 0.95
- Adjudication ceiling: 0.20
- Task-mass-weighted coverage floor: 0.80
- Occupation-family coverage floor: 0.70, independently binding
- Transport-sensitivity rule: existing signed PI-15 bounds
- Binding weighting and `U` treatment: task-mass weighted; `U` counts as non-`D`
- Locked test may be opened exactly once after decision commit and mechanical verification: YES
- Decision authority/date: PI/specification owner / 2026-08-21

The thresholds are signed, but the preflight status is
`BLOCKED_LABELS_AND_FROZEN_PREDICTION_RULE_ABSENT`; no locked result has been
opened and production use remains unapproved.

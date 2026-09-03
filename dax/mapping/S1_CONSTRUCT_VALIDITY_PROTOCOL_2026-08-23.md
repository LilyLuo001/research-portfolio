# DAX v3 S1 construct-validity pilot protocol freeze

**Status:** `FROZEN_BEFORE_S1_TASK_TEXT_INSPECTION`

**Base:** `5d33c61c5a2adf8f432ae092ec8e76b580a30670`

**Scope:** one no-model, outcome-blind, zero-spend construct-validity pilot.

## Provenance repair and one-time draw

The base repository and approved SCC private storage contain a proposed S1
sample size but no persisted 120-task draw, task-ID list, seed, or sampling
receipt. The instruction to use the already drawn sample is therefore
implemented as **one deterministic first realization**, not represented as an
earlier draw. There is no redraw, replacement, or difficulty-based substitution.

The private frame is the intersection of:

- O*NET 26.1 task rows with `primary_usable=true`; and
- 2021 frozen task-wage-allocation rows with `allocation_usable=true`.

The expected frame is 15,274 unique task IDs across 22 major occupation
families. The draw seed is the literal string
`DAX-V3-S1-FIRST-DRAW|5d33c61c5a2adf8f432ae092ec8e76b580a30670`.
Every ordering uses SHA-256 of `seed|purpose|value`.

Each major family receives five tasks. The ten families with the smallest
`extra-family` hashes receive one additional task, producing 120. Within a
family, tasks are mechanically prestratified by O*NET Core/Supplemental type and
the pre-text-inspection modality rules in the machine specification. Selection
cycles over nonempty strata in hashed order and takes the lowest unused task
hash in each stratum. Empty strata are not filled with a replacement task from
outside the already specified family cycle. The output is frozen private,
owner-only, and hashed before any selected statement is inspected.

## Unit and prohibited tailoring

The source unit is one O*NET occupational activity at its stated work-product
boundary. Construction may add only the minimum facts needed to instantiate
the role, start state, inputs, permitted tools, quality criterion, and observable
deliverable. It may not:

- expand an activity into a larger professional project;
- delete an essential physical, interpersonal, proprietary, or domain element;
- add irrelevant complexity to resemble GDPval;
- simplify difficulty because a present model might struggle; or
- name, query, or anticipate any target model while constructing or auditing.

## Evaluability taxonomy

Each source receives exactly one primary class:

1. `directly_executable_digital` — the complete activity and deliverable are
   natively digital with no missing material inputs;
2. `executable_with_supplied_files_data` — complete execution is possible when
   realistic files/data specified by the item are supplied;
3. `executable_with_construct_valid_simulated_inputs` — inaccessible real
   inputs can be simulated without changing the operative decision, work
   product, difficulty band, or quality standard;
4. `requires_unavailable_proprietary_system`;
5. `requires_physical_world_action`;
6. `requires_interpersonal_interaction`; or
7. `otherwise_not_currently_evaluable`.

Classes 4–7 are non-evaluable and remain missing/not identified. They receive
no benchmark instance, model score, or constructed AI failure. A digital
subcomponent of a physical/interpersonal task is not the full task.

## Required private instance fields

For classes 1–3, construct exactly one prospective instance specification with:

- occupational activity represented;
- minimum professional context;
- realistic required inputs/files/data and provenance method;
- allowed tools and environment;
- expected work product/output type;
- completion criterion;
- scoring method and objective checks;
- failure criterion;
- human-review requirement; and
- construction assumptions and unresolved dependencies.

The task definition is hashed separately from all future evaluation records.
Actual licensed/proprietary source files are not created or committed in this
pilot. If a complete construct-valid input package is not yet instantiated,
the item cannot receive `PASS`; it is `REVISE`.

## Construct-validity audit

Before any model evaluation, the single-Codex pilot audit records these seven
axes for every constructed item:

1. task-boundary fidelity;
2. work-product fidelity;
3. domain-context fidelity;
4. tool/input fidelity;
5. difficulty distortion;
6. added-task-content risk; and
7. omitted-essential-content risk.

The three final statuses are frozen as:

- `PASS`: class 1–3; all four fidelity axes pass; difficulty distortion is
  low; added and omitted risks are low; the input package, completion rule, and
  scoring rule are complete enough to freeze without model-specific revision.
- `REVISE`: class 1–3 and the same-boundary item is feasible, but at least one
  input, context, tool, scoring, difficulty, added-content, or omitted-content
  defect is prospectively repairable. No task replacement is permitted.
- `NON_EVALUABLE`: class 4–7, or faithful complete execution cannot be observed
  under the permitted harness without changing the task's substantive meaning.

This is a preliminary single-Codex construct audit, not independent expert
validation. Family-specific human review needs are recorded; no reviewer is
recruited or paid.

## Scoring feasibility

Each constructed item receives exactly one class:

- `fully_objective_mechanical`;
- `partially_objective_limited_rubric`;
- `primarily_expert_rubric`; or
- `not_currently_scoreable`.

Model self-grading may never be the sole criterion. A task-mass-weighted share
requiring no human judging counts only `fully_objective_mechanical` items that
pass construct validity.

## Weights and reporting

Unweighted counts cover all 120 selections. Sample task-mass summaries use the
frozen 2021 `task_annual_wage_bill_allocation`, normalized within this pilot;
they are descriptive, not design-weighted population estimates. Family-weighted
summaries give each of the 22 sampled major families equal weight and average
within family. No missing or non-evaluable mass is renormalized into the
benchmarkable subset.

## S1 decision status

No signed numerical S1 construct-validity threshold exists. This protocol does
not create one. It reports the complete distribution and leaves the gate
`NEED_PROSPECTIVE_PI_THRESHOLD_SIGNATURE`. The final scientific recommendation
may describe the observed pattern, but cannot formally pass S1 or launch S3.

## Hard stops

No AI evaluation, model metadata/API call, W4 capture, W5, identification,
power, outcome access, recruitment, or paid work is permitted in this batch.

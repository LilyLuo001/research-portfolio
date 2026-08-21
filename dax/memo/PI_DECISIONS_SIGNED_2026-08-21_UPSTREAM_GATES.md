# DAX PI Decisions — 2026-08-21

I am acting as the PI/specification owner for DAX. These decisions are made prospectively, before opening the locked Mapping A validation labels, before running W5 or identification, before the real power analysis, and while outcomes remain sealed.

These decisions must be committed before any locked validation results are opened. They may not be relaxed after observing whether the method passes.

## Decision 1 — Mapping A v2 blind validation

I approve the currently frozen Mapping A v2 method **for prospective blind validation only**.

This approval does **not** approve Mapping A v2 for production treatment construction. Production approval will depend on the one-time locked validation against the thresholds below.

### Binding validation rules

* Frozen Mapping A v2 method for blind validation: **APPROVED**
* PPV / precision floor: **0.95**
* False-positive-rate ceiling: **0.05**
* Candidate-recall evaluation rank: **k = 40**
* Candidate-recall floor at k=40: **0.95**
* Adjudication ceiling: **0.20**

  * If more than 20% of evaluated cases require adjudication, treat this as evidence that the relation taxonomy/candidate system requires redesign rather than simply adjudicating the entire mapping.
* Task-mass coverage floor: **0.80**
* Occupation/task-family coverage floor: **0.70**
* Transport sensitivity rule: **apply the existing signed PI-15 lower/center/upper bounds**
* Binding aggregate coverage metric: **task-mass weighted**
* Unweighted coverage: **mandatory diagnostic but not the principal aggregate gate**
* Family-level coverage remains independently binding at the 0.70 floor.
* `U` classifications count as **non-D** for PPV/FPR evaluation.
* Locked-test opening: **authorized exactly once after this signed decision is committed and mechanically verified**

### Interpretation

PPV is the principal false-link protection because candidate pairs are highly class-imbalanced. FPR must also be reported but must not be treated as mathematically equivalent to `1 - PPV`.

A validation failure must remain a failure.

Do not:

* reduce these thresholds after observing locked results;
* alter candidate generation based on locked results;
* relabel `U` cases to improve performance;
* change transport rules to make downstream coverage pass;
* inspect W5, power, or outcomes while deciding whether Mapping A passes.

If the locked test fails, stop production use and report which gate failed.

---

## Decision 2 — Task-duration source and fallback

I approve immediate outreach to the GDPval authors requesting task-level observed human completion-time metadata for the exact 220-task/version universe.

### Author-data route

* Send GDPval author request: **YES**
* Waiting period before activating fallback: **14 calendar days**
* One concise follow-up during the waiting period is permitted.
* Exact task-ID/version author-provided observed durations are acceptable if they pass the documented provenance and validation rules.
* Aggregate paper-level duration means must **not** be converted into task-level values.
* Semantic similarity alone must **not** be used to assign task duration.

### Qualified-human fallback

If validated task-level author data are unavailable after the 14-day period, I prospectively approve the three-independent-qualified-annotator fallback.

Requirements:

* minimum **3 independent qualified annotators per task**;
* annotators blind to AI-model capability/performance;
* annotators blind to W5 treatment values;
* annotators blind to identification and power results;
* annotators have no outcome access;
* elicitation follows the frozen lower/median/upper active-minutes protocol.

Before full annotation, run a stratified **40-task pilot**.

Pilot must cover multiple task families and anticipated duration ranges.

### Pilot pass rule

The fallback may proceed to the remaining task universe only if:

* at least **80%** of pilot tasks satisfy the prospectively defined adjacent-bin agreement criterion; and
* there is no clear systematic agreement failure concentrated in a task family that would invalidate the same elicitation protocol for that family.

If the pilot fails:

* do not lower the 80% criterion;
* revise the annotation instructions/protocol;
* construct a new independent pilot according to the repository's audit rules.

Do not use the failed pilot to choose a more favorable numerical threshold.

### Later author data

If exact-version, task-level observed GDPval author data are subsequently received and pass provenance validation, those observed data take precedence over human estimates for the corresponding tasks.

All restricted author-provided materials must remain in approved private storage unless redistribution is explicitly authorized.

---

## Decision 3 — Power benchmark

I define the primary power benchmark as an **external empirical effect-size calibration scale**, not as an estimate of the DAX treatment coefficient itself.

### Primary

* **0.13 relative decline**
* Source role: primary external empirical calibration
* Basis: authenticated August 2025 authored version already documented in the provenance audit

### Prespecified sensitivities

* **0.16**

  * later November 2025 authored/version-update empirical estimate
* **0.19**

  * historical DAX PI design target
  * retained as a sensitivity only
  * must **not** be represented as an externally sourced empirical estimate unless a valid primary locator is subsequently recovered

### Interpretation and disclosure

The repository and memo must explicitly state that 0.13 and 0.16 are external calibration scales rather than directly comparable DAX causal coefficients.

Differences in:

* exposure definition;
* sample;
* period;
* treatment unit;
* estimand;

must be disclosed.

The historical 0.19 value must be described as an intentional prior project design target whose external empirical provenance remains unresolved.

It must not be described as a literature estimate.

### Executable standard

I authorize a separate auditable commit changing `power_standard.json` to make:

* primary benchmark: **0.13**
* version status: resolved according to the authenticated 0.13 provenance
* required sensitivity calculations: **0.16 and 0.19**

The change must occur before the real power results are run or inspected.

Do not modify the benchmark after observing power results.

---

## Authorization for the next execution stage

After committing and mechanically verifying these PI decisions:

1. Open the Mapping A locked validation set exactly once.
2. Run the frozen validation without tuning.
3. Report every binding metric and PASS/FAIL individually.
4. If Mapping A passes all binding gates, prepare production Mapping A execution.
5. Send the GDPval author-duration request.
6. Do not launch the human-duration fallback until the 14-day condition or an explicit author response makes that route applicable.
7. Update the executable benchmark in a separate auditable commit before running power.
8. Continue free model-availability work where credentials are properly configured.
9. Do **not** incur paid W4 inference costs yet.
10. Do **not** run W5, identification, or real power until their upstream scientific gates pass.
11. Do **not** access outcomes or create `v1.0-preregistered`.

At the end of the next batch, report:

* the exact signed-decision commit;
* Mapping A locked validation results and PASS/FAIL for every gate;
* whether any rule was changed after label opening;
* GDPval outreach status;
* benchmark executable-standard commit and checksum;
* current task-duration status;
* W3/W4/W5 gate status;
* tests;
* secret/private-data scan;
* outcome-seal status;
* realized API spend.

No failed scientific gate may be converted into a pass without a new explicitly documented methodological decision.

# W3 decision — route GDPval through O*NET Detailed Work Activities

**Status:** DECISION MEMO, unsigned. Dated forward call for PI counter-signature.
**Date:** 2026-08-23. **Supersedes nothing**; Mapping A stays in the record as
executed and reported.
**Outcome-data status:** SEALED. No path under `dax/analysis/outcomes/` was
opened in producing this.

---

## 1. The decision being asked for

Buy **220 GDPval→DWA annotations** and make the O*NET Detailed Work Activity
layer the transport for Mapping A, replacing direct O*NET-task-to-GDPval-task
matching.

Everything in section 5 must be frozen **before** the annotation runs. Deciding
any of it afterwards is a specification choice under the portfolio's §11 rule.

## 2. What direct matching produced, and why it failed

Mapping A executed deterministically and reported honestly:

| | |
|---|---|
| O*NET tasks | 19,259 across 923 SOCs |
| auto-accepted | **0** |
| queued grade C | 37 |
| unmatched | 19,222 |
| task coverage | 0.00192118 |
| wage-bill coverage | 0.0022461 |

Two diagnostics, run before spending on formal validation, found D (direct
substitute) = 0/60 on development pairs, and 1 plausible D across 108 audited
candidate pairs.

The cause is a unit-of-analysis mismatch: an O*NET task statement is a short
occupational activity, a GDPval task is a composite professional assignment
with an extensive prompt, reference files, a deliverable and a rubric. They are
not the same kind of object, so no retrieval improvement makes them
commensurable.

**The literature does not attempt this mapping.** Tolan et al. (JAIR 2021,
10.1613/jair.1.12647) state the reason directly: an intermediate layer,
*"instead of mapping work tasks to AI benchmarks directly, allows for an
identification of potential AI exposure for tasks for which AI applications
have not been explicitly created."* That last clause describes the 19,222
unmatched rows. Brynjolfsson, Mitchell and Rock (AEA P&P 2018) scored ~2,059
DWAs and aggregated to ~18,112 tasks precisely because tasks share DWAs across
occupations. Eloundou, Manning, Mishkin and Rock applied their rubric at the
DWA level and aggregated. Three independent lines, one shared design.

## 3. What was measured

`dax/mapping/dwa_coverage_bound.py`, receipt
`dax/mapping/dwa_coverage_bound_receipt.json`, on the pinned inputs
(O*NET 26.1 `543d65fa…8017a`, GDPval `f8422fab…e0202`, wage allocations
`dc071f8e…708c`).

| Quantity | Direct match | DWA transport | Ratio |
|---|---|---|---|
| task-count coverage | 0.00192118 | **0.3389584** | 176× |
| wage-bill coverage | 0.0022461 | **0.4169526** | 186× |

Reconciliation passed: derived universe 19,259 tasks / 923 SOCs against the
pinned audit; weights 15,274 usable tasks and mass 56,074,210.000001125 against
`mapA_run_receipt.json`. Table selection was unambiguous — `Occupation
Data.txt`, `Task Statements.txt`, `Tasks to DWAs.txt`, with no rejected
alternatives.

**This is an upper bound, and the receipt says so.** It credits every DWA
belonging to a GDPval occupation as transportable.

## 4. Honest limits on that number

1. **The bound is optimistic by a measurable amount.** GDPval holds 220 tasks
   across 44 occupations — five per occupation, against an O*NET average of
   20.9. Five tasks cannot exercise an occupation's whole activity repertoire,
   so realised coverage will be below 0.4170. The gap is estimable from O*NET
   alone by a task-sampling-depth (rarefaction) curve: draw k tasks from an
   occupation, count distinct DWAs reached. Countervailing, GDPval tasks were
   expert-selected as representative rather than drawn at random, so they
   plausibly span more DWA diversity than random draws; the sampling-depth
   figure is therefore a floor and the truth lies between it and 0.4170.
2. **The weighted figure covers 79.3% of the universe.** 3,985 of 19,259 tasks
   carry no usable wage allocation and are excluded from both numerator and
   denominator. 0.4170 is a share of *allocable* mass, comparable to mapA's
   0.0022461 on the same basis. It must not be written as "42% of wage mass".
3. **Coverage is bounded by GDPval's occupational span.** 522 of 2,085 distinct
   DWAs are reachable — a quarter of O*NET's activity vocabulary. Roughly 58%
   of allocable wage mass is unreachable *even under the optimistic bound*.
4. **One occupation is unmatched.** `Buyers and Purchasing Agents` did not match
   an O*NET 26.1 title exactly, and was excluded rather than fuzzy-matched. The
   bound is conservative by that occupation.
5. **GDPval ships no O*NET linkage.** `onet_linkage_fields_present` is empty on
   the pinned revision, so the GDPval-side annotation is genuinely required and
   cannot be recovered from the dataset. The revision does carry `rubric_pretty`
   and `rubric_json`, which the public dataset card does not list — relevant to
   W4 grading later, not to this decision.

## 5. What is frozen by this memo, before any annotation runs

**[W3-D1] Transport layer.** O*NET Detailed Work Activities, using the
published `Tasks to DWAs` crosswalk for the O*NET side. The GDPval side is
annotated. Direct task-to-task matching is retired from the primary; Mapping A's
executed result stays in the record as the comparison in section 3.

**[W3-D2] Aggregation rule.** Task-level feasibility is **weakest-link**: an
O*NET task crosses only when *every* DWA it carries has crossed. Mean and
any-DWA variants are reported as sensitivities, never as the primary. Frozen
here because choosing it after seeing coverage would be a specification choice.

**[W3-D3] Candidate constraint.** Each GDPval task is annotated against the DWA
set of its own stated occupation, not against all 2,085. GDPval was built to
cover O*NET work activities for its 44 occupations, and the receipt shows 522
reachable DWAs across 43 SOCs, so the per-occupation candidate list is short.
An annotator may return *no* DWA; it may not return one outside the set.

**[W3-D4] Dual-channel and audit.** Two different vendor families per meta-rule
2, machine-diff, third model plus the RA on splits. **PI-DECISION 7 applies
unchanged**: audit 10% stratified by occupation family and ambiguity flag —
22 of 220 tasks — requiring weighted Cohen's kappa ≥ 0.70 and ≥ 90% agreement
on the binary crossing-relevant label. Failure returns the rubric for redesign
rather than lowering the bar.

**[W3-D5] Unmatched occupation.** `Buyers and Purchasing Agents` stays excluded
unless a signed amendment names the O*NET 26.1 titles it maps to. Coverage is
reported as conservative by one occupation either way.

**[W3-D6] Stop criterion.** If the pilot in section 6 fails the D4 bar twice
after rubric redesign, W3 stops and returns to the PI rather than proceeding to
the remaining tasks. Two consecutive failures auto-escalate per meta-rule 5.

**[W3-D7] Reporting rule.** Every coverage figure published from this layer
carries its basis: allocable-mass share, the excluded 20.7%, the one unmatched
occupation, and whether it is a bound or a realised value.

## 6. Sequence and cost

A **20-task pilot** runs first: both vendor families, agreement measured against
the D4 bar. A failure costs almost nothing and returns the rubric before the
remaining 200 are bought.

Direct cost is not the binding constraint. Arithmetic on the stated GDPval
lengths (~276-word prompt, ~780-word rubric) plus a per-occupation candidate
list gives roughly 415,000 input tokens per vendor pass, about 831,000 across
two, and under 90,000 output tokens. Rates are not recorded here — meta-rule 1
forbids quoting them from memory; multiply against current published vendor
rates at purchase time. For scale, the superseded S3 design proposed 384
constructed benchmark instances, which is GDPval-scale effort.

The binding costs are RA adjudication time and the design freeze in section 5.

## 7. What this decision does **not** do

It does not unblock measurement. W3 establishes *what* to measure. The W4
capability panel remains blocked on prerequisites this memo does not touch:

- the OpenAI API key at the expected private path, **verified absent on
  2026-08-23** and never provisioned;
- `dax/capability_panel/budget_ceiling.json` at `status: PI_SIGNED`, which does
  not exist;
- per-task duration metadata, at 0/220.

**Annotation is not deadline-bound; capture is.** Fourteen dated snapshots in
`vintage_registry.json` retire on 2026-10-23 and 2026-12-11 and cannot be
re-run afterwards. The annotation costs the same in December. If it displaces
provisioning the key, the project ends with a validated crosswalk and no
capability panel to apply it to.

## 8. Open provenance gap

The Mapping A v2 diagnostics and the S1 construct-validity pilot are cited in
project discussion but **have no artifacts in this repository**. The repo state
is the only shared state. Any figure from that work — including the S1 pass and
non-evaluable shares — cannot enter the paper until its artifacts and locators
are committed. This does not block the annotation; it blocks write-up.

## 9. Signature

    PI signature: ______________________  Date: ____________

    [ ] approved as drafted — freeze D1-D7 and run the 20-task pilot
    [ ] approved with modifications noted below
    [ ] rejected — direct matching stands at 0.0022461 wage-bill coverage,
        and the consequences for the estimand are accepted

Rejection is listed explicitly so that continuing with a 0.22% mapping is a
recorded decision rather than an outcome of inaction.

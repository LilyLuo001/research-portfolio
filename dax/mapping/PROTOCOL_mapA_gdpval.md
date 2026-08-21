# Mapping A (GDPval primary) — protocol and adjudication

**Task:** DAX-W3-mapA. **Status:** executed 2026-08-18 UTC; independent
adjudication and audit remain pending.
**Binding constraint:** the signed W0.5 feasibility condition — GDPval is
referenced **by task ID** for internal research; no GDPval task text or derived
task content enters W10a until redistribution rights are clarified.

**Supersession note (2026-08-21):** the executed method below is retained as
Mapping A v1 and as failure evidence. Its 0.19% matched-or-queued coverage does
not permit threshold tuning. The proposed v2 methodology and new approval gate
are in `MAPPING_A_V2_DECISION_PACKET_2026-08-21.md`; v2 does not become primary
until the PI approves calibrated many-to-many transport.

This is the primary mapping. Under the memo's §5 hierarchy, Mapping A is what
the headline estimate uses; Tolan (B) and Eloundou (C) are independent
robustness constructions and cannot rescue a sign conflict.

## 0. What this protocol produces

The private run produces `mapping_a_gdpval.csv`, keyed
`onet_task_id × gdpval_task_id`, under `ops/contracts/mapping_a_gdpval.yaml`.
Every O*NET task appears exactly once — matched, queued, or unmatched. The
ID-level mapping, coverage rows, and adjudication queue remain outside Git;
`mapA_run_receipt.json` and `mapA_private_artifacts_manifest.json` expose only
safe counts, distributions, hashes, and status.

## 1. Embedding step (frozen and executed)

All O*NET task statements and the GDPval open gold subset were embedded with
`sentence-transformers/all-MiniLM-L6-v2` at immutable revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (Apache-2.0, 384 dimensions).
The ex-ante choice and blocking memo was committed before any similarity was
computed. See `mapA_ex_ante_model_choice.md`.

Cosine similarity was computed within deterministic occupation-adjacent blocks:
the 10 nearest of 44 GDPval occupation labels for each official O*NET title,
with all 5 tasks per selected label retained. No language model judged a match
at this stage; the scores are code output on text, which is what meta-rule 1
requires.

**Perturbation-robust variant.** The execution plan requires both average-case
and perturbation-robust π. The battery — paraphrase, reformatting, distractor
insertion — is applied to the *task prompts* used for capability measurement in
W4, not to the O*NET statements here. Mapping A emits a single similarity per
pair; robustness enters through W4's π, not through re-embedding.

## 2. Grading: why similarity alone is not enough

The obvious rule is "accept above a similarity floor". It is wrong in a
specific, checkable way.

Consider two O*NET tasks. The first matches one GDPval task at 0.81 and nothing
else above 0.55. The second matches two GDPval tasks at 0.81 and 0.80. A
similarity-only rule accepts both. But the second task is *ambiguous precisely
because it matched well twice* — assigning it to whichever GDPval task won by
0.01 is a coin flip that propagates into π, into crossings, and into the index.

Grading therefore uses the **margin over the runner-up** as well as the top
score. Thresholds, pre-registered as constants in `mapA_adjudication.py`:

| Grade | Condition | Disposition |
|---|---|---|
| **A** | similarity ≥ 0.80 **and** (margin ≥ 0.05 or no runner-up) | auto-accept |
| **B** | similarity ≥ 0.80 but margin < 0.05 | adjudication queue — ambiguous |
| **B** | 0.70 ≤ similarity < 0.80 | adjudication queue with pre-label |
| **C** | 0.60 ≤ similarity < 0.70 | adjudication queue, pre-label not carried |
| **unmatched** | no candidate ≥ 0.60 | retained and reported |

Ties in similarity break on `gdpval_task_id`, so two runs of the protocol cannot
disagree.

**Changing any threshold after seeing match outcomes is a specification
choice.** They are module constants so that a change shows up in a diff and
requires a §11 deviation memo.

## 3. Unmatched tasks are a finding

An O*NET task with no candidate above the floor stays in the output with
`grade = unmatched` and its best sub-floor similarity recorded. It carries its
occupation's wage-bill share into the coverage table.

This is not bookkeeping politeness. Unmatched wage-bill share is the honest
upper bound on how much of the DAX index is *unmeasured*, and a mapping that
silently dropped these would report artificially clean coverage. `route()`
partitions rather than filters, and a test asserts the partition conserves
every task.

## 4. Coverage

Coverage is computed per occupation as matched tasks over total tasks.
Occupations below **0.70** are flagged, not dropped — the flag propagates to
W5, which reports index values for flagged occupations separately so a reader
can see how much of the estimate rests on thinly-mapped occupations.

## 5. Match quality and the top-quartile subset

The execution plan requires a top-quartile match-quality flag for headline
re-estimation. Quality is the similarity of a matched or queued pair.

**Unmatched tasks are excluded from the quartile calculation rather than scored
zero.** Scoring them zero would drag the cut point down and silently widen the
"top" quartile — the subset would look more selective than it is. A test pins
this: adding twenty unmatched tasks must not change the flagged set.

## 6. Adjudication (the T1 judgment)

Grade B and C pairs go to a queue carrying: both IDs, similarity, runner-up
similarity, margin, the machine pre-label for grade B, and the reason string.

Adjudication order is **frozen before any adjudication begins**: by occupation
wage-bill share descending, then by `onet_task_id`. Adjudicating high-value
occupations first is defensible; choosing the order after seeing the queue is
not.

Per the execution plan's agent table, bulk pre-labelling is a T3 task and audit
is T1 on a stratified sample, with human validation by the RA. Disagreements
are logged with both labels and the resolution — never overwritten.

**[PI-DECISION 7] applies unchanged:** audit 10% of annotations stratified by
occupation family, score decile, and ambiguity flag; require weighted Cohen's
kappa ≥ 0.70 and ≥ 90% agreement on the binary crossing-relevant label before
W5. Failure returns the rubric for redesign rather than lowering the bar.

## 7. The GDPval licence guard

`assert_release_safe()` refuses any release-path record carrying a task-text
field with content. Fields checked: `gdpval_task_text`, `task_text`, `prompt`,
`rationale_text`, `gdpval_prompt`, `excerpt`.

A licence condition that lives only in prose gets violated by whoever writes the
release script months later, under deadline, with no memory of the feasibility
gate. This is the same reasoning as the outcome seal: the rule is enforced where
the violation would occur.

Internal working files may hold task text; the guard applies to anything on a
release path. A blank column is not a violation — only content is.

## 8. Frozen execution decisions

The model, revision, pooling, 10-occupation block, and all four grading
thresholds were frozen before inspecting mapping outcomes. The observed
distribution did not trigger any tuning: the 0.60 floor, 0.80 auto-accept
threshold, 0.05 margin, and 0.70 occupation-coverage floor remain unchanged.

## 9. Status of this protocol

`run_mapA.py` executed twice with byte-identical ID-level outputs. It conserved
all 19,259 O*NET tasks: 0 auto-accepted, 37 queued as grade C, and 19,222
unmatched. Matched-or-queued task coverage is 0.00192118; the available 2021
annual task-allocation-mass coverage is 0.00224610. All 923 occupations fall
below the 0.70 coverage floor. This low coverage is reported rather than
repaired by post-outcome tuning.

The 37-row queue is frozen and remains private. No B/C judgment has been
self-certified. W3 remains dependent on independent cross-vendor annotation
and the PI-decision-7 T1 audit before any queued judgment can be treated as
audited.

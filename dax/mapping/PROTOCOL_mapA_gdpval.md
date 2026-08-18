# Mapping A (GDPval primary) — protocol and adjudication

**Task:** DAX-W3-mapA. **Status:** protocol drafted 2026-08-18; not executed.
**Blocked on:** `DAX-W2-data` (O*NET task statements are not yet built).
**Binding constraint:** the signed W0.5 feasibility condition — GDPval is
referenced **by task ID** for internal research; no GDPval task text or derived
task content enters W10a until redistribution rights are clarified.

This is the primary mapping. Under the memo's §5 hierarchy, Mapping A is what
the headline estimate uses; Tolan (B) and Eloundou (C) are independent
robustness constructions and cannot rescue a sign conflict.

## 0. What this protocol produces

`dax/mapping/mapping_a_gdpval.csv`, keyed `onet_task_id × gdpval_task_id`, under
`ops/contracts/mapping_a_gdpval.yaml`. Every O*NET task appears exactly once —
matched, queued, or unmatched. Plus a protocol run report with similarity
distributions, coverage tables, the adjudication queue, and inter-rater
statistics.

## 1. Embedding step (specified, not yet run)

Embed all O*NET task statements and the GDPval open gold subset with a
**pinned open embedding model**, recording model name, version, revision hash,
and dimension in the run lineage. The model is pinned because a silent upgrade
would change every similarity score and therefore every crossing, with no diff
to show for it.

Cosine similarity, computed pairwise within occupation-adjacent blocks to keep
the comparison tractable. No language model judges a match at this stage; the
scores are code output on text, which is what meta-rule 1 requires.

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

## 8. What is deliberately not decided here

- **The embedding model.** Pinning it is a choice with real consequences for
  every downstream number, and it should be made once W2 shows what the O*NET
  statements actually look like. Recorded as an open item, not defaulted.
- **The occupation-adjacent blocking scheme** for pairwise comparison, which
  trades recall against compute and needs the real corpus size to settle.
- **Whether the 0.60 floor survives contact with the real similarity
  distribution.** If the distribution is bimodal with a trough well away from
  0.60, the floor should move *before* any matching is adjudicated, and that
  move is a §11 deviation with the distribution attached as evidence.

## 9. Status of this protocol

Sections 2 through 7 are implemented and tested in
`dax/mapping/mapA_adjudication.py` and `dax/tests/test_mapA.py` (14 tests). The
embedding step of §1 is specified but not implemented, because it needs O*NET
task statements from `DAX-W2-data`.

When W2 lands, the only genuinely new component is the embedding call. That is
the point of front-loading this: the judgment-heavy part is settled while it is
cheap to argue about, and it is settled in code that fails when violated rather
than in prose that can be forgotten.

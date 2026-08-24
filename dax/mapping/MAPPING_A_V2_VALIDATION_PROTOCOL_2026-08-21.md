# Mapping A v2 prospective validation protocol — 2026-08-21

**Status:** validation preparation authorized; production method not approved.
**Blinding:** no W4 capability result, W5 dose, power result, treatment effect,
or outcome may enter retrieval, sampling, annotation, or method selection.

## 1. Universes and preprocessing

- Source universe: the 19,259 unique O*NET 26.1 task IDs and statements in the
  executed v1 input receipt, retaining the linked O*NET-SOC and 2021 task mass.
- Target universe: all 220 unique GDPval task IDs at repository revision
  `11e7900cdcac61bc4daf59e65feb238acda98fbf`.
- Dense channel: `sentence-transformers/all-MiniLM-L6-v2` revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 dimensions, tokenizer
  truncation at 256 wordpieces, attention-mask mean pooling, L2 normalization,
  and cosine similarity. Negative cosine is clipped to zero only for release
  schema compatibility; ranking is deterministic by score then GDPval task ID.
- Lexical channel: Unicode NFKC, casefold, tokens matching `[a-z0-9]+`, no
  stemming and no stop-word deletion; Okapi BM25 with `k1=1.2`, `b=0.75`, and
  the 220 GDPval prompts as documents. Ties break by GDPval task ID.
- Every one of the 19,259 x 220 = 4,236,980 pairs is scored in both channels.
  Occupation labels are diagnostics only and cannot exclude a pair.
- Seed namespace: `DAX-MAPA-V2-20260821`. Duplicate source or target IDs and
  any missing pair fail the run.

The dense model is retained from v1 as a retrieval channel to avoid selecting
a new model after seeing v1's low scores. Unlike v1, cosine is not a match
grade. BM25 supplies an independent lexical channel.

## 2. Frozen relation taxonomy

All examples below are synthetic illustrations, not GDPval/O*NET source text.

| Code | Exact definition | Positive illustration | Negative illustration | Ambiguous illustration | Proposed transport permission |
|---|---|---|---|---|---|
| `D` direct substitute | Successful completion demonstrates substantially the same work product, core operations, domain constraints, and quality criterion as the O*NET task. | “prepare a monthly financial statement” vs “produce monthly statements from a ledger” | financial statement vs repair plumbing | “analyze accounts” vs conduct a complete audit | central/lower/upper, subject to calibration |
| `F` same capability family | Tasks share a material capability or workflow, but success on one is not sufficient evidence of completing the other end to end. | summarize a legal record vs draft a case memorandum | legal summary vs weld a pipe | analyze records vs produce a regulatory filing | upper-bound/sensitivity only; not central |
| `N` unrelated | No material task-output or capability transfer supports the mapping. | repair machinery vs draft tax advice | two substantially equivalent tax-return tasks | both use spreadsheets but produce unrelated outputs | none |
| `U` insufficient/ambiguous | Available task information cannot distinguish D/F/N or required artifacts/constraints are missing. | a generic “analyze data” statement with no output | a clearly direct pair belongs in D | same occupation title but incompatible deliverables | none until adjudicated |

One GDPval task may be related to many O*NET tasks and one O*NET task may have
many GDPval candidates. Annotators may use only D/F/N/U; proposing a fifth
class reopens the protocol before production.

## 3. Independent annotation

- Round 1 requires two independent annotators from different vendor families.
- Each sees the two private task records, the rubric above, and retrieval ranks
  only after entering an initial relation label; scores are otherwise hidden.
- Annotators never see W4 performance, price, W5 dose, occupation exposure,
  power, treatment effects, or outcomes.
- Disagreement or any U label goes to a third vendor-family adjudicator. A
  human reviewer resolves remaining D-versus-F disagreements and audits the
  sample required by PI Decision 7.
- Labels, rationales, task text, and identities stay private. Git receives
  counts, reliability metrics, hashes, and statuses only.

Inherited pass criteria are only PI Decision 7: 10% stratified human audit,
weighted Cohen kappa at least 0.70, and at least 90% agreement on the binary
crossing-relevant label. PPV, false-positive, candidate-recall, adjudication,
and v2 coverage thresholds are new and remain `NEED_HUMAN` before labels open.

## 4. Blind validation sample

- Within every observed major SOC family, select up to 20 O*NET tasks by
  deterministic round-robin over 2021 task-mass band and v1-score decile.
- For each selected task, take at most one distinct pair from each frozen
  category: dense/lexical top-10 agreement, dense-only top-10 with lexical rank
  over 40, lexical-only top-10 with dense rank over 40, medium ranks 11--80 in
  both channels, an apparent negative with both ranks over 100, and reciprocal-
  rank-fusion best (`60` denominator). Missing categories remain missing.
- Split at O*NET-task level by SHA-256 seed: 60% development, 20% calibration,
  20% locked test. All candidate pairs for one O*NET task stay in one split.
- Development labels may refine code defects and rubric wording. Calibration
  may fit a pre-specified calibrator. Locked-test labels stay sealed until code,
  features, and proposed thresholds are committed.

## 5. Proposed transport rule — not approved

For destination O*NET task `t`, let `J_D(t)` be adjudicated direct substitutes
and let `p_tj` be a transfer probability calibrated only on development and
calibration labels. Proposed central weights are

`w_tj = p_tj / sum_{k in J_D(t)} p_tk`, so `sum_j w_tj = 1` within task `t`.

W4 capability is transported from GDPval task `j` to O*NET task `t`, never in
the reverse direction. Multiple GDPval tasks for one O*NET task are replicate
evidence, not additive task coverage; the O*NET task's wage mass is counted
once. One GDPval task may inform several O*NET tasks, each of which retains its
own mass. Exact duplicate benchmark deliverables are grouped prospectively and
only the highest-calibrated member contributes, preventing duplicate semantic
coverage.

- lower: weighted lower W4 bounds over D candidates;
- center: weighted central W4 values over D candidates;
- upper: maximum of the D-weighted upper value and F-family upper evidence;
- unresolved/U/no-D task: center remains null and bounds remain `[0,1]` rather
  than redistributing its mass to observed tasks.

Mapping uncertainty is propagated by resampling adjudicated relation labels
and the calibration fit before recomputing all three bounds. No final transport
weight, calibrator, or bootstrap count becomes binding without PI approval.

## 6. Prospective metrics and unresolved thresholds

Report on calibration and locked test separately: D precision/PPV; N/U false-
positive rate; D/F/N/U confusion matrix; candidate recall across the evaluated
rank grid `{5,10,20,40,80,220}`; kappa and binary agreement; adjudication rate;
task- and task-mass-weighted coverage; coverage distribution by major SOC
family; dense-only, lexical-only, combined, and transport-bound sensitivity.

`NEED_HUMAN: prospectively approve numerical floors/ceilings for PPV, false
positives, candidate recall, adjudication rate, weighted coverage, family-level
coverage, and acceptable transport sensitivity before locked-test labels open.`

Permitted stage statuses are `VALIDATION_SUPPORTIVE_PI_APPROVAL_REQUIRED`,
`VALIDATION_FAIL`, or `NEED_HUMAN`. Code execution alone cannot mark v2
validated or production-approved.

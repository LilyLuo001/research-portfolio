# Mapping A v2 decision packet — 2026-08-21

## Determination

Do not repair Mapping A by lowering the v1 cosine thresholds. The executed v1
run retained all 19,259 O*NET tasks but auto-accepted none, queued only 37, and
left 19,222 unmatched. Its maximum score was 0.6963 and its 99th percentile was
0.5583; all 923 occupations failed the 0.70 coverage floor. That pattern is not
a marginal threshold miss. It shows that a short-task generic sentence
embedding is not calibrated to the long, artifact-rich GDPval prompts.

Preserve v1 and its hashes as a failed measurement attempt. Mapping A v2 is a
new, versioned methodology; it must not overwrite the v1 receipt.

## Proposed v2 methodology: calibrated many-to-many transport

Mapping A should estimate whether performance on a GDPval task transfers to an
O*NET task, not whether two strings happen to have high cosine similarity.

1. **Full-pool retrieval.** Score every O*NET task against all 220 GDPval tasks.
   The pool is only 4,236,980 pairs, so GDPval occupation labels must not block
   candidates. They may be retained as features and diagnostics.
2. **Independent retrieval channels.** Union a pinned dense top-k and lexical
   top-k. `mapA_v2_candidates.py` fails if any O*NET x GDPval score pair is
   missing and freezes deterministic ties.
3. **Relation labels, not cosine grades.** Independently label candidate pairs
   as `direct_substitute`, `same_capability_family`, or `unrelated`, under a
   written rubric. A cross-encoder or LLM may pre-label, but two vendor families
   plus human adjudication are required under the repository meta-rules.
4. **Calibrate transport on held-out labels.** Estimate a transfer probability
   from retrieval/reranker features on a training split and calibrate it on a
   held-out split. Do not assign arbitrary 1.0/0.5 weights after seeing dose
   behavior. Keep an explicit uncovered probability mass for each O*NET task.
5. **Propagate uncertainty.** W5 receives lower/central/upper task-capability
   values. Uncovered mass and `same_capability_family` uncertainty widen the
   interval; they are never silently renormalized away.

## Blind validation design

- Draw O*NET tasks before any W4 outcomes are opened, stratified by major SOC
  family, task-allocation mass, and v1 score decile.
- For a retrieval audit, independently adjudicate the full 220-task GDPval pool
  for a manageable validation subsample and report candidate recall across the
  frozen rank grid. The numerical recall floor is `NEED_HUMAN`; failure of the
  eventual prospectively approved floor makes v2 fail and does not authorize
  post-label tuning of k.
- For relation labels, retain PI Decision 7: 10% stratified audit, weighted
  Cohen kappa at least 0.70, and at least 90% agreement on the binary
  crossing-relevant label.
- Do not interpret candidate coverage as valid mapping coverage. The latter is
  counted only after adjudication/calibration.

## Prospective Mapping gate — thresholds not approved

The following are proposed measurement dimensions, not an active pass gate:

- full 19,259 x 220 score-pool completeness is verified by hashes and counts;
- held-out candidate recall (numerical floor `NEED_HUMAN`);
- the inherited PI-Decision-7 label-reliability thresholds;
- 2021 task-allocation-mass coverage (numerical floor `NEED_HUMAN`);
- major-SOC-family coverage distribution (numerical floor `NEED_HUMAN`);
- every O*NET task is retained, including uncovered tasks;
- all text-bearing and ID-level GDPval artifacts remain private.

Failure at the eventual PI-approved coverage gate does not authorize threshold tuning. The
fallback is to report partial-identification bounds and seek PI approval for a
different primary measurement design. Mapping B/C may diagnose the failure but
cannot silently replace Mapping A.

## Faculty decision required

The current authorization permits blind validation and method-freeze
preparation only. After reviewing that evidence, approve, revise, or reject
**calibrated many-to-many transport** as the primary Mapping A methodology.
Nothing here authorizes W4 spending, W5 construction, identification, power,
or outcome access.

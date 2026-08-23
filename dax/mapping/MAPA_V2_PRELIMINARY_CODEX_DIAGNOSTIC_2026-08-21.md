# Mapping A v2 preliminary Codex diagnostic — 2026-08-21

**Status:** `PRELIMINARY_DIAGNOSTIC_COMPLETE_NOT_FORMAL_VALIDATION`

## Scope and safeguards

This is a deliberately limited diagnostic requested by the PI. It used one
current Codex session under included usage and incurred zero incremental API
spend. It is not independent multi-vendor annotation, does not satisfy the
formal labeling protocol, and cannot be used as a locked-test result or as
production approval.

The sample contains 60 pairs from the already frozen development/calibration
partitions: 36 development and 24 calibration. It has ten pairs from each of
the six frozen retrieval categories and covers all 22 major SOC families. A
fixed diagnostic seed shuffled category blocks before annotation. The private
packet contained the two task records and the D/F/N/U rubric, but no retrieval
scores, probabilities, downstream variables, outcomes, or locked-test task
text. Row-level sample IDs, text, labels, and rationales remain mode-0600 on
SCC. Git contains only code and sanitized aggregate receipts.

The diagnostic did not open a locked-test label, consume the one-time locked
opening, fit the frozen classifier, select a cutoff, change a threshold, change
candidate generation, or modify any transport method.

## Descriptive result

The single Codex annotator assigned 0 direct substitutes (`D`), 24 same-family
relations (`F`), 36 unrelated pairs (`N`), and 0 insufficient-information
pairs (`U`). Thus the descriptive direct-substitute rate is 0/60 (Wilson 95%
interval 0.000--0.060), while the broader D-or-F rate is 24/60 = 0.400
(Wilson 95% interval 0.286--0.526).

Retrieval has a visible family-level semantic signal. The combined
`agree_high` plus `rrf_best` strata contain 11/20 D-or-F judgments, compared
with 0/10 in the prospectively sampled `apparent_negative` stratum, a
descriptive difference of 0.55. Dense-only and RRF-best each contain 7/10
D-or-F judgments. However, all of those positive semantic judgments are `F`,
not `D`.

These quantities are not binding PPV, false-positive rate, candidate recall,
inter-vendor agreement, adjudication rate, task-mass coverage, transport
sensitivity, or locked-test performance. The sample deliberately balances
retrieval categories and therefore is not an estimate of the prevalence of
relations in the full 4,236,980-pair universe.

## Viability judgment

**The observed quality does not yet justify launching the full formal
independent validation of Mapping A v2 as currently frozen for the central
mapping.** The retrieval channels appear capable of finding broad capability-
family links, which is useful for the pre-specified upper-bound sensitivity,
but this diagnostic found no evidence that they recover the strict direct
substitutes required by the frozen central transport rule. Even within the 20
highest-agreement/RRF pairs, the direct-substitute count is 0.

This is a preliminary go/no-go judgment, not a formal failure of any signed
threshold. Mapping A v2 remains unvalidated rather than failed. A PI may still
authorize formal independent labeling as a confirmatory/falsification exercise,
but the present diagnostic does not support spending that effort on the
expectation that the frozen method is already production-viable. Any redesign
or change in the role of `F` would require a separate prospective PI decision;
none is made here.

## Audit trail

- Private SCC directory:
  `/usr3/graduate/qluo/dax-private/w3_mapA_v2_codex_diagnostic/run_20260821`
- Sampling receipt: `mapA_v2_codex_diagnostic_sampling_receipt_20260821.json`
- Aggregate result receipt:
  `mapA_v2_codex_diagnostic_result_receipt_20260821.json`
- Incremental API spend: USD 0.00
- Locked-test labels opened: no
- Independent multi-vendor validation claimed: no

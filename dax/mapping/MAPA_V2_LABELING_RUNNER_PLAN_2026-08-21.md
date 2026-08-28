# Mapping A v2 independent-label runner plan — frozen, not launched

**Status:** `NEED_PI_BUDGET_AUTHORIZATION`. No annotation inference call has
been made and realized spend is USD 0.00.

## Frozen routing

- Unit: one O*NET/GDPval pair per isolated call.
- Initial annotator 1: DeepSeek family, `deepseek-v4-pro`, thinking disabled.
- Initial annotator 2: Alibaba family, `qwen-plus`, thinking disabled.
- Third annotator, only for disagreement or either initial `U`: Google family,
  `gemini-2.5-flash`, thinking budget zero.
- Temperature zero; maximum 160 output tokens; JSON D/F/N/U plus concise
  rationale. No vendor family is reused as another independent annotator.
- Unresolved D/F disputes go to the authorized qualified human procedure.

The exact rubric, forbidden fields, output schema, and routing are serialized
in `mapA_v2_annotation_spec_20260821.json`. The independent-label validator is
`mapA_v2_label_protocol.py`.

## Private execution order after budget authorization

1. Materialize separate encrypted/private input shards for development and
   calibration. Include only the two task records and rubric; exclude scores,
   probabilities, cutoff, downstream data, outcomes, and the other vendor's
   response.
2. Complete both initial families. Persist raw response, request hash, model
   returned, UTC timestamp, usage, and vendor-family code in mode-0600 storage.
3. Build the deterministic disagreement/U queue. Dispatch it only to the third
   family. Route unresolved D/F cases to the human queue.
4. Validate exactly 1,513 development and 540 calibration final labels. Fit
   with `freeze_mapA_v2_prediction.py`; if no feasible cutoff exists, stop with
   `MAPPING_A_V2_CALIBRATION_FAIL`.
5. Only after the immutable prediction receipt is committed may the already
   separated 533-pair locked shard be finalized. Store it under a distinct
   sealed path and publish only count, completion, family provenance, hash, and
   confirmation that fitting code never read it.
6. Label the frozen 60-task exhaustive recall sample. Open reserve 1 and then
   reserve 2 only when the completed denominator has fewer than 100 adjudicated
   D links; never expand because Recall@40 is unfavorable.

## Spend and failure controls

- The runner must acquire a single job lock, enforce the USD 60.00 batch cap,
  and stop before a request that could cross it.
- Retry only transport/rate-limit/5xx failures, at most twice with the same
  request hash. Never replace a substantive label by retrying.
- Any model-route mismatch, non-JSON response after the transport retry, reused
  vendor family, missing lineage field, or private-path violation fails closed.
- Git receives aggregate counts, hashes, status, and spend only—never task text,
  IDs, labels, rationales, identities, or credentials.

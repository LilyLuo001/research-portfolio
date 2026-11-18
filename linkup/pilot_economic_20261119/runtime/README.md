# Economic pilot runtime v1

This is a **new**, separately pinned pilot runtime. It neither edits nor reopens the previous confirmation runtime, its ledger, its $50 allocation, or its exhausted Astra attempts. Offline tests are engineering evidence, not measured economic Macro-F1, model qualification, or production admission. Root owns deployment and model calls; this package was prepared without either.

## Execution contract

- Direct Azure Responses/chat completions through the established managed-identity `workflow.token` helper. No OpenCode, redirects, environment HTTP proxy, credential files or credential logging.
- The initial launch defaults to concurrency **2** (allowed 1–4) and a cumulative **100-new-logical-context** ceiling. Raising the ceiling requires an explicit later launch; the same ledger is retained. Checkpoint receipts are immutable. No automatic expensive continuation.
- Hard main ceiling: Luna **10,000 new logical contexts**, at most 12,000 physical attempts, **$110**. Kimi audit: at most 100 logical **and physical** attempts, **$25**. Astra: at most 20 logical **and physical** attempts, **$15**. Audit retries consume their physical limits. The dollar cap can bind well before a context maximum.
- All legs share one durable `ADMISSION_PRIVATE.sqlite3`, atomic context claims, byte-upper reservations, shared rolling token window and persistent global stop. Same-context audit claims are separate from the main claim and require a completed Luna carrier.
- Shared scheduled maximum **800,000 TPM**; Luna **80,000 TPM** against 100,000 actual, Kimi **720,000 TPM** against 3,000,000 actual, Astra 800,000 TPM against 1,000,000 actual. Observed lower provider quotas only tighten admission.
- Each reservation charges `(complete_request_UTF8_bytes + 1024) * input_price + maximum_output_tokens * output_price`. No cache credit, actual-usage refund, or token estimate is used to pre-spend the budget. Over-limit requests are not truncated or forwarded.
- At most two attempts per context; retry only after confirmed 429/500/502/503/504, and only while retry attempts remain at most 20% of already-admitted logical contexts. Thus no retry is available before five logical contexts have been admitted. Unknown transport and interrupted admissions hold the run without retry.
- First non-filter HTTP 400/401/403 persistently stops new admissions across legs. Requests already admitted by another concurrent thread may still finish. Provider-filter/refusal cases remain quarantined across all legs, never bypassed.
- Prior model reservation **$215.3315657**, including separate prior confirmation **$37.2664193**, plus **$50** infrastructure and this pilot's maximum **$150**, totals **$415.3315657**, within the unchanged **$450** phase cap. Prior charges are not reset.

## Scientific and release boundaries

Luna payload, Kimi direct payload, original instructions, complete schema, deployment, effort and output limits retain the previous scientific messages. Astra alone includes the known transport fix: literal `Return JSON.\n` before the exact original source-JSON bytes. No physical mapping, cache key or release-mask metadata enters a prompt.

Field validation retains its complete field-local result. A failed unrelated field does **not** discard the successful fields. Only global parse/validator failure prevents a carrier. Root's separate projection component decides which exact policy-listed measure IDs may be released. All outputs remain machine research outputs, not human gold labels.

The short Kimi identifier `Kimi-K3.1` is accepted only against the exact pinned ARM evidence for the established Pro deployment, version and capacity. This is execution-scoped evidence, not an official model-alias claim. Unknown identities stop admission.

## Root-provided policy and pinned inputs

Required policy keys:

```json
{
  "protocol_version": "economic-pilot-20261119-v1",
  "released_measure_ids": ["ROOT_SUPPLIED_EXACT_IDS"],
  "phase_prior_reserved_nano": 215331565700,
  "prior_confirmation_reserved_nano": 37266419300,
  "phase_infrastructure_reserved_nano": 50000000000,
  "phase_cap_nano": 450000000000,
  "pilot_cap_nano": 150000000000,
  "pins": {
    "SCHEMA.json": "SHA256",
    "INSTRUCTIONS.md": "SHA256",
    "preparation/batch0001/INPUTS_PRIVATE.jsonl": "SHA256",
    "preparation/batch0001/PHYSICAL_ROWS_PRIVATE.jsonl": "SHA256",
    "preparation/batch0001/EXCLUSIONS_PRIVATE.json": "SHA256"
  },
  "code_sha256": {
    "pilot_common.py": "SHA256",
    "pilot_worker.py": "SHA256"
  },
  "runtime_sha256": {
    "field_validator": "SHA256",
    "frozen_validator": "SHA256"
  },
  "initial_batch_manifest_sha256": "SHA256",
  "kimi_arm_evidence": {
    "path": "DIRECT_ARM_DEPLOYMENT_PUBLIC.json",
    "sha256": "25352e137d33a6c8ab2088b0fe2f2da322764263561a95e78204bd1b55035870"
  }
}
```

Additional source, score, release-mask and version evidence is preserved through the whole-policy SHA. Do not mutate that policy after admission; changed identity is rejected. Do not transplant or reset the ledger to evade a stop.

Batch manifest keys: `batch_id`, `filenames` with `inputs`/`physical_rows`/`exclusions`, each corresponding `*_sha256`, and `previous_batch_manifest_sha256` (null for the first batch). Files resolve relative to the manifest. Root must explicitly pass its exact SHA. Later manifests append to the immutable registered chain; previous inputs are never rewritten. Input items retain the Stage5 `{case,row:{record_id,context_sha256,full_document},...}` shape, including `fresh_never_exposed: true`. Additional `partition: "pilot"` metadata is supported. Physical source rows and mappings remain separate pinned private files.

## CLI

```sh
python3 -B runtime/pilot_worker.py \
  --leg Luna \
  --directory /home/linkup/migration/pilot_economic_20261119/run01 \
  --policy /home/linkup/migration/pilot_economic_20261119/run01/policy.json \
  --batch-manifest /home/linkup/migration/pilot_economic_20261119/run01/preparation/batch0001/BATCH_MANIFEST_PUBLIC.json \
  --batch-manifest-sha256 ROOT_VERIFIED_SHA256 \
  --field-validator ROOT_DEPLOYED_FIELD_VALIDATOR \
  --frozen-validator ROOT_DEPLOYED_FROZEN_VALIDATOR \
  --workflow-directory /home/linkup/migration/code \
  --max-new-logical 100 --concurrency 2 --max-wall-seconds 14400
```

The hard live run directory and managed-identity helper directory cannot be changed by CLI. `STOP_REQUESTED` in the run directory (or explicit `--stop-file`) stops future reservations. Unknown in-flight state cannot be cleared by restarting. A known completed result is reused only after its saved SHA and policy/context identity match.

Private carriers: `results/<Leg>/<context-hash>/RESULT_PRIVATE.json`, with unchanged `payload`, `field_validation`, `record_id`, `context_sha256`, `case`, `leg`, `status` keys. Each raw response and visible response is immutable. The ledger pins each result path and SHA. `OUTPUTS_<LEG>_<batch_id>_PRIVATE.jsonl` is the current derived batch index, accounting for unprocessed contexts without pretending they are successful outputs. Its later replacement does not overwrite immutable response evidence.

Public metadata-only progress: `RUN_STATUS_PUBLIC.json`, `<LEG>_FINAL_PUBLIC.json`, `CHECKPOINT_FIRST_BATCH_PUBLIC.json`, and (once 100 logical contexts have been admitted) `CHECKPOINT_100_PUBLIC.json`. No case IDs, source context hashes, record IDs, source bodies or model output bodies appear in those public summaries. Transport-uncertain attempts prevent a claim of terminal no-active-request status.

## Offline verification

`PYTHONDONTWRITEBYTECODE=1 python3 -B test_pilot_runtime.py`

The suite uses synthetic sources, validators, identity and HTTP responses; network connections are blocked. It checks the initial-100 checkpoint and explicit continuation, no old 150-context cap, concurrent claims, cache SHA checks, original scientific-message equality, batch pinning/append chains, token windows, physical/dollar bounds, retry limits, fail-fast errors, quarantine, unknown-transport recovery, field-local preservation and public-data minimization. `RUNTIME_TEST_PUBLIC.json` records the result and hashes. Original runtime files remain hash-identical to `ORIGINALS_BEFORE_PUBLIC.json`.

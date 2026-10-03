# Measurement L2 scaffold

Status: local development infrastructure is ready; no paid or external batch API is available, no production L3 run has started, and no 200-record model run is claimed.

This directory implements the frozen `RESEARCH_CONTRACT.json` LinkUp definitions. It is deliberately small: one versioned extraction schema, one prompt, one semantic validator, and one local development/evaluation entry point. Raw advertisements and private locator maps must stay outside the repository.

## Routes

`agent-assisted bounded development` prepares a private 200-record pack and, only when supplied, materializes L1's frozen 80-key configuration-comparison manifest. It checks true source text locally and supports later import of offline JSONL extractions. It does not treat agent agreement as truth and must never be expanded into chat-based reading of the production frame.

`batch API` is unavailable. `config/batch_api_gate.template.json` records this as current state and keeps `production_l3_allowed=false`. This is not a pending user budget task.

## Commands

Prepare a private development pack after L1 materializes the final 200 texts:

```bash
python3 measurement/run_local.py prepare \
  --mode development \
  --input /private/L1_DEVELOPMENT_200_TEXT.jsonl \
  --output-dir /private/measurement_dev_v1 \
  --expected-count 200 \
  --comparison-manifest /private/L1_CONFIG_COMPARE_80_MANIFEST.parquet
```

The input can be JSONL or Parquet and must contain `JOB_HASH`, `SOURCE_FILE`, `SOURCE_ROW`, `RECORD_SOURCE_ROW`, plus a text column. Use `--text-column` if the text is not one of `original_text`, `text`, `DESCRIPTION`, or `description`. The 80-record pack is created only from L1's exact 80-key manifest; if it is absent, preparation produces only the full 200 development pack and does not redraw a substitute.

Import and validate offline extractions against the exact source text:

```bash
python3 measurement/run_local.py validate \
  --source /private/measurement_dev_v1/development_200.pack.jsonl \
  --predictions /private/development_predictions.jsonl \
  --receipt /private/development_validation_receipt.json
```

Prepare evaluation only from its separately locked 200-record input. Do not reveal evaluation before prompt/schema/model freeze:

```bash
python3 measurement/run_local.py prepare --mode evaluation \
  --input /private/L1_EVALUATION_200_TEXT.parquet \
  --output-dir /private/measurement_eval_v1 --expected-count 200 \
  --evaluation-lock-receipt /private/L1_EVALUATION_LOCK_RECEIPT.json
```

Evaluation preparation refuses to run without a receipt whose `status` is `locked_for_single_reveal`, whose `input_sha256` and `record_count` match the supplied file, and which records verified full-text grouping, zero within-evaluation duplicate groups, zero overlap with development and historical text groups, and verified exclusion-key manifests. The input is also checked locally for duplicate full-text hashes.

Estimate local workload from the real local text lengths:

```bash
python3 measurement/run_local.py cost \
  --source /private/measurement_dev_v1/development_200.pack.jsonl \
  --receipt /private/development_cost_receipt.json
```

The receipt calls character-to-token conversion a proxy, leaves actual API usage, price, and billed cost null, and never represents it as an API benchmark or invoice.

## Enforced semantics

- all four experience objects occur exactly once;
- `knowledge`, `proficiency`, and `training_certification` remain separate from `prior_experience`;
- negative, not mentioned, insufficient text, and unresolved remain distinct;
- every positive mention has an exact source substring and valid offsets;
- a duration is legal only inside a positive mention and must cite one of that mention's spans;
- OR/equivalent alternatives carry an explicit alternative group and no aggregate-years field exists;
- AI development and use of AI to write software have different role/basis combinations;
- failed or unresolved records are never converted to zero.

Run the synthetic acceptance check with `python3 -m unittest measurement/tests/test_measurement.py`. It verifies the valid fixture and rejects a bad offset, an unbound duration, and zero-filled negative/unresolved findings.

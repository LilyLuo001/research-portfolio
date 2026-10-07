# Fixed 10,000 text handoff

`prepare_fixed10000_text_adapter.py` converts the frozen private sample locators into the exact selection and source-map interface consumed by the existing regional `materialize_selected_text.py` tools. It does not read raw job text, call a model, install packages, or change the frozen sample.

Run it on a host with access to the frozen regional plan files and write its output to a private directory outside the repository:

```bash
python prepare_fixed10000_text_adapter.py \
  --sample /public/home/lilysharp/linkup_analysis_execution_oct02/private/next_stage_20261004/linkup/run-123660254/FIXED_RESEARCH_SAMPLE_KEYS_PRIVATE.parquet \
  --source-plan /public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan/plan.jsonl \
  --source-plan /public/home/lilysharp/linkup_release_v1/semantic_v1/final_gate_wuzhen/plan.jsonl \
  --output-dir /public/home/lilysharp/linkup_analysis_execution_oct02/private/next_stage_20261004/text_handoff_20261007/run-123660254 \
  --public-receipt ../FIXED10000_TEXT_HANDOFF_RECEIPT.json
```

Run the generated `RUN_MATERIALIZE_FIXED10000_KUNSHAN_PRIVATE.sh` only on Kunshan and `RUN_MATERIALIZE_FIXED10000_WUZHEN_PRIVATE.sh` only on Wuzhen, with its source-map entries available on that host. Each calls the paired fixed-10,000 materializer in this directory; that file preserves the frozen exact locator/hash verification and changes only the cap from `(40, 200)` to `10000`. The receipt has input/output hashes and counts, while raw text remains private.

## Submitted jobs (2026-10-07)

Kunshan `123910578` and Wuzhen `46027883` were both verified RUNNING in the last bounded snapshot (elapsed 1m21s / 2m10s). These are raw-text materialization jobs, not model inference. Final text and receipts had not yet been retrieved; selection counts are not processed-row counts. See [TEXT_JOB_STATUS.json](TEXT_JOB_STATUS.json).

## Verified partial retrieval, 2026-10-07

Wuzhen job `46027883` completed successfully. Its 4,505 exact source texts were collected privately and checked against the selected canonical keys and materialization hashes. `WUZHEN_CORPUS_READINESS_AGGREGATE.json` reports workload only: 3,666 unique exact texts, 839 repeated rows beyond those unique texts, and no empty texts. The regional file partition is not a representative analytic subgroup. Character lengths are Unicode code points, not model tokens.

Kunshan job `123910578` was still running at the most recent recorded check. The full 10,000-row merge/cache has not yet been produced. All rows and weights will remain in the analysis even where model output is cached for identical text. See `TEXT_JOB_STATUS.json` for the timestamped evidence and `summarize_corpus_readiness.py` for the reproducible workload calculation.

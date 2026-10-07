# Compact measurement diagnostic source pack

This is a capped diagnostic round, not a redraw of the fixed 10,000-row sample and not a main estimator or population-precision exercise. The heldout core contains eight A and eight B records; C is outside this diagnostic.

Reader-facing files use exactly two fields per JSONL record: `record_id` and exact, untruncated `original_text`. The review IDs are opaque. Reader-facing files contain no arm, source filename, canonical locator, or reference label.

Private inputs for blind review:

- `private/source20_pack/development4/SOURCE_PRIVATE.jsonl`: byte-for-byte copy of the prior four-record pilot source.
- `private/source20_pack/heldout16/SOURCE_PRIVATE.jsonl`: newly selected heldout eight A plus eight B, presented blind.
- `private/source20_pack/source20/SOURCE_PRIVATE.jsonl`: combined twenty-record reader source, with the unchanged development four first.
- `private/source20_pack/UNBLIND_MANIFEST_PRIVATE.jsonl`: separate private mapping from review ID to split, arm, canonical key, and exact source SHA-256.

`build_source20_pack.py` reproduces selection from the verified merged fixed-sample Parquet and discoverable earlier review sources. `SOURCE20_SELECTION_RECEIPT.json` publishes counts, exclusions, deterministic method, invariants, and whole-file hashes without publishing identifiers or text.

After both independent readers finish, `compare_readers.py` binds their twenty JSONL rows to this source order and the private unblind manifest. It reports strict validator results separately from agreement on object state, the required/unconditional/prior-experience main estimand, complete strength/mode/scope signatures, and duration signatures bound to each object. Its public output contains aggregate counts only; its private output lists source-keyed disagreements and validation failures without copying source text.

Example invocation:

```bash
python3 compare_readers.py \
  --source private/source20_pack/source20/SOURCE_PRIVATE.jsonl \
  --unblind-manifest private/source20_pack/UNBLIND_MANIFEST_PRIVATE.jsonl \
  --reader primary=private/reader_primary.jsonl \
  --reader blind=private/reader_blind.jsonl \
  --reader-order primary=private/reader_primary.ORDER_PRIVATE.json \
  --reader-order blind=private/reader_blind.ORDER_PRIVATE.json \
  --public-output READER_AGREEMENT_PUBLIC.json \
  --private-output private/READER_DISAGREEMENTS_PRIVATE.json
```

## 本轮最终结果

本轮已完成20条双读者诊断及一次根代理裁决；未启动正式批量。见[结果与裁决](RESULTS_AND_DECISION_CN.md)、[最终裁决回执](ROOT_FINAL_DECISION.json)。读者最初声称的20/20校验包含改变语义字段或删除证据，已与首轮盲比较分离，不能用于正式验收。

# fixed10k 正式生产 Batch 001 结果

本批是既有 fixed10k 的首批 100 份正式生产，不是新试点或最终样本。结果仅覆盖这 100 个直接上下文的全正文语义判断；不据此报告总体比例、准确率或全框完成度。

1. **新增处理量：**100 个上下文由主审完成并经五个 20 条 Formal800 验证包全部通过；覆盖 700 个上下文—字段单元、784 个广告—字段行和 112 条广告。账本仍为 70,000 行，七个字段族各 10,000 条。
2. **复用量：**0 个既有完成字段单元复用为本批判断；100 份直接判断精确覆盖 112 条广告，其中 12 条是同一上下文带来的额外广告，不是新增阅读。已有字段及既有 308 个已审未知未整体重审或重入队。
3. **最终未知量：**本批有 5 个上下文在至少一个字段族保留 `unknown_or_conflict`；它们是审后未知，不被当作负例。
4. **剩余量：**仍需新审的上下文为 6,799；另有 313 个已审但仍含不确定性的上下文。6,799 表示至少缺一类判断，并不表示每个上下文需从零重读全部七类。
5. **产物位置：**私有账本、待审队列和不确定登记册分别位于 WZ 的 `/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/batch001/final/FIELD_PROVENANCE_LEDGER_PRIVATE.jsonl`、`/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/batch001/final/REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl`、`/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/batch001/final/REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl`，SHA-256 依次为 `435c7262700a42c4571160e772158f1344a58d39ee387be4436172b8053f5403`、`902f21c05dac1b02c37bda034f035c4a21b12a69ba893fb6088a7ed5a24bd0f4`、`41d7e50153aa99bebd51d2cd1634a8eb2457512367234ba34e9c4fa142991254`。公开汇总为 `public/BATCH001_RESULTS_PUBLIC.json`，最终回执为 `receipts/BATCH001_FINALIZE_RECEIPT.json`。
6. **实际耗时：**本轮正式生产从 2026-10-17 05:32:31Z 开始，到主审及回填在 06:03:02Z 完成，共 30 分 31 秒。最终任务 WZ job `46767649` 于 14:02:52 至 14:03:02 完成，退出码 `0:0`，回填耗时 10 秒；五个验证回执均为 `pass`。
7. **具体阻碍：**首次 job `46767563` 在汇总未知数时漏传队列定位参数，14 秒后以 `1:0` 终止，未写出最终产物。已将该统计改为直接计数 `unknown_or_conflict`，未改 taxonomy、schema 或任何审阅输入；重试成功。

最终回执断言：100 份均已验证、700 个单元均按七字段族替换、未覆盖已有 `known`／`not_applicable`／`unknown_or_conflict`，且非本批账本行原样保留。

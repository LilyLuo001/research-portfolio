# D59–D62 continuation status

This directory records the cloud-only continuation after the accepted five-shard baseline. Public files contain methods, execution paths, aggregate receipts, and QA only; private manifests, credentials, raw text, row-level outputs, and temporary payloads remain excluded.

## Current status

- **BU13 return:** verified and cleaned. Job `124118871` completed with exit 0; 54 files and 597,922,077 verified bytes passed hash checks. The 13-shard QA aggregate is 1,097,202 postings and 5,603,232 evidence rows with global `JOB_HASH`/locator uniqueness. Cleanup removed only the verified returned/staging artifacts and dedicated task credentials; SCNet originals, public receipts/code/logs, and unrelated job `7488095` were preserved. See `BU13_DOMESTIC_RUN_RECEIPT_PUBLIC.json`, `SHARD_SET_13_QA_PUBLIC.json`, and `BU_CLEANUP_D60_PUBLIC.json`.
- **WZ production:** accepted. Four production tasks completed under job `46208844`; QA `46209816` passed with 342,546 postings, 1,753,539 evidence rows, and 186,863,325 bytes. See `ROOT_WZ4_ACCEPTANCE_PUBLIC.json` and `domestic_wz_d60/`.
- **Metadata:** first-five metadata accepted; full-corpus inventory and remaining domestic expansion are pending. The earlier metadata chain was stopped after its replacement was accepted; no completed R1 receipt exists. D62 metadata chain completed: prepare `124124920` and finalizer `124124933` passed; the four-batch execution receipts record complete scans of 356,449,214 Records rows and 356,299,258 O*NET rows. For the first-five-shard metadata output: 424,226 Record keys were 1:1, 424,072 O*NET rows matched and 154 were missing, 424,014 had official occupation, and 421,114 had complete company×occupation×region fields. This is a bounded metadata result for the first five shards; the 17-shard wave is not full corpus, was not directly cross-scanned for global keys, and does not establish semantic gold, population validity, or causal validity.
- **D62 fast path:** the Arrow exact-hash prefilter and fixed semantic gates are prepared. Qualification `124122881` passed the stated checks on real O*NET input (524,288 rows, 602 exact hits) and real Records input (82 rows, 0 hits), plus synthetic edge cases. These are qualification checks, not a real Records accuracy or production-performance claim.
- **Routing boundary:** D60 ended future BU bulk permissions. Subsequent bulk extraction and metadata joins are intended for in-place SCNet China execution; no 26.6 GB metadata cache transfer to BU is authorized.

## Historical failures and corrections

- Wrapper job `46208826` failed before data output; the later WZ run corrected module load order. The failed receipt remains immutable.
- BU metadata discovery `8005585` was stopped with no retrieved files; its public cancellation receipt is retained.
- Earlier BU13 attempts `124117556` (failed) and `124117634` (duplicate cancellation) remain historical; `124118871` is the accepted replacement.
- The prior metadata attempt produced only an unaccepted partial temporary artifact; no completed R1 receipt exists and it is not merged into results.

No document here claims population representativeness, causal effects, semantic validity, or full-corpus completion; final receipts can establish engineering completion only within the documented shard and metadata scope.

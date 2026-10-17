# Independent QA: fixed10k production coverage reconciliation

**Decision: PASS.** This QA accepts the coverage inventory produced by SCNet job `46764737` and does not certify semantic accuracy or completion of Scheme 2.

## Accepted execution and artifacts

- Scheduler state: `COMPLETED`, exit `0:0`, elapsed `00:00:55`, 2 CPU and 4 GB, as recorded in `receipts/SCHEDULER_RECEIPT.json` (SHA-256 `7f28cb2fb7659eaaad73829353059a11ea074ba9d9e007effe7aaa29b599d8b6`).
- Executed analyzer SHA-256: `4697d56d9660cdd7ea5c26505ab3d917466c6f67d2552c5d39a0a7ceee1e9110`, identical to the repository analyzer and the hash embedded in `receipts/ANALYSIS_RECEIPT.json`.
- Wrapper SHA-256: `4bc6d75190087c1f5208ee1ed580b5051b24165f93802973d8c2cac87e83c10d`.
- Public aggregate SHA-256: `53dcf3edbb9a4c5a1e64e331f8ff4f85d41fe841987022440f8296f00d125531`, identical to the receipt.
- Earlier jobs `46764472`, `46764510`, and `46764596` are explicitly excluded. Their outputs are absent from the accepted local artifacts; the completed but rejected attempt is recorded as quarantined.

## Independent checks

1. **Frame and denominator conservation passed.** The accepted receipt reports 10,000 ads, 7,635 raw exact texts, 7,617 frozen-normalized complete inputs, and 70,000 ad-field ledger rows. Independent summation of the public table gives exactly 10,000 ads for each of all seven required field families.
2. **Source binding is disclosed at its actual scope.** Formal800 binds 719/719 source rows, Wave01 14/14, Batch001 24/24, and Batch002 128/128. Wave02 remains 0/96 after exact-raw and full-normalized-input binding paths; it contributes no assignment to this frame and is reported as an unbound retained source. This is not evidence that Wave02 is invalid.
3. **Legacy status handling passed.** Batch001/002 strict zeros are not mapped to semantic absence. Their partial positive evidence, six object-outcome unknowns, 20 duration errors, and 11 unknown durations remain distinguishable in the aggregate adapter counts. These sources do not create technology, entry, or responsibility coverage.
4. **Queues are separated correctly.** `REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl` contains 6,899 unique contexts with at least one partial or missing field family. `REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl` separately contains 308 contexts with reviewed unknown/conflict fields; 37 contexts occur in both only because other fields still require work. The counts must not be summed as disjoint workload.
5. **Claims and privacy passed.** Public artifacts contain aggregates and hashes, not ad text or quotes. `COVERAGE_RESULTS_ZH.md` (SHA-256 `81495ab957fb4cc1d3f26ba3b3969ff6a8f7fdfad369e2b8f23e86d6518917ee`) distinguishes never-reviewed fields from rule/legacy candidates, describes exact reuse as reuse rather than new review, and makes no prevalence, accuracy, causal, or whole-project-completion claim. `ROOT_ACCEPTANCE.md` preserves the same boundary and states that semantic completion remains outstanding.

No material issue remains within the fixed reconciliation contract. The accepted private queue and uncertainty register are the continuation artifacts; this PASS does not authorize treating unresolved or unreviewed fields as completed labels.

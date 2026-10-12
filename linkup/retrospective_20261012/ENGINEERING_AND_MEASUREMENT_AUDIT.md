# Engineering and measurement audit

Scope: concise retrospective from the late private history (Oct 7--11) and published receipts. This is not a complete code audit: the delegated Sol engineering capacity was unavailable, and no unreviewed source was represented as inspected.

## Verified runtime record

- Text materialization completed for the frozen fixed10k: 10,000 rows, 7,635 exact unique texts, zero empty texts, and preserved locators/weights. See [`FIXED10000_EXACT_TEXT_CACHE_RECEIPT.json`](../analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/text_handoff_20261007/FIXED10000_EXACT_TEXT_CACHE_RECEIPT.json).
- A local-model route failed first on proxy/compiler deployment and later on semantic object/binding errors; it was correctly not scaled ([1098--1118]). CPU/format success is not semantic qualification.
- Scheduler failures `124117556` (missing log directory), `124117634` (duplicate, cancelled), and `124118220` (launch) occurred before data QA; replacement `124118871` passed file/shard/key checks ([1344--1351]). Initial fast metadata chain `124124467` failed from an initialization path and dependents cancelled; replacement chain ran ([1361--1364]). These are orchestration defects, not evidence of data loss or negative findings.
- D60 is operative: the roughly 2.18-GB BU batch was the final BU use; subsequent bulk work remains on Chinese SCNet resources. No inference/API claim follows from scheduler use.

## Measurement record

- Rule/code production provides candidate wording fields, evidence spans, row conservation and explicit unknown states. It does not provide human gold labels or population semantic accuracy.
- The finite Pro workflow has exact record-bound review increments: Wave01 14 contexts and Wave02 96 purposeful contexts. It may change only exact reviewed rows (or logged identical evidence contexts); it is not a corpus-wide correction model.
- Do not use HIP/accelerator or CPU availability as a proxy for model quality. The successful reusable compute pattern is scheduled CPU code applying frozen rules, with independent row/key/evidence checks, no paid API, and no bulk conversation-model labeling.

## Operational conclusion

Reuse the fixed10k text/locator/weight infrastructure and frozen code outputs. Keep scheduler receipts separate from semantic acceptance, preserve launch/transfer failures honestly, and do not reopen local-model deployment, paid API, SCNet CLI, or BU expansion.

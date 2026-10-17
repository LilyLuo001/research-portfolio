# Fixed10k coverage reconciliation: root decision

Date: 2026-10-17. Scope: reconcile existing semantic artifacts with the original prepared 10,000-ad frame. This release does not complete Scheme 2 semantic production.

## Accepted execution

Wuzhen scheduled job `46764737` completed in 55 seconds with exit `0:0`, using 2 CPU cores and 4 GB RAM. The queue required a DCU reservation; this computation used CPU code and does not claim DCU acceleration. Accepted analyzer SHA-256: `4697d56d9660cdd7ea5c26505ab3d917466c6f67d2552c5d39a0a7ceee1e9110`. Prior attempts are recorded and excluded in `receipts/SCHEDULER_RECEIPT.json`.

The denominator remains 10,000 ads, 7,635 distinct raw texts and 7,617 distinct frozen normalized full inputs. The private ledger has 70,000 ad-field rows; all seven field-family denominators conserve 10,000 ads. No new sample, semantic reading, model inference, parser extraction or analysis estimate was produced.

## Decisions from the result

- Continue from `REQUIRED_NEW_CONTEXT_QUEUE_PRIVATE.jsonl`: 6,899 unique complete contexts have at least one unfilled or partially covered field family. Retain their completed fields; this is not an instruction to redo all seven families for every context.
- Keep `REVIEWED_UNCERTAINTY_REGISTER_PRIVATE.jsonl` separate: 308 contexts have reviewed unknowns/conflicts. Of these, 37 also need other fields and therefore appear in both files. The two headline counts must not be summed as disjoint work.
- Formal800's 719 final judgments bind to 1,981 ads: 800 direct assignments, 1,160 additional raw-exact matches and 21 additional identical-normalized-input matches. These are reused judgments, not 1,981 newly reviewed ads or new accuracy evidence. Published Formal800 estimates and weights remain unchanged.
- Older Batch001/002 and Wave01 artifacts are retained at their actual field scope. Strict-rule zero is not absence of an experience requirement. Partial/question-specific evidence cannot certify unmeasured fields.
- Wave02's 96 accepted reviews have no verified raw/full-input match in this particular 10,000-ad frame. Preserve them separately; neither discard them nor count them toward this frame's coverage. Earlier diagnostic reviews without a bindable accepted structured artifact are disclosed in the inventory rather than invented as completed labels.
- Unknown and conflict masks remain in force. No majority vote, recency preference, fuzzy match or JOB_HASH-only transfer is used to turn them into known values.

## Acceptance and handoff

Root accepts the coverage inventory and private continuation queues after independent QA passed, as recorded in `qa/COVERAGE_QA.md`. Sol/medium implemented and ran the cloud job; an independent Sol/medium reviewed contracts and aggregate checks; Terra/medium documented sources and results. Root made binding/scope decisions and reviewed the final claims.

The next production input is this existing queue, with source locators, field requirements and provenance already attached. No new overall plan, sample or parser-development cycle is needed. Actual semantic completion of these remaining contexts is still outstanding; this release must not be cited as that completion, whole-corpus semantic certification or permission to infer historical description versions.

Private artifacts stay under `/work/home/lilysharp/private/production_coverage_20261017/private/`. Git contains code, source inventory, aggregate counts and sanitized receipts only.

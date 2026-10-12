# Late-history audit: 2026-10-07 through 2026-10-11

Private source read in bounded chunks: `private_history/05_oct07_through_oct09.txt` (129,410 bytes; IDs 1084--1306) and `private_history/06_oct10_through_oct11.txt` (120,402 bytes; IDs 1307--1541). This memo has no raw text, keys, credentials, or row-level decisions. IDs/timestamps are private-history locators.

## Plan B: intended choice versus what happened

The intended transition was not another cleaning pass. It was: reuse the frozen 10,000-ad/7,635-unique-text sample, use code for deterministic evidence/format work, use a lower-cost model for contextual relations, use GPT-6 only for bounded design/acceptance/adjudication, then update fixed-sample tables. The assistant eventually stated that architecture clearly at [1273, 2026-10-09 05:43:53Z]; the user chose its code-plus-midrange-model option at [1274, 06:23:55Z].

Actual execution departed twice:

- **Local-model/CLI route:** complete texts were assembled (10,000 ads, 7,635 distinct texts) but local-model output made core object/binding errors, so it was stopped rather than scaled ([1116--1118, 2026-10-07 11:53--13:04Z]). A later fixed 20-context test still had shared misclassification ([1123--1125, 14:11--14:52Z]). The full sample was therefore a prepared measurement frame, not validated semantic production.
- **API/model-service route:** a batch-Astra cost scenario was prepared, but the user explicitly rejected paid API use: Pro-only, bring bounded decisions back to the conversation ([1276--1277, 2026-10-09 06:26--06:27Z]). The earlier all-GPT-6 production suggestion was explicitly withdrawn as unjustified ([1271--1273, 05:37--05:43Z]).

The durable Plan B is consequently rule/code production with explicit unknowns, plus bounded Pro review bound to exact evidence—not a lower-cost-model production system and not a full-corpus semantic certification.

## Completed assets, failures, and their meaning

| Item | History evidence | Correct status |
|---|---|---|
| Fixed text frame | 10,000 sample ads / 7,635 distinct texts assembled and independently checked [1117--1118]. | Reusable input/text-and-weight mapping; no semantic-validation implication. |
| Probability design | A=10,075 all included; B controls sampled within 69 support cells to 30,225, total 40,300. Public release-v2 methods records per-cell inclusion probability and inverse-probability reconstruction. | Valid old candidate-frame sampling design. It does not validate labels, represent all postings, or make fixed10k a probability-labelled subsample unless its own manifest shows that relation. |
| Local inference attempt | Network proxy failure before inference [1098--1099]; later compiler/model setup worked but real outputs failed semantic requirements [1116--1118]. | Infrastructure success is not measurement success. No restart/scale justified. |
| Rule-first 10k run | 7,635 texts processed; coordinate/format checks passed; candidate flags and fixed-sample T1--T6 published [1279--1289]. | Engineering/rule candidate outputs only. The assistant correctly separated code completion from research-variable acceptance at [1282, 07:28:23Z]. |
| 14-context Pro Wave01 | 14 existing unreviewed texts; 55 candidate findings: 21 confirmed, 32 corrected, 2 unresolved; evidence binding validated by job 124250182 [1512--1518, 2026-10-11 22:33--22:52Z]. | Exact, purposive review increment. It validates those decisions, not an error rate or corpus labels. |
| Wave02 preparation | First selection job failed because conditional cases were ordered after unresolved cases [1536, 23:38:15Z]; fixed preparation job 124252012, 96 actual contexts, same comparison universe/weights planned [1537--1541]. | A finite review wave with a documented selection failure/fix; review impact must remain limited to exact reviewed rows. |

## No-human, no-paid-API, no-CLI constraints

- The history contains no human gold-label completion. Early “human review” readiness is a protocol/availability fact, not completed human labels; later actual semantic decisions are Pro conversation-model decisions and must retain that provenance.
- No paid API was authorized after [1276]. Claims of zero API spend are compatible with code/rule production; they do not make all rule outcomes semantically accepted.
- Codex CLI on SCNet was explicitly closed after the user reported it unsupported ([1523--1527, 2026-10-11 23:17--23:21Z]). Earlier CLI/install attempts are failed/superseded engineering history, not a viable current route.
- The final BU scope was narrowed by the user: the approximately 2.18-GB batch was the last BU use; subsequent bulk execution stays in China ([1323--1329, 2026-10-10 02:15--02:31Z]). D60 preserves that boundary. Do not propose a new BU run or transport of a large metadata cache.

## Engineering attempts that must not be remembered as data failures

- Cross-site transfer was slow but live ([1314--1319]); this is an operations constraint, not evidence against the data/rule.
- `124117556` never started because of an absent log directory; `124117634` was a duplicate cancelled job; replacement `124118871` passed 54-file and 13-shard QA ([1344--1351, 04:54--05:11Z]).
- The first fast-metadata chain failed from an initialization-path error and dependent tasks were cancelled; repaired `124124920` completed, followed by replacement extraction/QA ([1361--1364, 06:01--06:09Z]). Treat cancelled/launch failures as no-processing attempts, not negative results.
- D65 later established the larger conceptual correction: D63/D64 counts were a newer rule version, while the old 2,464-shard base was already complete. This history explains the wasted expansion path; it cannot justify calling base cleaning unfinished.

## Fixed10k and finite Pro-review reuse contract

1. Reuse the fixed10k only with its manifest's canonical keys, source-text hashes, original sample-arm label, stratum, inclusion probability/weight, and explicit **rule-version** output. The contract is verified in [`SAMPLE_EXECUTION_RECEIPT.json`](../analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/linkup/artifacts/run-123660254/SAMPLE_EXECUTION_RECEIPT.json): 4,000 A, 4,000 B and 2,000 C, with `total_inclusion_probability = original_inclusion_probability × conditional_inclusion_probability` and `nested_design_weight` its inverse.
2. The fixed10k is nested within the accepted 40,300 candidate sample but is its own second-stage probability design. A is explicit GenAI **use**; B is explicit traditional-software **use with no detected AI**; C is a residual inside the technology-screened candidate frame and is not an occupation-wide background arm. Thus arm labels remain candidate-rule labels, and C is not a valid all-other-jobs contrast.
3. Development material (200 texts; the 20/24 diagnostic reads) is contaminated for evaluation and cannot become a fresh independent accuracy set. Locked eval80 is excluded from Wave02 selection by public receipt, but exclusion does not demonstrate its labels exist or are validated.
4. Wave01 14 and Wave02 96 are purposive semantic review artifacts, not additional sampling frames. Apply a review decision only to the exact same text/context or explicitly logged exact-context reuse; preserve unreviewed and unresolved states.
5. Exact text recovery is complete without re-extraction: [`FIXED10000_TEXT_HANDOFF_RECEIPT.json`](../analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/text_handoff_20261007/FIXED10000_TEXT_HANDOFF_RECEIPT.json) confirms 5,495 Kunshan plus 4,505 Wuzhen records and canonical-key conservation; [`FIXED10000_EXACT_TEXT_CACHE_RECEIPT.json`](../analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/text_handoff_20261007/FIXED10000_EXACT_TEXT_CACHE_RECEIPT.json) confirms all 10,000 texts, zero empty exact-text rows and 7,635 unique texts while retaining all probability/weight fields. The 69 L1 support **cells** must not be confused with D67's 69 QA-passed **shards**.
6. No additional targeted-100 correction loop follows from this history. The 96-context Wave02 was the authorized finite next wave; once its before/after tables and unresolved counts were published, the decision is to freeze it and name remaining candidate fields honestly.

## Vendor Job Postings delivered schema

The actual delivery audit is decisive, not product marketing. The inspected 19 annual files share a 28-column schema containing identifiers, company/role, O*NET/geography, salary/predicted fields, post/remove dates, parent, remote, expected hires, and sources. It contains **no description, explicit experience years, seniority, education, skills, or requirement fields**. Therefore it cannot be used as a reference or cross-check for those semantic measures, and no later plan should imply otherwise. Its usable role is metadata/coverage/identity and date-related provenance only. This strengthens the reason to retain LinkUp full-text evidence for clause-level experience, alternatives, and responsibilities.

## Decision-ready reading

The reusable outcome is a frozen base plus finite, versioned rule measurements and exact bounded Pro corrections. The history supports neither restarting sampling/parser development, reopening paid/API/CLI/BU channels, nor declaring a model/human-validated full corpus. A final plan should consume the already-published old base, D67 overlap, and Wave01/Wave02 increments; show original candidate versus exact review-corrected estimates where available; and carry unresolved semantics as unknown.

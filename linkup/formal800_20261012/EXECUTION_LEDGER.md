# Formal 800 review execution ledger — 2026-10-12

Current status: sample freeze completed in Wuzhen job46364888; finite Pro primary reading and independent blind review are in progress. No final semantic comparison is complete yet. Earlier preparation entries below are retained as history and are superseded by the actual freeze section.

- Scope: existing fixed 10,000 exact-text sample with nested probability metadata; maximum 800 ads (duplicate contexts may be read once but remain ad-level records).
- Arms: A 320, B 320, C 160; remaining capacity is reserved by the documented review design and does not expand the cap.
- Model path: Sol medium was attempted first and failed capacity before action. This is an engineering capacity failure, not a semantic model substitution. Terra medium is the conditional primary fallback; if Sol cannot be retried at packet readiness, Terra medium is primary with independent GPT-6 medium audit at 20%; root adjudication remains capped at 40 high-effort cases.
- Analysis: scheduled SCNet China jobs only for sampling, validation, weighting, aggregation, and uncertainty. WZ preflight job 46362837 completed in 11 seconds. KS2 CPU sanitizer job 124276150 completed in 5 seconds. The freeze job has not been submitted; it remains pending SHA-only exclusion transfer.
- Provenance: `linkup/formal800_20261012/EXECUTION_LEDGER.md` is the authoritative stage ledger; private packets, raw text, IDs, and review outputs remain excluded from Git.
- Ownership: formal800_cloud_terra owns sampler/cloud execution; formal800_qa owns independent QA; root freezes schemas and decisions.
- Prohibitions: no BU work, paid API, new model deployment, full-base re-extraction, private Git data, raw text, record IDs, row-level review outputs, credentials, or `private_history`.
- Historical record: retrospective `ROOT_HISTORY_AND_DECISION.md` remains unchanged; this ledger records the later approval and engineering status.

## Historical preparation artifact statuses (superseded by actual freeze)

| Artifact | Status |
|---|---|
| Frozen sample manifest | pending cloud receipt |
| Pro review packets/decisions | not started |
| Independent blind review | not started |
| Root adjudication (max 40) | not started |
| SCNet validation/aggregation | not started |
| Public acceptance receipt | pending all named outputs |

The freeze stage is intentionally still pending the separate SHA-only transfer receipt; this commit does not claim a frozen sample or semantic completion.

## Actual freeze and reading start

- WZ freeze46364558 failed after 2m48s on null legacy upstream weights before sample selection. Root decision12 keeps these ads eligible for the finite fixed10k target; no imputed upstream weights and no parent-frame inference.
- WZ freeze46364888 completed, exit0, 3m33s: 9,282 eligible ads,718 excluded;800 sampled ads,719 distinct contexts;160 audit ads,153 distinct contexts. All37 primary/audit transport files passed SHA-256 verification.
- Historical raw manifests were not transferred after automatic review rejected that route. Scheduled KS124276150 emitted a hashes-only file (no text or ad keys), whose SHA agrees on KS, local protected staging, and WZ.
- All54 existing entry-candidate ads were included; shortages reallocated within arm by the predeclared rule. No outcome-based replenishment.
- Sol/medium primary packet001 and independent Sol/high blind audit records1–20 are now actually dispatched. No semantic packet is yet accepted; outputs require scheduled validation. The conditional Terra/GPT-6 fallback was not used.
- Final comparison tables remain pending the finite reading/audit/validation work. Existing full-corpus outputs remain intact.

## Reading and cloud QA checkpoint (16:55 China time)

- Authored primary001–003:60 contexts; blind audit001–002:40 contexts. Authored does not mean accepted. Current parallel work: Sol/medium primary_b packet007; Sol/medium primary_c packet004 plus specifically rejected003 records; independent Sol/high audit003.
- Validation46366447 rejected2 of20 initial primary001 records; originals retained and corrected. Validation46367639 rejected2 of40 combined001–002 records, both in002; originals retained and corrected. Validation46368747 accepted50 of60 records and rejected10 in003 for outcome/explicit-clause inconsistency. This is a finite record repair, not rubric development.
- Independent audit validation46368752 accepted17 of20 and rejected3 for branch/evidence/field consistency. It did not compare audit labels with primary decisions. Only audit-specific errors are returned to the blind reviewer.
- No formal800 semantic acceptance or aggregate result is yet claimed. The full sample, definitions, exclusions, and weights remain frozen.

## Frozen review continuation and first passing audit packages

- WZ46370420 (5s) passed repaired audit001:20/20 records, zero errors. WZ46370425 (3s) passed audit003:20/20 records, zero errors. These certify mechanical identity/evidence consistency only.
- WZ46370126 examined100 primary review rows and retained92 valid records. It rejected six semantic-output/evidence inconsistencies plus two duplicated IDs, which also left two frozen records without reviews. Packet007 was preserved, its two missing originals were actually read and authored, and identity order was rebuilt; packet004 quote/field inconsistencies were repaired. No rejected or missing record enters aggregation.
- Complete authored primary files now cover001–008; audit files001–004 are written. Cloud acceptance remains separately tracked. Sol/medium primary_b continues009; a fresh Sol/medium primary_d owns010 because the prior reviewer reached context capacity before saving010 output. Sol/high audit continues005. Read-but-unwritten work is never counted.

## 19:15 checkpoint: fixed packets and scheduled validation

- Complete authored primary001–010 and blind audit001–006 are preserved privately; authoring is separate from acceptance. Primary011–012 and specific rejected004–008 repairs are assigned; primary013 is reserved to the repairing reader only if capacity permits. Blind audit007–008 remain the frozen final audit units.
- Stalled local SSH submission was terminated only after scheduler history showed that its three jobs had not submitted. Replacement WZ46382193 validated primary004–008:91/100 valid,9 record rejections. WZ46382210 passed repaired audit002:20/20. WZ46382212 rejected2/20 audit004 records; WZ46382213 rejected1/20 audit005 records. These exact records are returned to their appropriate reviewers; no sample, definitions or validator changes.
- Audit001/002/003 each have a passing scheduled evidence/identity receipt (60 contexts). This is mechanical validation, not a claim of semantic accuracy. Full release and comparisons remain pending.
- QA jobs request2CPU,4GB,10min and the Wuzhen partition-mandated oneDCU; code executes onCPU. Observed QA runtimes1–4s. No accelerator utilization claim.

## Audit through120: mechanical acceptance checkpoint

WZ46382515/46382517/46382521 completed0 in2s/5s/2s and passed audit004/005/006, each20/20. Together audit001–006 have120 mechanically valid contexts; semantic disagreement is assessed only after independent primary coverage is complete. Primary009–010 job46382523 accepted39/40 and rejected one missing supporting experience clause. Fresh independent Sol/high audit_b owns the final33 frozen audit contexts; its identity is passed explicitly to the slice validation wrapper.

The validation orchestration now permits distinct transport slices of the same frozen global audit packet ID. Duplicate packet/file assignments are rejected; the unchanged core validator still rejects duplicate/missing records. No semantic schema or acceptance rule changed.

## Frozen blind reading complete; remaining primary packets continue

All153 audit contexts are authored, audit007 validation46383553 passes20/20, final13 repaired audit008 validation46383927 is pending. Generic ability to work independently was rejected as insufficient evidence of explicit judgment under the unchanged rubric; the independent auditor preserved its intermediate correction and final source-grounded decision. No primary/audit comparisons were disclosed during repairs.

Primary001–013 are authored. Consolidated001–011 validation46382806 rejected4 records, all in011, for literal year/quote/tool-clause consistency; Sol/medium repair_i corrected them against originals. Revalidation46383930 is pending. Primary012–013 validation46383612 rejected23 records, mainly unmatched branch IDs and exact quotation characters; rejected012 and013 records are separate bounded repair tasks. No source, sample, definition or core validator change. Primary014/015 continue.

Static finish-wrapper QA's schema-location concern was checked against the actual server: code/FORMAL800_REVIEW_SCHEMA.json exists,11586bytes, SHA256 fdc5b0d653bd8f1c98a3e6cd20970156621403154a7ad073e977ea14ddfb310e, identical to accepted receipts. The repository root location differs from the deliberate deployed code path. Final analysis remains unrun until all required reviews and bounded adjudications pass.

## First220 primary and all153 audit contexts pass mechanical checks

WZ46383927 completed0 in2s and passed final audit008; all153 independent audit contexts now have passing slice receipts. WZ46383930 completed0 in3s and passed primary001–011,220contexts,zero errors. This is identity/evidence/schema acceptance; semantic agreement/root review and final analysis remain pending. Primary014 is authored and validator46384192 is pending; primary015/016 are active. Packet012's13 rejected rows are repaired with preserved originals; packet013's10 rejected rows are assigned separately. The independent audit reading scope is closed.

Final delivery retains the advertisement-level measured dataset privately onSCNet, linked to validated evidence; only aggregate tables/code/methods/receipts enterGit.

## Recovered packet and additional40 accepted

WZ46384738 completed0 in2s and accepted all40 primary012–013 contexts; primary001–013 now260 mechanically accepted. The014 writer had accidentally overwritten20 authored records with2; exact original authored records were recovered from that reviewer’s task history, broken output preserved. Recheck46384739 confirms20 records with one literal quote reject; the invented prefix is removed with source evidence and unchanged labels. Primary015 check46384741 rejects one clause/outcome inconsistency for a bounded source-based repair. Primary016 is submitted46384815. No rejected data enters final analysis.

The optional private 800-ad Parquet exporter now links canonical keys, context hashes, validated-review file hash, strata, main1/pi3 weights and existing measures. Upstream pi12/nested weights stay null where unavailable; no parent-frame inference is introduced. Final aggregate analysis remains unrun.

## Primary001–019 accepted:380 contexts

Primary014 passed46384870 after exact quote recovery;015 passed46385544;016 passed46384815;017/018/019 passed46385911/46385912/46385916. All completed0 in1–4s. These receipts bring primary mechanical acceptance to380 of719 contexts. Primary021 is authored;020/022/023 continue. The original800-ad selection and153-context independent audit remain unchanged. Scoped failures and pre-repair files are retained privately.

Rootdecision14 narrows Q2 claims for type-specific experience waivers and adds a graduate-wording-only sensitivity from an existing field before final estimates. Figure code renders existing aggregate estimates only; ad-level labels and evidence remain private. No final analysis or semantic accuracy claim is made at this checkpoint.

## Primary001–021 accepted:420 contexts

Primary021 passed46386358 (2s);020 passed46387704 (2s) after five source-bound repairs. Primary022/023 validation46387706/46387708 rejected2/5 records, respectively; only these named records are being repaired. Full153-context independent audit remains sealed. A transient Sol capacity error interrupted023/024; the bounded023 retry completed without changing model, while024 resumes only saved-missing rows. Primary025/026 are assigned to fresh Sol/medium readers. Final comparisons remain pending.

Runtime preflight46386283 completed0 in5s with Python3.8.10, pyarrow11.0.0 and matplotlib3.5.2. It checked runtime/import/syntax readiness without research data, not production inference. Independent export/figure QA found missing explicit-graduate/private-entry columns, which are now included; upstream missing weights remain null.

The user explicitly authorized sanitized publication to main. Push5ef1a05 succeeded; no renewed Git permission is needed.

## Primary001–025 accepted:500 contexts

Primary022/023 repaired seven exact failed records and passed46388197/46388200 (2s/3s). Primary024 passed46387936 (6s). Primary025 saved all20 individually authored full-review records before its final capacity error; root recovered the transport/provenance sidecar without relabeling and cloud46388439 passed20/20 (5s). Both reading history and final-turn failure are disclosed. Primary026 job46388946 rejected5 records; bounded source repairs only. Primary027–029 continue;028 preserves one saved row by its previous reader and assigns only19 missing records to the next reader. Final analysis has not run.

## Primary001–030 accepted:600 contexts

Passing jobs026:46389467,027:46390425,028:46390798,029:46390601,030:46390602 all completed0 in1–2s. These certify frozen source/ID/schema/evidence consistency, not semantic accuracy. Primary031 is authored; validation46390603 rejected8 quotation/alternative-reference records, assigned to a fresh independent Sol/medium repairing reader. Primary032/033 proceed;034–036 remain unassigned.

A private root bundle now packages only the already selected maximum40 contexts with complete original text and both existing decisions. Selection, rubric and labels are unchanged; this reduces transport/retrieval work for actual root adjudication. No final estimates have been computed.

## Current checkpoint: primary001–035 accepted; primary036 exact repair pending

- Primary001–035 are authored and mechanically accepted across all700 contexts. Passing jobs031–035 are46391861,46391906,46391988,46392417, and46392423; shared-condition QA6cases passed on46391861 and independent QA passed. Acceptance certifies frozen source/ID/schema/evidence consistency, not semantic accuracy.
- All153 independent blind-audit contexts remain authored and mechanically accepted. The frozen sample remains800 ads/719 distinct contexts; the audit remains160 ads/153 distinct contexts. No sample or arm allocation changed.
- Primary036 has19 authored records. Cloud46392427 rejected exactly2 literal year-bound records; same-reader repair job46392568 is submitted. Its result is pending and no pass is claimed.
- Root prepare job46392632 was submitted after the final package with an afterok dependency. The first2CPU/8GB submission was rejected by the scheduler without a job ID; the resubmission uses the verified2CPU/4GB queue configuration. No result is claimed yet.
- Root adjudication capacity remains at most40; current root use is0/≤40. Final analysis and T1–T6 have not run. Git main authorization remains active; latest pushed checkpoint is351ed36.

## Full consolidation and bounded root-review preparation

- Full primary consolidation job46392632 accepted all719 frozen primary contexts; full audit consolidation accepted all153 independent audit contexts. These are validation/provenance receipts and do not constitute semantic accuracy certification.
- Root review documentation is prepared for at most40 selected cases:36 selected differences and4 agreements. The composite comparison covers144/153 contexts; its discordance is a bounded comparison result and must not be reported as a population error rate.
- Root validation job46393703 accepted39/40. One record (case29) has a quotation-location issue in qualification alternatives; the same root reader is repairing the provenance/record with no semantic label change. Final root receipt and final tables remain pending.

## Root40 complete and private archive checkpoint

- Root40 validation job46393877 completed0:0 in2 seconds. The bounded root review is complete:40 actual full reads, documented as36 selected differences and4 agreements. This remains a bounded comparison; composite144/153 discordance is not a population error rate.
- The authorized local private assignments, reviews, repair provenance, and root authoring outputs were archived remotely without deletion. Archive SHA-256 is `7885c50ab41957c2584422d8fe24aea23e92ab59216f4911232482deca936ae2`; remote path is `/work/home/lilysharp/private/formal800_20261012/archive_bounded_20261012/formal800_private_bounded_20261012.tar`.
- Final tables and final analysis remain pending separate results.

## Final finite release checkpoint

- Finalize46394029 completed0:0 in32s; figures46394097 completed0:0 in7s; baseline+summary46394098 completed0:0 in27s. Public T1–T6 tables, two figures, primary-baseline comparison, and primary-vs-final assets are present under `results/`, `primary_baseline/`, and `primary_vs_final/`.
- Root40 is complete:36 selected differences and4 agreements. Provenance counts are719 total primary contexts =566 unaudited primary +5 audited agreements +108 masked disagreements +40 root contexts. The composite144/153 discordance is not a population error rate.
- No active jobs remain. No new jobs, re-extraction, or global-corpus claim is authorized. Final state is a bounded finite800 release.

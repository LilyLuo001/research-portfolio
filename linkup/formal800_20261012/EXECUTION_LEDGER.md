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

## Planned artifact statuses

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

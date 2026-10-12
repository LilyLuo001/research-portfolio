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

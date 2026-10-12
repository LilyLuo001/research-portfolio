# Formal 800 review execution ledger — 2026-10-12

Status: preparation started under explicit user approval. No sample, semantic review, or scheduler job is complete until a public receipt names the artifact and status.

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

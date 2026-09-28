# Stage C release-v1 enrichment decision

## Scope and freeze

This release adds a separate, conservative enrichment layer over the frozen V6
payload. It does not change V6 education, experience, or no-experience
detection. The public API is `enrichment.enrich(payload)` and returns sparse
`experience_evidence`, sparse `technology_evidence`, and integrity `flags`.
Text is represented by half-open offsets into the V6 normalized text; the
result does not copy full text.

The semantic module is frozen at SHA-256
`cf0cf8fae3451d463430c14ebe6bf2a6dcc72b8239589ed2fbeb20ef0c4451c6`.
The 100,000-row pilot used lean writer SHA-256
`56b4c1daaff2a6015a64ebe91f3541fb65858c1a196d62998868b569ea8cf450`.
The final production writer is
`67c22e5db1d61f7a909235150a0254f9af9bd2ccd6f1958aa6d7a555e32b99d5`;
its post-pilot changes are limited to zero-row handling and audit retention.

## Interpretation

Experience duration and object fields are populated only for explicit local
syntax. Unresolved V6 experience candidates retain `object_unspecified` and an
unknown binding. AND, OR, includes, optionality, source context, applicant
candidate status, and requirement strength remain separate fields.

Technology mentions are candidates. Generic machine-learning, deep-learning,
neural-network, NLP, and computer-vision terms are `unspecified_ai`; a bare
`LLM` is ambiguous. Develop, implement, and use roles require a local action
before the technology. Only tight direct grammar is `explicit`; other nearby
relations are `candidate_local_relation`. Context and applicant-candidate
status remain separate from role and technology classification.

Parse failure, input evidence truncation, or V6 incomplete status sets
`enrichment_incomplete` and suppresses enrichment evidence. Education and
no-experience outputs remain measurement-audit candidates and are outside the
enrichment module. The lean writer retains them in a sparse `v6_audit` table
with offsets and frozen V6 flags but no copied evidence text. `ad_status`
retains `DESCRIPTION_EMPTY`; empty matched-USA descriptions stay in the
canonical denominator and are not removed by key-only preprocessing. The
targeted 32-item comparison is a bounded diagnostic, not a
prevalence or accuracy estimate, and cannot trigger semantic edits after the
freeze.

## Validation and pilot history

Eleven focused synthetic tests cover duration/object binding, coordinated
objects, type distinctions, bare-LLM ambiguity, company context, unresolved
experience, direct and candidate role binding, co-occurrence, truncation/error
suppression, and span offsets.

Pilot job `123196300` exposed an engineering defect in the first lean writer:
each row was written as its own Parquet row group. The generated partial reached
138,751,292 bytes after about 1 minute 54 seconds. The job was canceled at 2
minutes 9 seconds, before the 250 MB cap. The partial was retained at
`stage_c_release_v1/failed/kunshan_100k_job123196300`. The writer was changed
to buffer 512 rows per table before each Parquet write; the enrichment module
was not changed. A 20-row write/read smoke passed before the replacement pilot.

Replacement pilot metrics and receipt status are recorded separately in
`PILOT_REPORT.json` after the remote `COMPLETE.json` is available.

After the pilot, an actual 21-row compact writer smoke (including empty text,
education, explicit no-experience, and an education/experience alternative)
serialized and reread all retained fields successfully. A zero-input smoke
emitted all four empty Parquet tables and a complete receipt. These retention
checks did not rerun or revise semantic diagnostics.

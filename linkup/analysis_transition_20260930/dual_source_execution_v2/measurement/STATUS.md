# L2 measurement status — 2026-10-04

## Completed locally

- Versioned extraction schema and model/agent prompt are frozen at `v1.0.0` for this scaffold.
- Schema and consistency checks verify exact source spans and the representation of objects, durations, alternatives and states. They cannot establish semantic completeness or correct interpretation; the real diagnostic demonstrated this limitation.
- Development and evaluation preparation commands accept real local CSV, JSONL, or Parquet text, audit exact locators and readability, and write private packs outside `measurement/`.
- The development route can materialize the frozen D25 two-configuration 80 only from L1's exact 80-key manifest; it never redraws that subset.
- Offline prediction import, validation receipts, local text-length/token-proxy receipts, and a hard unavailable batch gate are implemented.
- The compact-label helper now accepts the authorized two-column blind pack directly, computes source hashes/offsets locally, and does not require reviewers to add a SHA column.

## Real-input status

The first repair attempts failed or were superseded. The accepted case-fixed run selected 40,300 formal rows across 69 cells (A=10,075; B=30,225), with zero cell-count mismatches and maximum B inverse-probability reconstruction error below `8e-10`. Independent QA also verified 40,300 unique formal keys, disjoint 200-record development/evaluation subsets, and the nested 80-record A40/B40 comparison subset.

The regional materializers recovered all 200 development texts (Kunshan 122, Wuzhen 78) using exact canonical locators. The private prepared pack contains 200 nonempty texts and the exact config80 manifest. Exact-text diagnostics found 185 distinct texts among 200 records and 76 among config80; the fixed development sample was not redrawn. Complete historical review text was unavailable, so cross-key historical same-text and heldout-400 contamination remain unverified.

The bounded Terra/medium versus Sol/medium diagnostic stopped after part 01 because core semantic failures were already material. Both final expanded files cover the same 20 unique record IDs and pass frozen structural/evidence validation 20/20, but first-pass exact-quote expansion passed only 12/20 for Terra and 17/20 for Sol. Terra's quote-repair step also changed semantic fields, which is recorded separately as a protocol deviation. Public aggregate results are in `results/DEVELOPMENT_COMPARISON_PART01_AGGREGATE.json`; row-level labels, text, and the eight-case adjudication queue remain private.

## Explicitly not completed

- The remaining 60 config-comparison records were intentionally left unread after the part-01 quality stop.
- GPT-6 completed four targeted full-source adjudications, including shared omissions; the other queue cases were not adjudicated. No original model label was overwritten. See `results/ROOT_DEVELOPMENT_DECISION.json`: both tested prompt/workflow configurations remain unaccepted for unattended production.
- No evaluation set was revealed.
- No separate batch API or paid external call occurred. Authorized conversation subagents received the first 20 development texts; production L3 has not started.

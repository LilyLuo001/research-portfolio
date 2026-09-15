# Final delivery locator

The final, hash-bound delivery for this task is `delivery_v4/`. Earlier
`delivery`, `delivery_v2`, and `delivery_v3` folders are retained as historical
intermediate construction attempts; do not use them for decisions.

- `delivery_v4/RETRIEVAL_SEED_STOCK_WAVE.csv` and
  `delivery_v4/RETRIEVAL_SEED_SECURITIES.csv` are the E007-only retrieval seed.
- `delivery_v4/ROSTER_MANIFEST.json` defines the source purpose and boundary.
- `delivery_v4/EARNINGS_METADATA_CENSUS.csv` and
  `delivery_v4/EXECUTION_RECEIPT.json` report only aggregate metadata results.
- `delivery_v4/NEW_CLOCK_MEMBERSHIP_GAPS.csv` records outstanding row-level
  new-clock evidence gaps.
- `DATA_REVIEW_DELTA.md` is the independent v2 execution review.

The protected row-level metadata remains only on SCC at the path recorded in
the execution receipt. The status is `METADATA_PROJECTED /
ECONOMIC_EVENT_RULE_PENDING`, not a scientific GO.

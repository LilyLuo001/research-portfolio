# Bounded coordinator verification

Executed `verify_checkpoint.py` locally on 2026-09-15. PASS: the 13 existing fixture assertions, two additional synthetic scenarios, saved code/config/manifest consistency across pilot and full receipts and gate, and four full-run aggregate hashes. Receipt arithmetic reconciles 99 candidates = 24 matched + 75 unmatched, with 45 candidate-by-other-wave pairs across four other waves. This is not an independent source-row re-extraction or a scientific referee review.

Two concrete code issues were repaired before the final pilot/full run: unmatched sentinels are reconciled separately from real pairs, and missing dates cannot match each other as empty strings. Missing adviser metadata is also kept unknown. Additional coordinator scenarios verified that an entirely unmatched input is preserved and that the same security in different focal waves is not collapsed.

No model-estimated effects, empirical power or clean/exclude inference was performed. Several receipt flags are descriptive assertions rather than independent tests; do not interpret their collective PASS as a scientific gate. The exact-time clarification in `CLOCK_BOUNDARY_CLARIFICATION.md` reads the unchanged proposed contract rather than introducing a new timing specification.

# Continuation checkpoint 02 — actual source recovery

Research remains **HOLD_DESIGN + HOLD_DATA**. This is a completed metadata-recovery test, not final population approval or a power result.

## Decisive result

Of the fixed 202 previously unrepresented stock-wave candidates, **99 have unique date-valid mappings in both existing SCC actuals families** and 103 do not have a unique recovery in either checked family. No core-only or rescue-only recovery was observed. The source families remain separate.

| Wave | High recovered / checked | Low recovered / checked |
|---|---:|---:|
| W002 | 33 / 59 | 36 / 73 |
| W016 (stress) | 7 / 24 | 9 / 29 |
| W025 | 3 / 6 | 11 / 11 |

Each family gives 1,246 wave-specific candidate release keys: 833 PRE, 318 POST and 95 transition. All 99 have a PRE key, but only 27 have a POST key. These are candidate-source metadata keys, not certified unique economic events or a final qualified sample.

The full QTR archive-window metadata row-key sets agree (160,612 keys in each source and in their intersection). This is a different denominator from the 202 candidates. Rescue is an overlapping archive version, not independent evidence to double-count.

Ten fixtures, a 20-candidate pilot, 20 actual source-row lineage checks and the full-run invariants passed. A failed pilot-receipt JSON serialization attempt was corrected and recorded; no full run launched before its corrected gate. Sources were column-projected without actual/EPS, forecast values, prices, returns or responses. Protected rows remained on SCC.

## Interpretation and next authorized operation

The old protected retrieval view omitted some records already present in the canonical SCC archive. Therefore the earlier one-high-candidate known-clean diagnostic cannot be treated as a complete-population upper bound. Recovery does not establish competing-conversion cleanliness, correct pre-announcement tiers, timezone/RTH, analyst support or final inclusion.

The user has authorized diagnostic execution. A versioned **CORE-only recovered-candidate sidecar** may now measure PRE/POST support, nominal source-clock support and observed analyst-ID coverage, preserving source/version identity. This is not a silent pool with the old view or automatic final-population adoption. The next sidecar is in progress; do not stop at another generic proposal or ask the PI to supply a programmatically recoverable roster. Scientific population/session/inference approval remains a separate issue.

Evidence: [results](artifacts/unrepresented_source_recovery_20260915/RESULTS.md), [execution receipt](artifacts/unrepresented_source_recovery_20260915/EXECUTION_RECEIPT.json), [artifact index](ARTIFACT_INDEX.json). [Previous checkpoint](../20260915_continuation_01/STATUS.md).

Requested execution: retained Sol/medium, backend telemetry NOT_OBSERVED. No new high-model review, purchase, live WRDS connection or POST response read.

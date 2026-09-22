# Native source field map

Date: 2026-09-22. Sources are Databento `mbp-1` DBN files from `XNAS.ITCH` and `ARCX.PILLAR`. Each dataset is a direct, venue-specific feed; neither is SIP NBBO and the two venues are never pooled into a synthetic NBBO.

## Fields and implemented use

| Field | Documented meaning | Pilot use |
| --- | --- | --- |
| `ts_event` | Publisher/matching-engine event timestamp, integer nanoseconds since Unix epoch; publisher value is not adjusted by Databento | Primary axis. Kept as `int64` nanoseconds. |
| `ts_recv` | Databento capture-server receive timestamp, integer nanoseconds; not a SIP timestamp | Independent timing sensitivity. Quoting it as “SIP time” is prohibited. |
| `instrument_id` | Numeric instrument identifier, only guaranteed unique within a day | Resolved through the DBN file’s dated mappings; not joined across dates as a permanent ID. |
| `publisher_id` | Dataset/venue publisher | Retained implicitly by one-dataset-per-file requests; no cross-venue aggregation. |
| `action` | `A` add, `C` cancel, `M` modify, `R` clear, `T` aggressing trade, `F` resting fill | Economic trades are counted from `T` only. `F` is excluded to avoid double-counting an execution normalized into trade/fill messages. Adds/cancels/modifies update the venue BBO state. |
| `side` | For `T`, `B` is buyer aggressor, `A` is seller aggressor, `N` is unspecified | Native `B/A` is primary (`A` maps to signed sell). Only `N` falls back to a strict prior-message midpoint rule. At-mid, no-prior-quote and ambiguous cases remain unknown. |
| `price`, `size` | Fixed-precision trade/order price and quantity | Used for trade response and aggregate size diagnostics. No row-level values leave SCC. |
| `bid_px_00`, `ask_px_00`, sizes | Venue top-of-book after each MBP-1 message | Valid positive, non-crossed sides form quote state. A trade is classified/responded against the last valid *prior* message on the selected axis, never its own post-message state. |
| `sequence` | Venue-assigned message sequence number | Tie-breaker after timestamp, followed by original file order. Same timestamp is not deduplicated. |
| `flags` | Bit field: `128` last record in event, `8` bad receive timestamp, `4` maybe-bad book, `2` publisher-specific | Bit-tested, not equality-tested. Across 12,298,752 records, bad-receive and maybe-bad-book flags are both zero. Publisher-specific flags are reported but not reinterpreted as sale conditions. |

Databento documentation: [MBP-1 schema](https://databento.com/docs/schemas-and-data-formats/mbp-1), [timestamps/actions/sides/flags](https://databento.com/docs/standards-and-conventions/common-fields-enums-types), [XNAS.ITCH normalization](https://databento.com/docs/venues-and-datasets/xnas-itch), and [venue/dataset descriptions](https://databento.com/docs/venues-and-datasets).

## Actual source diagnostics

- 12,298,752 MBP-1 records; 513,606 `T` records; 70 `F` records. The 70 fills are not counted again as trades. Fixed analysis windows contain 482,020 trades; 31,586 trades in the request lead/tail are support-only.
- Across purchased files, native aggressor side is present for 438,478 trades (85.37%). A strict prior-midpoint fallback classifies another 54,347 (10.58%); 20,781 (4.05%) remain unknown. In the fixed analysis windows the counts are 411,837 (85.44%), 50,457 (10.47%) and 19,726 (4.09%). These totals are invariant across event/receive sorting, though fallback signs can differ by axis.
- `XNAS.ITCH` native trade sides: 116,397 `B`, 115,043 `A`, 45,387 `N`. `ARCX.PILLAR`: 97,451 `B`, 109,587 `A`, 29,741 `N`.
- Trade flags are limited to integer values 0, 128 and 130 in this sample. There are no `F_BAD_TS_RECV` or `F_MAYBE_BAD_BOOK` records. Value 130 combines `F_LAST` and a publisher-specific bit; this pilot does not pretend that bit is a TAQ sale-condition field.
- The normalized MBP-1 schema does not expose TAQ-style correction/cancel sale-condition columns. XNAS documentation states that non-displayed/cross trades may have unspecified side; the pilot preserves that uncertainty rather than inferring an auction flag from price behavior.
- All 36 instrument-file partitions have zero invalid/crossed/zero BBO messages under the implemented validity rule. Live unchanged quotes are carried forward; this is valid state, not automatically “stale.”

Detailed aggregate provenance is in `SOURCE_SEMANTICS_COUNTS.csv`; licensed row-level DBNs remain only in `/scratch/qluo/native_tick_pilot_20260922/` on SCC.

# P1 event and exposure count audit — current

**Status date:** 2026-09-03

**Authority:** `p1/universe_v2/output/event_master_final_reconciled.csv`,
`p1/exposure/universe_census.json`

This file supersedes the old 131→172 register memo. The old
`p1/events_merged.csv` (172 rows / 96 legacy waves) and
`p1/conv_exposure_free.parquet` (6,377 cells / 2,241 CUSIPs) remain only as
reconciliation baselines. They are not the current research universe or
treatment input.

## Current measured census

| Stage | Events | Dates/waves | Status |
|---|---:|---:|---|
| Structural register | 247 | — | includes future/cancelled/unresolved |
| Completed conversions | 156 | — | 74 tier A + 82 tier B |
| Verified exact-day | 74 | 49 dates | primary timing-eligible universe |
| N-PORT Gate0 PASS | 71 | 47 waves | exact-series PRE and earliest eligible POST |
| Pending first POST | 3 | 2 waves | recent 2026 events; valid PRE retained |
| Exposure with positive, denominator-ready U.S. common stock | 71-event construction universe | 30 waves | 17 PASS waves have no eligible mapped U.S. common-stock cell |

The completed-event date precision census is 74 verified exact day, 14
proposed exact day only, 57 month only, 9 bounded window, and 2 year only.

## Current treatment census

- 26,399 strictly-PRE N-PORT positions.
- 11,962 unique reported securities before mapping.
- 15,425 position rows classified as candidate common equity.
- 14,747 exact-matched CRSP position rows covering 96.49% of candidate
  common-equity position value.
- 8,801 positive, ownership-ready stock×wave cells.
- 3,440 unique positive-exposure PERMNOs.
- 573 unique PERMNOs reach ExposureOwnership ≥0.5%; 27 reach ≥1%.
- 2,380 positive-exposure stocks appear in more than one wave; 10 of the 573
  ≥0.5% stocks appear in more than one wave.
- Dimensional-only: 559 unique ≥0.5% PERMNOs. Excluding Dimensional: 21.

## Reconciliation and decision consequence

The old “389 treated stocks” was generated from the legacy 131-event ConvExp
artifact and is not authoritative. The rebuilt ≥0.5% count is 573. However,
the frozen K2 condition is based on the exclude-Dimensional arm: the current
conditional count of 21 is below the preregistered power floor of 33. No
threshold was changed and no outcome coefficient was inspected. However, K2 is
suspended: the Fed note's four empirical events all match P1, but its separate
125-fund end-2024 aggregate is not published row by row and remains open against
P1's 95 through-2024 completions. See
`p1/universe_v2/output/event_universe_reconciliation_report.md`.

Machine-readable detail and cause classifications are in:

- `p1/exposure/universe_census.csv`
- `p1/exposure/universe_discrepancy_report.csv`
- `p1/exposure/nport_pre_post_coverage_by_wave.csv`
- `p1/exposure/exposure_construction_report.md`

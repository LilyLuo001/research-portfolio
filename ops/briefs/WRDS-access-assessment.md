# WRDS access assessment — P1-T2

**Status: BU WRDS access is gone.** CRSP (`crsp.holdings`, `crsp.portnomap`,
`crsp.stocknames`, `crsp.msf` shrout) and TAQ are not reachable from this seat.
The original T2 brief (Project_1.md §101-113) assumed WRDS credentials injected
via env; that assumption no longer holds.

## Decision: free EDGAR path, run in parallel to the frozen contract

ConvExp is a **holdings ratio**, not a price series, so it can be reconstructed
entirely from free public filings with equal rigor (meta-rule 1 is *satisfied*,
not diluted — every number keeps an EDGAR/OpenFIGI locator):

| WRDS piece | free substitute |
|---|---|
| `crsp.holdings` (fund holdings) | EDGAR **NPORT-P** `invstOrSec` (CUSIP, ticker, shares) |
| CUSIP → identity | N-PORT `<identifiers><ticker>`, else **OpenFIGI** `/v3/mapping` |
| ticker → issuer | SEC **company_tickers.json** (ticker → CIK) |
| `shrout` (shares outstanding) | SEC **XBRL** `dei:EntityCommonStockSharesOutstanding` |
| `permno` key | deferred — CUSIP↔ticker↔CIK crosswalk merges to CRSP later |

N-PORT is already named as a T2 source in Project_1.md §108, so this is within
the original spec, not a workaround.

## What is NOT reproduced without CRSP/TAQ (downstream flags)

- `permno` — left blank; the crosswalk recovers it if CRSP access returns.
- `pre_etf_ownership` here = the **converting funds'** ownership only (== conv_exp).
  Total mutual-fund ownership would need the full CRSP MF universe; flagged.
- T4 (Saglam-Tuzun replication) and any TAQ-based T-tasks still need a price/TAQ
  source; out of scope for this step.

## Contract discipline

Frozen `ops/contracts/conv_exposure.yaml` is **untouched**. The free path emits
`conv_exposure_free.parquet` against the new parallel contract
`ops/contracts/conv_exposure_free.yaml`, which reproduces every frozen column
1:1 (same names) plus additive crosswalk/provenance columns. No frozen column is
renamed (CLAUDE.md rule 3).

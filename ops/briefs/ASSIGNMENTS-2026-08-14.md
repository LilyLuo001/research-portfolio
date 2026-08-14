# Seat assignments — 2026-08-14 (owner-issued after the W1 design audit)

Context: the 2026-08-14 audit (`dax/memo/design_audit_2026-08-14.md`, pending)
found that the W1 stacking protocol yields **2 estimable events** from its own
4 eligible rows, and **1** if the registry is completed as planned. W5/W3 must
not be started until the window rule is resolved. These assignments are chosen
to be **zero-waste under any resolution of that rule**.

## Collision carve-out — read before claiming DAX-W2-data

`DAX-W2-data` is being executed as **two non-overlapping halves** so two
workers can run it concurrently without touching the same files. The
`dax_built_backbone` contract requires four files; ownership is split:

| File | Owner | Status |
|---|---|---|
| `dax/data_built/price_histories.csv` | **price-panel worker** (in flight) | claimed 2026-08-14 |
| `dax/data_built/onet_timeshares.parquet` | **seat A** | unclaimed |
| `dax/data_built/oews_wages.parquet` | **seat A** | unclaimed |
| `dax/data_built/cps_extract.parquet` | **seat A** | unclaimed |

Seat A: do **not** write `price_histories.csv`, do not edit anything under
`dax/w2/prices/`, and do not modify `ops/contracts/price_histories.yaml`.
The price worker will not touch the other three files or the crosswalk code.
`DAX-W2-data` is marked complete only when **both** halves pass the backbone
contract.

## Seat A (DAX-prime, `dax/`) → `DAX-W2-data`, non-price half

Brief: `ops/briefs/opus/OPUS-DAX-W2-data-nonprice.md`.

Deliverables, all pre-period only (the outcome seal is closed and stays closed):
1. O*NET 2021 vintage task/IWA time-shares → `onet_timeshares.parquet`.
2. OEWS 2021 occupation wages → `oews_wages.parquet` (2019 baseline as the
   registered robustness vintage, not a replacement).
3. IPUMS-CPS pre-event extract → `cps_extract.parquet`. Extract 6 is already
   pulled and checksum-recorded in
   `dax/memo/power_calcs/ipums_preperiod_extract_receipt.json` — **reuse it,
   do not re-pull**, and verify the SHA256s match before building.
4. Employment-weighted many-to-many CPS↔O*NET-SOC crosswalk, emitting the
   Decision-12 dispersion diagnostics (within-code dose SD, max mapping
   weight) as first-class columns, not as a report.
5. Frozen Felten / Eloundou / Webb static-score ensemble for the Decision-8
   convergent-validity check.

Every file gets a lineage JSON. Every external download gets a locator
(agency, table ID, vintage, retrieval date, checksum). No figure from memory.

Why this is safe to do now: none of these five items depends on the window
rule, the event count, or the price panel. They are required under every
candidate resolution.

## Seat B (E2-prime, `e2/`) → `E2-T4a-design`

READY, unblocked (`E2-T1-facts` complete). No brief exists yet — write one
into `ops/briefs/` as the first act of the session, per the working protocol,
then execute. Touch only `e2/`.

## Seat C (P1-prime, `p1/`, `refraction/`) → L1 dispatch + gate prep

No L2 P1 block is READY. Do the overnight-batch work instead:
- `make l1` (dry run) → `make l1-live` for the ready batches: `P1-T1-events`,
  `P1-T13-ant`, `P1-T0-monitor`, `REFR-R0-collide`, `REFR-R1a-verify`.
- Reap the two stale leases first: `DAX-W1-memo` (expired 2026-08-06) and
  `P1-T1-events` (expired 2026-07-16). `make reap`.
- Close `DAX-W0.5-legwork`: `ops/decisions.md` §3 records it superseded by the
  owner-run inline legwork, but the runner still advertises it READY and will
  re-spend on it. Close it explicitly in an operations-state commit.

## Owner / PI items (not delegable)

1. **Merge the stranded W1 work.** `7a6a401` and `5d26fe2` sit on
   `task/DAX-W1-memo` above the PR #35 merge point and never reached `main`.
   They contain the cross-vendor red team, its remediation, the memo revision,
   the updated PDF, and the IPUMS pull. Until merged, the PDF on `main` is the
   pre-red-team draft — do not review that one.
2. **Rotate the GitHub PAT.** Flagged in `progress_audit_2026-08-06.md` defect
   3, and a token was subsequently pasted into a chat session.
3. **Resolve the window rule (D1) and the power bar (D3).** Both are
   `[PI-DECISION]` items; no agent may pick them. A quantified options pack is
   the next DAX task after the price panel.

## Standing rule reaffirmed

Do not start `DAX-W3-mapA` or any W5 work until D1 is signed. Mapping and
index construction built against the current window rule would be rework.

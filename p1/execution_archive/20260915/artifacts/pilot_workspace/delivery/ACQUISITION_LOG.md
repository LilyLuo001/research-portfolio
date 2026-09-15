# Acquisition execution log

Execution date: 2026-09-14 (Asia/Shanghai). Requested routing/effort was
Terra/Medium; actual routing telemetry is `NOT_OBSERVED`.

## Completed offline controls

- All 18 entries in `manifest_hashes.json` were recomputed and matched.
- `delivery/run_fixed_order.py prepare` validated 489 fixed source-manifest rows
  that canonicalize to 375 distinct physical requests:
  220 full-core, 115 reduced-core, 16 validation, and 138 optional-ETF
  intervals. Every interval had exclusive ordered UTC bounds and round-tripped
  to its recorded `America/New_York` date and clock.
- Every event-map entry resolves to its named containing physical request:
  full core 256, reduced core 128, extra ETF 192.
- Read-only `git show` at pinned commit
  `cb36417304b282cda5e38ede13d1af872ad9f346` found all eight exact
  ticker/PERMNO pairs in their named W002/W016 crosswalk memberships. The
  committed E007 file hash was
  `905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320`,
  matching the manifest.

## Live-execution result

The owner supplied a current balance of USD 125 and expressly authorized this
fixed order subject to the USD 100 planning cap and USD 125 hard ceiling. The
official SDK returned complete quotes for all 375 canonical alternatives. The
predefined budget rule selected 374 canonical requests: full core32, both
fixed validation bundles, and the optional ETF bundle. Exact quoted/reserved
gross usage was USD 1.578307747849, leaving USD 123.421692252151 relative to
the hard ceiling. Cash top-up, subscription, agreement acceptance, SCC access,
and any expansion of the order were not attempted.

All 374 selected requests completed once through sequential
`timeseries.get_range` calls and were stored as native compressed DBN: 172
PRE-only files, 194 POST-only files, and 8 shared files with PRE-authorized
subwindows and POST content. The final manifest has a nonempty byte count and
SHA-256 for every file. POST-only files received hash/byte checks only. For the
8 mixed files, the QA reader accessed quote fields only for mapped PRE windows;
POST quote fields were not accessed or returned. The credential was held only
in the no-echo process environment and was unset when execution finished.

Free `metadata.get_dataset_condition` results covered 96 requested
dataset-dates: 95 `available` and XNAS.ITCH on 2021-10-26 `degraded`. The
degraded date remains an explicit quality exception rather than being treated
as zero or ordinary coverage. The owner supplied the pre-run credit balance;
the post-run vendor billing receipt could not be independently read, so actual
billed credits remain pending reconciliation. Cash spend remains USD 0 under
the owner's credit-only authorization unless the vendor receipt shows
otherwise.

## Runner hardening

The runner now canonicalizes all four source manifests before any live work
(375 unique physical requests), so cost/symbology checks occur once per exact
dataset/schema/symbol/bounds tuple. It writes a hashed quote receipt and a
budget-gate-compatible input with `Decimal` bundle totals; a bundle becomes
unavailable if any constituent quote fails. Local SDK 0.86.0 signatures were
inspected without authentication. If every explicit guard later passes, the
only charged method is sequential `timeseries.get_range` with native DBN
output, pre-submission reservation accounting, no retry after an uncertain
result, and POST_FOCAL files isolated under `sealed_post_focal/`.

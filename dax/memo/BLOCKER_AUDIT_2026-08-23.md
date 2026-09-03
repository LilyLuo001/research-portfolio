# Blocker audit — W1, W2, W3, and who can clear each

**Date:** 2026-08-23. **Status:** audit, signs nothing.

Asked to clear every block before budget starts. This records what was
cleared, what is now one signature away, and what nobody in this seat can
clear. It also corrects a claim I made earlier today.

## Correction: the power benchmark is not unresolved

The `DAX Gate Map` review stated the power benchmark was `UNRESOLVED` and that
Gate 1 could not pass while it was null. **That is wrong.**
`dax/memo/power_calcs/power_standard.json` records
`version_status: RESOLVED`, `locator_status: VERIFIED`, and
`version_chosen: August 26 2025 authored version, 0.13`, decided by a
prospective PI commit. The source of my error was
`benchmark_source_audit_2026-08-19.md`, which reported `UNRESOLVED` and has
since been superseded. The audit was correct on its date; I read it as current.

What *is* still null in that file is different and smaller:
`status: PLACEHOLDER_REQUIRES_REAL_CPS`, `frozen_at_utc`, `provenance`, and
both MDE ceilings. The benchmark is chosen; the standard has never been frozen
against data.

## The dependency nobody had drawn

`freeze_power_standard.py` takes `--extract` and needs the columns
`month, age, <weight>, employed, hours_unconditional`. So:

    W2 CPS extract  ->  freeze power standard  ->  W1 Gate 1 power item

W1's power block is **downstream of W2**, not independent of it. That was not
visible in any brief and changes what "clear W1 first" means.

Better still: IPUMS extract 6 is already pulled and checksummed, and its 16
samples run `cps2021_11s` through `cps2023_02s` — **exactly** the standard's
frozen window of 2021-11 to 2023-02. The input exists. Nothing needs buying.

## Cleared in this pass

- `dax/w2/build_cps_preevent.py` builds the pre-event panel from extract 6 in
  the shape `freeze_power_standard.py` requires. It verifies the file against
  the pinned SHA-256 and refuses an unpinned one; it refuses to guess the
  `EMPSTAT` and `UHRSWORKT` recodes, reports every observed code, and records
  which codes were treated as not-employed. Five tests.
- **Scope guard.** This writes `cps_preevent_power_panel.parquet`, *not*
  `cps_extract.parquet`. The W2 brief defines the latter as running to the
  latest frozen month for the analysis panel; extract 6 stops at 2023-02.
  Writing one file for both would silently truncate W5's sample.

## One signature away, costing nothing

| Block | Stage | What it needs |
|---|---|---|
| v3 PI decision forms 1-5 | W3 | PI signature; gates all benchmark construction |
| Capture/scoring split amendment | W4 | PI signature; otherwise duration blocks capture even when funded |
| Capture priority rule | W4 | PI signature before any spend |
| Non-evaluable bound repair | W1/W3 | adopt the kappa dose path into whichever primary is signed |
| W3 reconciliation | W3 | PI counter-signature on the delegated decision |

## Still blocked, and not by a signature

- **`cps_extract.parquet` (analysis panel)** needs a *new* IPUMS extract
  running past 2023-02. Free, but a real pull with its own receipt.
- **`oews_wages.parquet`** needs OEWS 2021. Public download; not present here.
- **`onet_timeshares.parquet`** needs the O*NET 26.1 zip, which is on the SCC
  and already pinned.
- **Fresh red-team** on the post-D1 design. Cents, but needs vendor keys —
  which must be rotated first, having been exposed in conversation.
- **PI line-by-line review** of the rendered memo. Owner only.

## Why the three remaining builders were not written blind

The DWA coverage script took four rounds to get right, and every fault was the
same shape: inferring a column or table instead of requiring it to be named
and reconciling against something pinned. Three more builders written against
data I cannot see would repeat it. The CPS builder above was written because
its output columns are *exactly specified* by
`freeze_power_standard.py` — a target that cannot be guessed wrong. The other
three need an input inventory first.

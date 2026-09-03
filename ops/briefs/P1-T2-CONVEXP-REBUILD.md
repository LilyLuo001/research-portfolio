# P1-T2 — paused Exposure^pre construction brief

**Status:** first run executed 2026-09-03; further work paused pending the
Fed/source event-universe gate

**Design authority:** `docs/基金转换实验_博士研究计划.md`

**Current status:** `p1/STATUS-2026-09-03.md`

This brief supersedes the legacy 172-event ConvExp rebuild instructions. Do
not rebuild from `p1/events_merged.csv`, classify PRE/POST with filing dates,
or treat the old 389-stock result as current.

## Frozen inputs

- `p1/universe_v2/output/event_master_final_reconciled.csv`
- `p1/t2_free/nport_gate0_event_level.csv`
- exact-series N-PORT cache described by the Gate0 lineage
- SCC WRDS mirror documented in the owner's
  `P1_Refraction_WRDS_Data_Usage_Manual.md`

The existing run used exactly 71 Gate0 PASS events. Treat that set as a
provisional verified subset, not a final global universe. Keep the three
missing-first-POST events
in `exposure_pending_missing_post.csv`. Preserve event rows, waves,
many-to-one relationships, adviser/sponsor proxies, Dimensional flags, and the
two long-handoff flags.

## Construction rules

1. Select the latest filing-internal N-PORT `repPdDate` strictly before the
   verified effective date for the exact predecessor series. Reverify the
   series inside the filing. Never read POST holdings into treatment.
2. Map candidate common-equity positions through date-valid CRSP stock names:
   exact CUSIP9 first, labelled CUSIP8 fallback second. Never force a fuzzy
   name match. Preserve ambiguous, unmatched, non-U.S./non-CRSP, and
   non-common-equity statuses.
3. Apply the frozen formula per fund-position before aggregation:
   `AdjustedShares = RawShares × CFACSHR`. Align legacy `cfacshr` or CIZ
   `dlycumfacshr` to the N-PORT report/as-of date, never the SEC filing date.
4. Use CRSP `shrout × 1,000` from the latest trading day strictly before the
   wave effective date. Use that same date for `abs(price) × shares` market
   capitalization. Do not carry a post-event or stale denominator backward.
5. Save raw adjusted shares, value, fund portfolio weight, ownership
   normalization, and market-cap normalization. `exposure_ownership` is the
   recommended primary measure, but all alternatives remain in the artifact.
6. Save all-sponsor, Dimensional-only, ex-Dimensional, and LOSO position inputs.
   Adviser is only a proxy until the economic-sponsor crosswalk is signed.
7. Audit no POST holdings, no post-event denominators, no future sponsor data,
   and no future wave data. Do not winsorize extreme positions automatically.
8. Stop before outcomes and headline regressions.

## Rerun

Local SEC extraction:

```bash
python p1/exposure/build_nport_pre_holdings.py
```

SCC WRDS construction (paths may be passed explicitly):

```bash
module load python3/3.12.4
python p1/exposure/build_exposure_from_wrds.py \
  --archive /projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902
```

The builder writes the required census, PRE/POST wave coverage, crosswalk,
match and corporate-action audits, exposure matrices, LOSO inputs,
concentration/extreme-position diagnostics, discrepancy report, and lineage.

## Current first-run facts

- 247 structural members; 156 completed conversions.
- 74 verified exact-day events / 49 dates.
- 71 Gate0 PASS events / 47 waves; 3 pending events / 2 waves.
- 26,399 PRE N-PORT positions; 11,962 unique reported securities.
- 14,747 exact-matched common-equity positions; 96.49% of candidate
  common-equity value matched.
- 8,801 positive ownership-ready stock×wave cells in 30 waves.
- 3,440 positive-exposure PERMNOs; 573 at ≥0.5%; 27 at ≥1%.
- Excluding Dimensional leaves 21 unique ≥0.5% PERMNOs in the provisional run;
  K2 is suspended and this is not a final stopping-rule decision.
- All 71 leakage-audit rows PASS. No outcome coefficient was inspected.

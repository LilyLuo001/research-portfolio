# P1 data handoff — 2026-09-13

**Domain status: HOLD_DATA.** This is an inventory/coverage finding only, not an overall P1 verdict. I did not open, compute, plot, or summarize any post-conversion earnings-response outcome or uncertain-result file.

## What is measured now

`MEASURED_NOW` against read-only snapshot `cb36417304b282cda5e38ede13d1af872ad9f346`: the frozen SEC/N-PORT/CRSP exposure build has 74 event rows in 49 waves, 71 Gate0-PASS events in 47 waves, 71 unique predecessor series, 70 successor series, and 34 raw adviser labels (`p1/t2_free/nport_gate0_event_level.csv`; `p1/exposure/nport_pre_post_coverage_by_wave.csv`). Event metadata include predecessor/successor series and CIKs, effective date, report/as-of date, accession, filing date, and pre/post holdings counts. The 71-event leakage audit passes: all input holdings are strictly PRE, no post holdings or post-event denominators were used, and its future-sponsor/wave flags are false (`p1/exposure/exposure_leakage_audit.csv`). This does not establish public availability before the earliest announcement/anticipation clock: the cell artifacts retain report and filing dates but no announcement-to-public-availability eligibility audit.

`MEASURED_NOW`: recomputation from `exposure_stock_wave_*.csv`, restricted to `primary_ready` and positive `exposure_ownership`, gives all sponsors 8,801 stock-wave cells / 3,440 PERMNOs / 30 waves; Dimensional-only 3,503 / 2,548 / 2; excluding Dimensional 5,638 / 2,979 / 29. At ownership exposure >=0.5%, the arms are respectively 583 cells / 573 stocks / 4 waves, 561 / 559 / 2, and 21 / 21 / 2. Repeated PERMNOs are material (2,380 all-sponsor stocks repeat over waves; maximum 16); rows are not independent fund or earnings observations. The 25 adviser strings are an **unsigned adviser proxy**, not an economic-sponsor crosswalk; final sponsor clustering/LOSO is blocked.

`MEASURED_NOW`: schema separates `raw_reported_shares`, split-adjusted shares, ownership exposure, value/market-cap exposure, fund portfolio weight, denominator, as-of-date range, effective date, and accession. Lineage gives formula `adjusted_shares = raw_reported_shares * share_factor` and date-valid CRSP matching (`p1/exposure/exposure_construction_report.md`, `exposure_construction_lineage.json`). All positive-ready cells have nonblank PERMNO/wave/adviser, complete factors, no effective dates after 2026-09-13, and PRE report dates before effective dates. Across all 8,826 aggregated rows, 25 lack a positive denominator and are not primary-ready. Value coverage is 67.23% of all N-PORT value and 96.49% of candidate-common-equity value; Dimensional is 64.15% of exact-matched PRE value. These are coverage facts, not portfolio-continuity or strategy/manager/fee/clientele evidence; that continuity audit remains unexecuted.

## Missing design inputs

`NOT_AVAILABLE`: no joined earnings-release calendar, announcement-time/session classification, eligible-forecast/actual/SUE panel, quote midpoint/trade panel, or horizon-specific response mask is available for this review. `p1/wrds/SCC-MIRROR.md` documents I/B/E/S files but unresolved `ANNTIMS` timezone semantics, no full intraday event-window data, and no 2026 CRSP DSF; `p1/NON_WRDS_BLOCKERS.md` names IBES timing/timezone and genuine intraday quotes as load-bearing. Therefore support by earnings date/session/horizon, control reuse after earnings matching, pre-treatment/untreated residual calibration, and empirical power are `NOT_ESTIMABLE`; no daily/macro substitute is valid.

Smallest request that changes this branch: an authorized, row-filtered extract only for the 8,801 frozen `(permno,wave_id,effective_date)` cells plus a preregistered control risk set, covering each eligible issuer's earnings events from 2019-01-01 through 2026-08-31: point-in-time identifier link; IBES actual EPS/date/**timestamp with timezone** and one latest eligible forecast per analyst (forecast timestamp, fiscal period, estimate, share/currency basis); and NBBO/TBBO bid/ask timestamps plus SPY for RTH windows from event time to +1 trading-day close. Include a market-session/half-day calendar and CRSP `retx` for [-250,-21]. This permits the blocked join, session/horizon mask, SUE construction, and residualized design/power calculation without requesting the whole market or opening sealed outcome values.

## Exact reproduction commands

```sh
git -C /Users/lilyluo/research-portfolio-p1-advanced-readonly rev-parse HEAD
python3 - <<'PY'
import csv
for n in ['exposure_stock_wave_all.csv','exposure_stock_wave_dimensional_only.csv','exposure_stock_wave_ex_dimensional.csv']:
 r=list(csv.DictReader(open('/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/'+n)))
 v=[x for x in r if x['primary_ready']=='True' and float(x['exposure_ownership'])>0]
 print(n,len(v),len({x['permno'] for x in v}),len({x['wave_id'] for x in v}))
PY
```


# P1 — WRDS table request list

_Seat C, 2026-08-19. Send this to the seller. ¥20/table._

**Sample anchors** (from `p1/events_merged.csv`, computed not assumed):

| | |
|---|---|
| Announcement dates | 2020-05-01 → 2026-06-30 |
| Effective dates | 2021-03-26 → 2026-11-20 |
| Event-study `t=0` | **announcement date** (§6 threat T2) |
| Market-model estimation window | −252 to −21 trading days before `t=0` |
| Post-event window | +120 trading days |

⚠️ **Date ranges below are anchored on the earliest ANNOUNCEMENT (2020-05-01)
minus the estimation window, not on the earliest effective date.**
`pull_scope.json` currently anchors on the effective date and therefore
under-pulls daily data by ~10 months — see "Known scope bug" at the end.

---

## Tier 1 — MUST HAVE · 11 tables · ¥220

| # | Library.Table | Freq | Date range needed | Key fields | Purpose |
|---|---|---|---|---|---|
| 1 | `crsp.stocknames` | reference | **full history** (no date filter) | `permno`, `ncusip`, `cusip`, `ticker`, `namedt`, `nameendt` | CUSIP↔PERMNO. Fills `permno`, blank on all 6,377 rows today. Nothing joins without it. |
| 2 | `crsp.dsf` | **daily** | **2019-01-01 → 2026-08-31** | `permno`, `date`, `ret`, `prc`, `vol`, `shrout`, `openprc` | CAR paths, Amihud, 1−R², variance ratio, price delay. The big one. |
| 3 | `crsp.dsi` | **daily** | **2019-01-01 → 2026-08-31** | `date`, `vwretd`, `ewretd` | Market-model benchmark. No abnormal returns without it. |
| 4 | `crsp.dsedelist` | daily events | **2019-01-01 → 2026-08-31** | `permno`, `dlstdt`, `dlret`, `dlstcd` | Delisting return inside the 120-day CAR window. Omitting it silently biases spine two. |
| 5 | `crsp.msf` | **monthly** | **2018-01-01 → 2026-08-31** | `permno`, `date`, `prc`, `ret`, `shrout` | ConvExp denominator, market-cap deciles, monthly reversal strategy. |
| 6 | `comp.fundq` | **quarterly** | **2018-01-01 → 2026-08-31** | `gvkey`, `datadate`, `rdq`, `epspxq`, `niq`, `atq`, `cshoq`, `prccq` | Earnings decomposition, FERC, SUE time-series branch. 2018 start = 8-quarter lookback for the earliest event. |
| 7 | `comp.funda` | **annual** | **2018-01-01 → 2026-08-31** | `gvkey`, `datadate`, `ceq`, `csho`, `prcc_f`, `at` | **Control group.** §107 matches on size × book-to-market × industry × ETF ownership × Amihud. Book equity is annual. |
| 8 | `crsp.ccmxpf_lnkhdr` | reference | **full history** | `gvkey`, `lpermno`, `linktype`, `linkprim`, `linkdt`, `linkenddt` | Compustat (gvkey) ↔ CRSP (permno). Items 6–7 are unusable without it. |
| 9 | `ibes.statsum_epsus` | **monthly snapshots** | **2018-01-01 → 2026-08-31** | `ticker`, `cusip`, `statpers`, `fpedats`, `fpi`, `meanest`, `medest`, `stdev`, `numest` | SUE-IBES (decided primary), analyst dispersion, coverage count. |
| 10 | `ibes.actu_epsus` | per announcement | **2018-01-01 → 2026-08-31** | `ticker`, `cusip`, `pends`, `anndats`, `value` | Reported actual EPS **and the announcement date** — `t=0` for every event in spines one and two. |
| 11 | `ibes.idsum` | reference | **full history** | `ticker`, `cusip`, `cname`, `sdates` | IBES ticker ↔ historical CUSIP. Point-in-time CUSIP on a statsum row is not the mapping history. |

## Tier 2a — holdings bundle · 3 tables · ¥60 · buy all three or none

| # | Library.Table | Freq | Date range needed | Key fields | Purpose |
|---|---|---|---|---|---|
| 12 | `crsp.holdings` | quarterly reports | **2020-01-01 → 2026-08-31** | `crsp_fundno`, `report_dt`, `permno`, `nbr_shares` | CRSP-identifier twin of the free-path ConvExp |
| 13 | `crsp.fund_hdr` *or* `crsp.fund_names` | reference | **full history** | `crsp_fundno`, `fund_name`, `ticker` | Fund identity — `holdings` cannot be mapped to a fund without it |
| 14 | `crsp.portnomap` | reference | **full history** | `crsp_portno`, `crsp_fundno` | Portfolio no. ↔ fund no. crosswalk |

## Tier 2b — monthly delisting · 1 table · ¥20 · independent

| # | Library.Table | Freq | Date range needed | Key fields | Purpose |
|---|---|---|---|---|---|
| 15 | `crsp.msedelist` | monthly events | **2018-01-01 → 2026-08-31** | `permno`, `dlstdt`, `dlret`, `dlstcd` | Delisting on the monthly file. Only for the Jegadeesh monthly reversal strategy (§7, 2-7). |

**Total: 15 tables = ¥300.**

---

## DO NOT BUY

| Item | Why |
|---|---|
| Fama-French factors | **Free** from Ken French's data library. The market model uses `vwretd` from `crsp.dsi`. |
| TAQ / WRDS IID | Seller does not have it. Replaced by Databento BBO. |
| `ibes.det_epsus` | `statsum` carries `numest` and `stdev`, covering the 4-6 variables. |
| `crsp.ermport` | DGTW benchmark only; we use market-model adjustment. |
| US Patents, DealScan, global ownership, word indices | Not in any P1 spine. |

---

## Two questions for the seller

1. **Delisting table names** — is it `crsp.dsedelist` / `crsp.msedelist`, or does this
   account carry the newer CIZ-format equivalent?
2. **IBES adjusted vs unadjusted** — `statsum_epsus` is split-**adjusted**;
   `statsumu_epsus` is unadjusted. For SUE the unadjusted file is usually preferred,
   because retroactive split adjustment introduces per-share rounding that can
   dominate a small earnings surprise. **Which one is available?**

---

## Known scope bug — fix before pulling

`p1/wrds/pull_scope.json` reports `daily_start: 2020-03-04`. That was derived from
the earliest **effective** date (2021-03-26) minus 250 trading days.

But the event study anchors `t=0` on the **announcement** date (§6 threat T2; T5
blueprint §5), and the earliest announcement is **2020-05-01**. With a −252
trading-day estimation window, daily data must begin **~2019-05-02**.

Pulling from 2020-03-04 would silently truncate the market-model estimation
window for the earliest events — no error, just a shorter window and a quietly
different beta. The ranges above use **2019-01-01** for daily to leave buffer.

`universe.py` should be re-pointed at `announce_date` before `pull_scope.json` is
regenerated.

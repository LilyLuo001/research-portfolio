# WRDS data requirements — P1 (plan v2.1) + Refraction (plan v2.1 + amendment v2.2)

_Seat C, 2026-09-02. Written after the owner obtained a WRDS account._

**What this is.** The complete list of datasets, variables, date ranges and
universes that the two live plans require — derived from the plan documents and
from committed artifacts executed in this container, not from memory.

**What this supersedes.** `p1/wrds/TABLE-REQUEST.md` (Rev 2, 2026-08-27) and
`p1/wrds/SHOPPING-LIST.md` were written for a **¥20/table seller** under the
**pre-v2.1** outcome set (daily CAR as the main evidence). Both are now
incomplete in seven specific ways (§1). They stay in the repo as the price/cut
record; **this file is the requirement of record.** `p1/wrds/tables.yaml` remains
the machine-readable contract and is the thing that must be patched (§6).

**Meta-rule 1 discipline.** Every table and column name below is a **candidate**
until `python p1/wrds/pull.py discover` has read it off the live server. Names
here are hints for the resolver, never authority. Every count is either computed
in-container (marked ✔computed, with the command) or explicitly marked
`[ESTIMATE]` / `[CONFIRM]`.

---

## 0. The two plans in one paragraph each

**P1 (`docs/基金转换实验_博士研究计划.md`, v2.1).** Unit of analysis = **stock ×
earnings event**. Main estimand = the **h-curve of β_h** in
`CAR^h_{i,e} = β_h·(SUE × Post × Exposure^pre) + …` for
h ∈ {5m, 15m, 30m, 60m, close, +1d} (§6.1.2), estimated separately for the
**idiosyncratic vs systematic** components of the surprise (§7.2), with
`Speed^h` demoted to a readability/robustness statistic. Everything daily
(CAR[0,+120], FERC, IPT, price delay, Amihud, 1−R², spreads) is **verification
layer** (§7.3–§7.6). Gate 0 (§9.0, portfolio continuity) runs before any headline
regression. Headline inference = (sponsor, stock) multiway wild cluster bootstrap
(§15.3.1).

**Refraction (`docs/MacroEvent_Chapter_Plan_v2_1_FINAL.md` + amendment v2.2).**
Unit = **stock × macro announcement** (FOMC/CPI/NFP), daily frequency on the
critical path. Estimand = γ on `Post × ConvExp × (L_i·S_a)` decomposed into
γ_mkt / γ_tilt / γ_fac, where `L_i = β_b^LOO(i) − β_i` is built from
**announcement-regime betas estimated on pre-conversion announcements only**.
Sample: announcements **2017-01→2026-06**, waves 2021-03→2025-12, equity_US only
(`refraction/frozen_config.yaml`). It reuses P1's event register and ConvExp
read-only and needs **CRSP daily including the open**, plus IBES for the
fundamental-anchoring leg.

---

## 1. Seven ways the old request list is now wrong

| # | Delta | Consequence if not fixed |
|---|---|---|
| **D1** | **IBES `anntims` (announcement time-of-day) is not requested anywhere** — not in `TABLE-REQUEST.md`, not in `tables.yaml`, not in `pull.py`'s IBES SELECT | Plan §7.1 classifies every event RTH / pre-market / post-market and sets `t_0` differently per class; §7.1.1 requires a **pure ex-ante sample table** built from that classification *before* any β_h, and §4.1 makes that table the **precondition for buying intraday data**. K3 (§9.1) gates on `anndats`+`anntims` coverage ≥ 70%. Without this column the v2.1 main result cannot be defined, let alone estimated. **This is the single highest-value line in this document.** |
| **D2** | Intraday trades/quotes were scoped to an **external vendor** (Databento TBBO, §4.1) because there was no WRDS account | With an account, WRDS TAQ may supply the same window at zero marginal cash cost. §4.1's ¥1,665 is self-declared as an unverified estimate with 7 soft inputs. **Establish WRDS TAQ availability before spending anything.** |
| **D3** | Daily window starts **2019-04-10** (`pull_scope.json`) | Refraction's announcement sample starts **2017-01-01** and its placebo-in-time re-estimates the whole design on **2017–2020** with fake conversion dates. A 2019 start silently kills the refraction chapter's placebo and its 8-pre-quarter coverage assert (A2). See §3. |
| **D4** | `crsp.dsf` / `crsp.msf` SELECT lists **omit `shrout`, `cfacshr`, `cfacpr`** although `tables.yaml` declares them | `p1/tests/test_gate0_continuity.py::test_direction_against_real_crsp_corporate_actions` cannot run, so the multiply-vs-divide direction of the share adjustment factor stays unverified against data. An inverted factor does not raise — it turns every split into fake turnover and silently fails Gate 0. |
| **D5** | `crsp.holdings` is pulled only up to the **last effective date** (`pull.py`, `mf_holdings`) | Gate 0 (§9.0) compares the **last pre-conversion** report against the **first post-conversion** report. With the window closed at the effective date the post side does not exist and Gate 0 — which the plan moved *ahead of* the headline regression — cannot be computed from CRSP at all. |
| **D6** | No **share code / exchange code / industry code**, no **fund flows / TNA / expense ratio**, no **index membership** anywhere | Universe filters, the `δ_{industry×quarter}` and `δ_{ind×a}` fixed effects, threat T5 (flows, FIT, fees) and threat T9 (Russell reconstitution — a *forced* sub-spec per `P1_修订补丁_v1_1.md`) all have no data source. |
| **D7** | The pull universe is derived from **`conv_exposure_free.parquet`, which is stale** | ✔computed: that parquet's lineage names `events_merged.csv` at sha `758b2ae…`; the committed event file today is sha `e5a4413…` (**172 rows**, up from 131 — commit `0bbd3ae`). ConvExp covers **49 waves**; the register has **96**. Scoping CRSP to today's 6,747 CUSIPs bakes the stale universe into the pull, and the ConvExp rebuild is blocked on `sec.gov` egress, not on WRDS. **Mitigation in §2: scope by CRSP universe filter, not by our CUSIP list.** |

---

## 2. Universes — who to pull

✔computed (`p1/events_merged.csv`, `p1/conv_exposure_free.parquet`,
`p1/t2_free/NEED_HUMAN_stocks.csv`, `p1/t2_wrds/waves_members.csv`;
reproduce with `python p1/wrds/universe.py`):

| Universe | Definition | Size today |
|---|---|---|
| **U1 — ConvExp stocks** | CUSIPs with a computed exposure cell | **2,241** CUSIPs / 6,377 cells / **49** waves |
| **U1b — denominator-dropped stocks** | held but no shares-outstanding denominator; they are treated stocks missing a divisor, not missing a holding | **4,635** CUSIPs (5,929 rows) |
| **U1 ∪ U1b** | what `pull.py` currently scopes CRSP to | **6,747** CUSIPs |
| **U2 — treated set (≥0.5%)** | `conv_exp ≥ 0.005` | **398** stock-waves / **389** stocks / **10** waves; W002 (DFA 2021-06-11) alone = **361** |
| **U3 — converting funds** | rows of the event register | **172** events, **170** distinct `fund_name`, **84** distinct `family` (registrant/trust, *not* asset manager — see §5 note), **96** distinct effective dates |
| **U3b — fund tickers** | usable join keys on the register | `mutual_fund_ticker` non-null on **19 / 172**; `etf_ticker` non-null on **9 / 172** → **funds must be matched by normalised NAME**, as `pull.py::_landed_fundnos` already does |
| **U4 — control universe** | CRSP US common stock, not in U1 | not enumerable from the repo — must come from CRSP |

**Scoping recommendation (changes the current design).** Scope the CRSP pulls by
a **universe filter read off CRSP itself** — `shrcd in (10,11)` and
`exchcd in (1,2,3)` — rather than by our 6,747-CUSIP list. Three reasons, none of
them convenience:

1. **U1 is stale (D7).** Any pull scoped to it must be re-run after the ConvExp
   rebuild, and the rebuild is blocked on network egress this project does not
   control. A second rental costs more than the extra gigabytes.
2. **The control layers need non-held stocks.** Plan §5 layer 3 matches on
   size × B/M × industry × pre-ETF ownership × Amihud among **non-held** stocks;
   refraction §5 layer 3 is the same. Neither can be built from a universe
   defined as "stocks the converting funds held".
3. **NYSE breakpoints.** Market-cap deciles (`mcap_decile` in the frozen ConvExp
   contract) and any DGTW-style sort need NYSE-only breakpoints computed over the
   whole cross-section, not over our subset.

Practical shape: **`crsp.msf` full universe** (monthly, small) + **`crsp.dsf`
restricted to `shrcd in (10,11)`** over the full window. `[ESTIMATE]` ~1.2–2M
daily rows per year at that filter, i.e. ~15–25M rows for §3's window and roughly
1–3 GB of parquet with the columns in §4 — larger than the current scoped plan,
far below the "whole CRSP universe, all share codes, all columns" case the
sprint runbook warns about. **Measure it on the server with a `count(*)` before
running the pull**, do not trust this estimate.

---

## 3. Date ranges — when, and why

Every range below is derived, not chosen. Anchors are ✔computed:
announcements **2020-05-01 → 2026-07-08**, effective dates
**2021-03-26 → 2026-11-20** (register); equity_US subset: announce
**2021-03-03 → 2026-06-01**, effective **2021-06-11 → 2026-11-20**.

| Dataset | **Range to pull** | Binding constraint |
|---|---|---|
| **CRSP daily** (`dsf`, `dsi`, `dsedelist`) | **2014-01-01 → today** | Refraction announcements start 2017-01-01 (`frozen_config.sample.announcements_start`); its placebo-in-time re-estimates the design on **2017–2020 fake conversion dates**, and assert A2 requires **±8 quarters** of announcements around each wave → a fake wave in 2018 needs announcements back to 2016. P1 separately needs a **−250 trading-day** market-model window (≈14 calendar months) before the earliest event used, and pre-trend figures 4–8 quarters before the announcement date. 2014-01-01 covers every combination with margin; the current 2019-04-10 covers none of the refraction ones. |
| **CRSP monthly** (`msf`, `msi`, `msedelist`) | **2012-01-01 → today** | Momentum sorts need 12 months before the first daily date; book-to-market is stamped with a 6-month lag; the Jegadeesh reversal strategy (spec 2-7) needs a formation month before the first event. Monthly files are tiny — take the margin. |
| **CRSP names / link / crosswalks** | **full history, no date filter** | `stocknames`, `ccmxpf_*`, `portnomap` are mapping histories; a date filter on a mapping history is a bug. |
| **Compustat `fundq` / `funda`** | **2010-01-01 → today** | FERC uses a **3-year forward** earnings sum (spec 1-2) and the SUE time-series branch an **8-quarter lookback**; annual book equity for the §107 control match sits at a fiscal year end up to ~2 years before an event. Scoped by gvkey these files are small. |
| **IBES `statsum` / `statsumu` / `actuals`** | **2012-01-01 → today** | Must cover every earnings event in the refraction pre-period (from 2016) plus the 8-quarter SUE lookback, plus the analyst environment variables (4-6) for the same span. |
| **IBES `idsum` / identifiers** | **full history** | Mapping history. |
| **WRDS TAQ daily indicators (IID)** | **2014-01-01 → today**, or the product's full coverage if shorter | Spine four + the Saglam–Tuzun replication + refraction H5′; matches the daily window so spread variables exist wherever returns do. |
| **TAQ intraday (trades/quotes)** | **only (symbol × date) inside earnings-announcement windows** — list produced in Phase 4 of the execution prompt | §4.1: "日内数据只需要盈余公告窗". Range follows the event list; **do not** pull a date range. |
| **CRSP MF `holdings`** | **2018-01-01 → 2027-06-30** (i.e. **past the last effective date 2026-11-20 by ≥2 reporting periods**) | Gate 0 (§9.0) needs the **first post-conversion** report as well as the last pre-conversion one. The current code stops at the last effective date (D5). |
| **CRSP MF header / portnomap / fund summary** | **full history** (header, map); **2018-01-01 → today** (TNA/flows/fees) | Threat T5 controls: fund net flows, Lou-style FIT, fee changes. |
| **Fama-French factors** | 2012-01-01 → today | Characteristics-implied prior for the refraction β shrinkage; robustness benchmarks. Free either way — take it while connected. |

---

## 4. Table-by-table specification

Legend: **T1** = without it a named part of a live plan cannot be computed;
**T2** = validation / robustness / second chapter; **T3** = enhancement layer,
main conclusions forbidden to depend on it (plan §7.5).
`[CONFIRM]` = must be settled against the live server or the WRDS variable docs.

### 4.1 CRSP stock — the spine

| # | Candidate table | Tier | Freq | Range | Columns to request | Serves |
|---|---|---|---|---|---|---|
| 1 | `crsp.stocknames` (alt `crsp.dsenames`) | T1 | ref | full | `permno`, `permco`, **`ncusip`**, `cusip`, `ticker`, `comnam`, `namedt`, `nameendt`, **`shrcd`**, **`exchcd`**, **`siccd`**, `hsiccd` `[CONFIRM which of these live on this table vs dsenames]` | CUSIP↔PERMNO (blank on all 6,377 ConvExp rows and all refraction join keys); the universe filter (§2); symbol keys for TAQ; the industry code for `δ_{ind×·}` |
| 2 | `crsp.dsf` | T1 | daily | 2014-01-01→today | `permno`, `date`, `ret`, `retx`, `prc`, `openprc`, `vol`, `shrout`, **`cfacpr`**, **`cfacshr`**, `bid`, `ask`, `bidlo`, `askhi`, `numtrd` | Every P1 daily outcome; refraction's whole critical path (the **open** is load-bearing for its close→open / open→close timing split); Amihud; 1−R²; variance ratio; Gate 0's share-factor direction test |
| 3 | `crsp.dsi` | T1 | daily | 2014-01-01→today | `date`, `vwretd`, `ewretd`, `vwretx`, `sprtrn` | Market-model benchmark; `λ_a` sanity; refraction's market leg of `L_mkt` |
| 4 | `crsp.dsedelist` (alt CIZ-format equivalent) | T1 | events | 2014-01-01→today | `permno`, `dlstdt`, `dlret`, `dlretx`, `dlstcd`, `dlpdt` | Delisting inside [0,+120]; omitting it does not raise, it biases the CAR path silently (spec 2-2, Shumway −30% imputation) |
| 5 | `crsp.msf` | T1 | monthly | 2012-01-01→today, **full universe** | `permno`, `date`, `prc`, `altprc`, `ret`, `retx`, `shrout`, `cfacpr`, `cfacshr`, `vol` | ConvExp denominator; market-cap deciles + **NYSE breakpoints**; the matched-control pool; monthly reversal strategy |
| 6 | `crsp.msi` | T2 | monthly | 2012-01-01→today | `date`, `vwretd`, `ewretd` | Monthly benchmark for the reversal strategy and any DGTW-style reconstruction |
| 7 | `crsp.msedelist` | T2 | events | 2012-01-01→today | `permno`, `dlstdt`, `dlret`, `dlstcd` | The monthly file's delisting; only the Jegadeesh reversal variable (2-7) depends on it |
| 8 | `crsp.ccmxpf_lnkhdr` (alt `ccmxpf_linktable`, `ccmxpf_lnkused`) | T1 | ref | full | `gvkey`, `lpermno`, `lpermco`, `linktype`, `linkprim`, `linkdt`, `linkenddt` | gvkey↔permno. **Pull before Compustat** — the fundamentals pull is scoped by gvkey. Do **not** apply the `linktype/linkprim` filter at pull time; it belongs to the merge and the rows are needed to audit it |

### 4.2 Compustat

| # | Candidate table | Tier | Freq | Range | Columns | Serves |
|---|---|---|---|---|---|---|
| 9 | `comp.fundq` (North America — `[CONFIRM]` not Global) | T1 | quarterly | 2010-01-01→today | `gvkey`, `datadate`, `fyearq`, `fqtr`, `datacqtr`, **`rdq`**, `epspxq`, `epsfxq`, `ibq`, `niq`, `atq`, `ceqq`, `cshoq`, `prccq`, `saleq`, `ajexq`, `spiq`, `sich`, `cusip` | GNZ systematic/idiosyncratic earnings decomposition (spec 1-1 — **now blocking the main result**, §7.2); SUE time-series branch; FERC; `rdq` is the Compustat half of the §4 **dual-source announcement-date check**; `sich` is the industry code |
| 10 | `comp.funda` (North America) | T1 | annual | 2010-01-01→today | `gvkey`, `datadate`, `fyear`, `ceq`, `seq`, `pstkl`, `pstkrv`, `pstk`, `txditc`, `csho`, `prcc_f`, `at`, `sich` | Book equity for the §107 / refraction-layer-3 control match. `ceq` alone is the crude definition; `seq/pstk*/txditc` are there so the standard book-equity construction is *possible* — **which definition is used is a `NEED_HUMAN`, not a default** |
| 11 | `comp.company` (alt `comp.names`) `[CONFIRM]` | T2 | ref | full | `gvkey`, `conm`, `sic`, `naics`, `gsector`, `gind`, `gsubind` | A stable industry classification for the fixed effects; GICS if the subscription carries it, SIC otherwise |

### 4.3 IBES — including the field the whole v2.1 design turns on

| # | Candidate table | Tier | Freq | Range | Columns | Serves |
|---|---|---|---|---|---|---|
| 12 | `ibes.actu_epsus` (alts `act_epsus`, `actpsum_epsus`) | **T1 — highest priority** | per announcement | 2012-01-01→today | `ticker`, `cusip`, `oftic`, `pends`, `anndats`, **`anntims`**, `value`, `curr_act`, `usfirm`, `measure` | `t_0` for **every** event in the design. **`anntims` is the blocker**: plan §7.1's RTH / pre-market / post-market classification, §7.1.1's ex-ante sample table, §4.1's intraday purchase decision and gate K3 all fail without it. Its **time zone and non-null rate must be verified on the server** before anything is computed from it |
| 13 | `ibes.statsumu_epsus` (**unadjusted**) **and** `ibes.statsum_epsus` (split-adjusted) | T1 | monthly snapshots | 2012-01-01→today | `ticker`, `cusip`, `oftic`, `statpers`, `fpedats`, `fpi`, `measure`, `meanest`, `medest`, `stdev`, `numest`, `actual`, `anndats_act`, `curcode` | SUE-IBES (the D1 primary); analyst coverage and dispersion (spec 4-6). **Pull both files.** For SUE the unadjusted file is preferred — retroactive split adjustment introduces per-share rounding that can dominate a small surprise — and at an owned account there is no reason to choose sight-unseen |
| 14 | `ibes.idsum` (alt `ibes.id`) | T1 | ref | full | `ticker`, `cusip`, `oftic`, `cname`, `sdates` | IBES ticker ↔ **historical** CUSIP. A point-in-time CUSIP on a statsum row is not the mapping history, and 84% of this panel sits in market-cap deciles 1–5 where identifier changes cluster |
| 15 | `ibes.detu_epsus` / `ibes.det_epsus` | T2 | per forecast | 2012-01-01→today | `ticker`, `analys`, `fpi`, `value`, `anndats`, `revdats`, `actdats`, `fpedats` | Only if the exact "distinct analysts in a 90-day window" rule (spec 4-6, decision D6) turns out to matter, and for refraction's **analyst-revision** leg of the fundamental-anchoring test (plan §7.2). Cheap on an owned account; skip under time pressure |

### 4.4 Intraday — the v2.1 main result

| # | Candidate table | Tier | Freq | Range | Columns | Serves |
|---|---|---|---|---|---|---|
| 16 | WRDS **Intraday Indicators (IID)** — `wrdsapps.taq_iid`, `taqmsec.wrds_iid`, or the current equivalent `[CONFIRM name and key]` | T1 | daily | 2014-01-01→today | key (`sym_root`+`sym_suffix` **or** `permno` — `[CONFIRM which]`), `date`, effective spread, quoted spread, realized spread, price impact, depth, trade count `[CONFIRM exact field names and whether spreads are dollar or proportional]` | Spine four (4-1, 4-2); the Saglam–Tuzun replication (kill-test K4); refraction H5′. **This is the WRDS value-add daily product, not raw TAQ** |
| 17 | TAQ **intraday quotes and trades** — `taqmsec.cqm_*` / `ctm_*`, `taqm_*`, or the monthly/nbbo equivalents `[CONFIRM what this subscription actually carries]` | **T1 if available** | intraday | **(symbol × date) list only** | quote: `date`, `time_m`, `sym_root`, `sym_suffix`, `best_bid`, `best_bidsizshares`, `best_ask`, `best_asksizshares`; trade: `price`, `size`, `tr_corr`, `tr_scond` `[CONFIRM]` | `CAR^h` / `Speed^h` at h ∈ {5m,15m,30m,60m} — **the v2.1 main result**. Decision D-T3-13 says build the path from the **midquote**, not trade prices, so the quote file is the primary need. **If the account carries this, the Databento purchase in §4.1 may be unnecessary — establish availability, extended-hours coverage and small-cap coverage before any external spend** |

**Extended hours is a blocking sub-question, not a detail.** Plan §7.1 sets
`t_0` = the next 09:30 open for pre-market and post-market announcements, and
§7.1.1 warns that if the ex-ante table makes pre/post the main sample, the
intraday source **must** cover extended hours. Ask this of the WRDS product
explicitly, exactly as §4.1 requires asking it of Databento.

### 4.5 CRSP Mutual Fund / ETF

| # | Candidate table | Tier | Freq | Range | Columns | Serves |
|---|---|---|---|---|---|---|
| 18 | `crsp.fund_hdr` / `crsp.fund_names` `[CONFIRM]` | T2→**T1 for Gate 0** | ref | full | `crsp_fundno`, **`fund_name`**, `ticker`, `et_flag`, `index_fund_flag`, `mgmt_name`, `mgmt_cd`, `crsp_obj_cd`, `first_offer_dt`, `end_dt` | Fund identity. `fund_name` is load-bearing (U3b: a real MF ticker on only 19/172 rows). `et_flag`/`index_fund_flag` are how the **ETF-ownership** variable gets built (§5 note on `pre_etf_ownership`). `mgmt_name` is a candidate input to the **trust → asset-manager crosswalk** the headline inference needs (§15.3.0) |
| 19 | `crsp.portnomap` | T2 | ref | full | `crsp_portno`, `crsp_fundno`, date range columns | Portfolio ↔ fund crosswalk; holdings are keyed on one and identity on the other |
| 20 | `crsp.holdings` | T2→**T1 for Gate 0 and refraction R2** | quarterly reports | **2018-01-01 → 2027-06-30** | `crsp_portno`/`crsp_fundno`, `report_dt`, `permno`, `cusip`, `nbr_shares`, `market_val`, `percent_tna`, `security_name` | (a) the CRSP-identifier twin of the free-path ConvExp; (b) **Gate 0's post-conversion first report** (D5); (c) refraction's `holdings_weights.parquet` — basket weights for `β_b^LOO`, which does not exist in the repo and blocks R2 |
| 21 | `crsp.fund_summary` (alt `monthly_tna_ret_nav`) `[CONFIRM]` | T2 | monthly/quarterly | 2018-01-01→today | `crsp_fundno`, `caldt`, `tna_latest`, `mret`, `exp_ratio`, `mnav`, `nav_latest` | Threat **T5**: fund net flows, Lou (2012) flow-induced trading, fee changes. Currently has **no source at all** in the request list (D6). Also supplies the twin-unconverted-fund control layer (§5 layer 2) |

### 4.6 Index membership, factors, and the enhancement layer

| # | Item | Tier | Notes |
|---|---|---|---|
| 22 | **Russell / S&P index membership with effective dates** — `[CONFIRM what this account carries: `comp.idxcst_his` for S&P; a Russell constituent product; or nothing]` | T1 for a *forced* sub-spec | Threat **T9**: DFA's 2021-06-11 wave sits two weeks before the Russell reconstitution, and `docs/P1_修订补丁_v1_1.md` makes Russell handling a **forced T5 sub-spec**. Refraction's threat **T5** additionally wants `L^Russell_i` — the stock's *existing* basket lever. The frozen `outcomes_panel` contract already declares a `russell_change` column with no producer. **If the subscription has no membership file, record it as a NEED_HUMAN now**; the fallback (rank-based reconstruction with banding) is a design decision, not a data fix |
| 23 | `ff.factors_daily`, `ff.factors_monthly` `[CONFIRM library]` | T2 | Characteristics-implied prior for refraction's Vasicek shrinkage; robustness benchmarks. Free from Ken French too, but take it while connected |
| 24 | **13F institutional holdings** (`tfn.s34` / the current Refinitiv equivalent) `[CONFIRM]` | T2 | Plan §4 lists 13F for "controlling other ownership-structure change"; refraction's saturation control (T5) needs pre-existing ETF/passive ownership. **Note the plan itself prefers CRSP MF + N-PORT over s12/s34** — pull only if the subscription carries it and the ETF-ownership build from CRSP MF proves insufficient |
| 25 | **OptionMetrics** (`optionm.*`) — first option listing date per stock | T3 | H4's optionability channel, and the second chapter. Enhancement layer: main conclusions may not depend on it (§7.5) |
| 26 | **Short interest / borrow** (FINRA short interest, Markit) `[CONFIRM availability]` | T3 | H4's shortability channel. Same enhancement rule |
| 27 | **Macro consensus for CPI/NFP** | refraction T1 | `refraction/frozen_config.yaml: surprise.consensus_source` is **null**, a standing `NEED_HUMAN` (Bloomberg ECO at BU vs a WRDS alternative). FOMC surprises come free from the SF Fed USMPD and are **not blocked**. While connected, run `list_libraries()` and report every macro/consensus/survey product the subscription carries — this is a **discovery-and-report** item; the choice stays with the owner |

**Explicitly not wanted:** raw full-tape TAQ over a date range (terabytes; §4.1
wants announcement windows only), `crsp.ermport` (DGTW benchmark portfolios — the
implemented benchmark is the market model; DGTW survives only as the D-T3-11
second version and would be reconstructed, not bought), US Patents, DealScan,
global ownership, word indices.

---

## 5. Variable → source matrix

Only variables whose source is a WRDS field are listed; derived quantities cite
the fields they are derived from. "§" refers to `docs/基金转换实验_博士研究计划.md`
unless prefixed **R** = `docs/MacroEvent_Chapter_Plan_v2_1_FINAL.md`.

| Variable | Plan locator | Built from |
|---|---|---|
| `permno` (the join key, blank on all 6,377 ConvExp rows) | §4, amendment v2.2 §4 | `stocknames.permno` × `ncusip` (**not** `cusip` — the historical value is what a point-in-time N-PORT holding must match) |
| `Exposure^pre_{i,w}` (`conv_exp`) | §6.1.1 | N-PORT shares (free path) ÷ `msf.shrout` × `cfacshr`; CRSP twin from `holdings.nbr_shares` |
| `shares outstanding` units | `tables.yaml` assert | `msf.shrout` — **the ×1000 assumption is unverified**; a 1000× error does not raise, it moves every exposure |
| share-adjustment direction | Gate 0 | `dsf.cfacshr` + `dsf.shrout` in the **same** pull; the direction test requires raw × factor to be continuous across real corporate actions |
| `t_0` (announcement instant) | §7.1, §7.1.1 | `actu_epsus.anndats` + **`anntims`**, cross-checked against `fundq.rdq` (§4 dual-source rule) |
| RTH / pre-market / post-market class | §7.1 table | `anntims` vs 09:30–16:00 ET; **time zone `[CONFIRM]`** |
| `CAR^h`, h ∈ {5m,15m,30m,60m} | §6.1.2 | intraday **midquotes** (item 17, decision D-T3-13) |
| `CAR^{close}`, `CAR^{+1d}`, `OpenGap` | §7.1.1 | `dsf.prc`, `dsf.openprc`, `dsi.vwretd` |
| market-model residuals ([−250,−21]) | spec 0-1 | `dsf.ret`, `dsi.vwretd` |
| `SUE` (analyst branch — D1 primary) | spec 1-5, §125 | `statsumu_epsus.meanest`/`medest` vs `actu_epsus.value`, deflated `[NEED_HUMAN: by price or by forecast dispersion]` |
| `SUE` (time-series branch) | §125 fork | `fundq.epspxq` 8-quarter seasonal random walk |
| Systematic vs idiosyncratic surprise (**H3 — the dividing line with GNZ**) | §7.2, spec 1-1 | `fundq.epspxq`/`niq` scaled by `prccq`×`cshoq` or `atq`; industry from `sich`; market/industry aggregates from the same cross-section. Formula still `[NEED_PDF]` |
| FERC, IPT, Hou–Moskowitz delay | §7.4, specs 1-2/1-3/1-4 | `dsf.ret`, `dsi.vwretd`, `fundq`, announcement dates |
| Amihud | spec 4-3 | `dsf`: `|ret| / (|prc| × vol)`, zero-volume days excluded |
| 1 − R² | spec 4-4 | `dsf.ret` on `dsi.vwretd`, quarterly |
| Variance ratio | spec 2-8 | `dsf.ret` |
| Effective spread, price impact | specs 4-1/4-2 | TAQ IID fields — **convention `[CONFIRM]`**; fall back to `dsf.bid`/`ask` quoted spread if IID is absent and CRSP quotes are populated (`verify.py` decides this from the landed data, not from an assumption) |
| Analyst coverage, dispersion | spec 4-6 | `statsum*.numest`, `stdev` (or `det*` for the strict 90-day distinct-analyst rule) |
| Delisting handling | spec 2-2 | `dsedelist.dlret`, −30% imputed when missing |
| Book-to-market (control match) | §107, R§5 | `funda.ceq` (or the full `seq/pstk*/txditc` construction) ÷ `msf` market cap |
| Market-cap decile | ConvExp contract | `msf.prc × shrout`, **NYSE breakpoints from the full universe** |
| `pre_etf_ownership` | §6.1.1 **NEED_HUMAN** | ⚠ currently **equals `conv_exp`** in the parquet — the name is a lie. A real measure = Σ ETF holdings of stock i ÷ shares outstanding, from `crsp.holdings` restricted by `fund_hdr.et_flag` (or 13F). **Until rebuilt it may not be used as a GNZ-style ownership control** |
| Fund flows, FIT, fee change | §6.3 T5 | `fund_summary.tna_latest`, `mret`, `exp_ratio` |
| Portfolio continuity (Gate 0) | §9.0 | last pre- vs **first post-**conversion holdings: Jaccard, Σ min(w_pre,w_post), corr(w), turnover |
| `sponsor` cluster dimension | §15.3.0 ⚠ | **NOT `events_merged.family`** — that is the registrant/trust name (✔computed: 84 distinct, and the plan names JPMorgan Trust I/II and DFA Investment Dimensions Group / Dimensional Investment Group as split identities of one manager). Needs a hand-verified trust → asset-manager crosswalk; `fund_hdr.mgmt_name` is a **candidate input, not the answer** |
| **R** `S_a` (macro surprise) | R§2 | SF Fed USMPD (public, not WRDS); CPI/NFP consensus `NEED_HUMAN` |
| **R** `β_i` (announcement-regime beta) | R§3 | `dsf.ret` on announcement days **strictly before** the wave's effective date (assert A4), Vasicek-shrunk toward a characteristics-implied prior |
| **R** `β_b^LOO(i)` | R§3 | basket weights from `holdings` (pre-period) × the same announcement-day returns |
| **R** `L`, `L_mkt`, `L_tilt`, `F′λ_b` | R§3 | derived from `β_i`, `β_b^LOO`, `dsi.vwretd`, factor returns |
| **R** timing split (close→open, open→close) | R§7 spine 1 | `dsf.openprc` + `dsf.prc` — **the reason the open is on the critical path** |
| **R** fundamental anchoring | R§7 spine 2 | `statsum*`/`actu*` next-quarter SUE and analyst revisions |

---

## 6. Patch list — what must change in this repo before the window opens

Each item is mechanical, offline, and testable without a connection. Ordered by
what breaks if it is skipped.

| # | File | Change | Breaks if skipped |
|---|---|---|---|
| **P1** | `p1/wrds/tables.yaml` | Add logical column `anndate_time` (candidates: `anntims`) to the `ibes` pull, plus an assert `anntims_timezone_and_coverage: NEED_HUMAN` | The v2.1 main result has no `t_0`; K3 cannot be evaluated; §7.1.1's ex-ante table cannot be built; the intraday purchase decision stays un-makeable |
| **P2** | `p1/wrds/pull.py` (`build_queries`, `ibes.actuals`) | Add the resolved `anntims` column to the SELECT | Same as P1 — the column exists in the contract but never lands |
| **P3** | `p1/wrds/pull.py` (`dsf`, `msf`) | Add `shrout`, `cfacshr`, `cfacpr` to both SELECTs (already declared in `tables.yaml`) | `test_gate0_continuity.py::test_direction_against_real_crsp_corporate_actions` cannot run; the share-factor direction stays assumed |
| **P4** | `p1/wrds/pull.py` (`mf_holdings`) | Extend the holdings window past the last effective date by ≥2 reporting periods | Gate 0 (§9.0) — which the plan moved **ahead of** the headline regression — has no post-conversion holdings |
| **P5** | `p1/wrds/tables.yaml` + `pull.py` (`compustat.fundq`) | Add `niq`, `atq`, `ceqq`, `cshoq`, `prccq`, `saleq`, `sich`, `fyearq`, `fqtr` | The GNZ decomposition (§7.2, now a **main** result) has no earnings measure to scale; SUE-TS has no series; there is no industry code |
| **P6** | `p1/wrds/tables.yaml` + `pull.py` (`stock_names`) | Add `shrcd`, `exchcd`, `siccd`, `comnam`, `permco` | No universe filter, no industry FE, no control pool |
| **P7** | `p1/wrds/universe.py` | Widen `daily_start` to 2014-01-01 and `monthly_start` to 2012-01-01, or add a `--profile refraction` that does | Refraction's placebo-in-time and its ±8-quarter assert A2 both fail; a second rental is then required |
| **P8** | `p1/wrds/tables.yaml` | New pull `fund_flows` (candidates `crsp.fund_summary`, `crsp.monthly_tna_ret_nav`) | Threat T5's controls (flows, FIT, fees) have no source |
| **P9** | `p1/wrds/tables.yaml` | New pull `index_membership` (candidates `comp.idxcst_his`, a Russell product) with an explicit `NEED_HUMAN` if nothing resolves | Threat T9's **forced** sub-spec and the `russell_change` column in the frozen contract have no producer |
| **P10** | `p1/wrds/tables.yaml` (`ibes.summary`) | Land **both** `statsum_epsus` and `statsumu_epsus` rather than resolving to one | The adjusted-vs-unadjusted question becomes a second rental instead of a `groupby` |
| **P11** | `p1/wrds/tables.yaml` | New pull `msi` + `msedelist` | Monthly benchmark and monthly delisting for spec 2-7 |
| **P12** | `p1/wrds/tables.yaml` (`taq_iid`) | Add a sibling pull `taq_intraday` whose scope is a **(symbol, date) list**, never a date range, and which refuses to run without that list | Either no v2.1 main result, or an accidental terabyte-scale query |

`p1/wrds/verify.py` should gain two checks in the same pass: **`anntims`
non-null rate** and **holdings coverage on both sides of each effective date**.
Both are release-gate facts — cheap to fix while the account is live, expensive
after.

---

## 7. What must be answered on the live server (discovery checklist)

These are not answerable by listing columns; they are the questions where a wrong
answer returns a plausible number instead of an error.

1. **`anntims` — exists, time zone, non-null rate by year and by market-cap
   decile.** The whole v2.1 design routes through it.
2. **Intraday availability** — which TAQ product this subscription carries, its
   key (symbol vs permno), whether it covers **extended hours**, and its small-cap
   coverage. Decides whether §4.1's external purchase is needed at all.
3. **IID field semantics** — which effective-spread convention (dollar vs
   proportional, quote-matching rule) the chosen field implements.
4. **`shrout` units** on `msf` and `dsf`; and whether `cfacshr` multiplies or
   divides, checked **against real corporate actions in the landed data**, not
   against documentation alone.
5. **Delisting table format** — `dsedelist`/`msedelist` or the CIZ-format
   equivalent this account carries.
6. **`ncusip` vs `cusip`** on `stocknames` — the resolver will refuse this as
   ambiguous, deliberately. The answer is **`ncusip`**; paste it from the web
   query tool.
7. **CCM link codes present** — which `linktype`/`linkprim` values actually occur,
   before any merge applies the standard filter.
8. **Compustat is North America**, not Global.
9. **Index membership** — does anything resolve? If not, say so explicitly.
10. **Macro consensus** — does any library carry CPI/NFP consensus? Report, do
    not choose.
11. **CRSP MF `et_flag`** (or equivalent) — is an ETF flag available, so
    `pre_etf_ownership` can be rebuilt into the thing its name claims?
12. **Fund-name match quality** — read
    `raw/mf_holdings__matched_fundnos.json`. A zero match refuses automatically;
    a **partial** match cannot be detected by machine and silently drops treated
    funds.

---

## 8. Cut order, if the window is short

Drop from the bottom. Everything above a line is worth more than everything below.

| Rank | Item | What is lost |
|---|---|---|
| **never cut** | `stocknames`, `dsf`, `dsi`, **`ibes` actuals with `anntims`** | No permno, no returns, no benchmark, **no `t_0`** — there is no paper |
| 2 | `ccm_link` → `fundq` | The H3 decomposition, i.e. the dividing line with GNZ (§7.2) |
| 3 | `msf` (full universe) | Deciles, NYSE breakpoints, the control pool |
| 4 | `dsedelist` | Silent survivorship bias in the CAR path |
| 5 | `statsum` + `statsumu` | SUE-IBES, coverage, dispersion |
| 6 | `holdings` + `fund_hdr` + `portnomap` | **Gate 0** and refraction R2's basket weights (this rises to rank 2 if Gate 0 is the next milestone) |
| 7 | TAQ IID | Spine four — **free to cut if CRSP `bid`/`ask` came back populated**; `verify.py` reports which world you are in |
| 8 | `funda` | The §107 matched-control layer. The primary spec (intensity terciles, decision V-3) does not need it |
| 9 | `fund_summary`, `msi`, `msedelist`, `det*`, factors | T5 controls, the monthly reversal variable, the strict analyst rule |
| 10 | OptionMetrics, short interest | Enhancement layer only (§7.5) |

**Never cut `ccm_link` while keeping `compustat`** — the fundamentals pull is
scoped by gvkey and refuses without it.

---

## 9. What WRDS still does not fix

Unchanged from `p1/NON_WRDS_BLOCKERS.md`, restated because an account makes it
tempting to assume otherwise:

- **The literature package (T0 阶段A)** — still the thing that gates the T3 spec's
  `[NEED_PDF]` cells, including the GNZ decomposition equation that now blocks a
  **main** result (§7.2). Data access does not unblock a specification.
- **The ConvExp rebuild** — needs `sec.gov`, not WRDS (though CRSP `shrout` can
  substitute for the missing denominators; see §2 and D7).
- **The Saglam–Tuzun FEDS Note PDF** — half of the K4 replication is transcription.
- **The SUE fork (D1) and every other `DECISION_NEEDED`** — WRDS supplies both
  branches, which is exactly why it cannot pick one.
- **The trust → asset-manager crosswalk** (§15.3.0) — a hand-verified mapping, and
  the headline inference's cluster dimension is not credible until it exists.
- **Refraction's `[PI-DECISION]` items** (amendment v2.2 §2) and its Gate-0
  thresholds — owner decisions recorded in `ops/decisions.md`, not data.

---

## 10. Reproducing the numbers in this document

```bash
python p1/wrds/universe.py                 # the pull scope, offline
python refraction/sample_scale_audit.py    # refraction's treated-mass counts
python p1/wrds/pull.py status              # what is resolved / blocked
sha256sum p1/events_merged.csv             # compare against the lineage sidecars
```

The event-register counts in this file (172 events, 170 fund names, 84 registrant
families, 96 effective dates, 46 `equity_US`, 34 blank `asset_class`) were
computed on `p1/events_merged.csv` at sha `e5a4413…` on 2026-09-02. The ConvExp
counts (6,377 cells, 2,241 CUSIPs, 49 waves, 398 treated cells / 389 stocks /
10 waves, W002 = 361) were computed on `p1/conv_exposure_free.parquet` at sha
`350c3c7…`, **whose lineage names an older event file** — see D7.

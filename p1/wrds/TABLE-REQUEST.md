# P1 — WRDS table request list

_Seat C. Send this to the seller. ¥20/table. **Rev 2, 2026-08-27** — date ranges
corrected after the announcement-anchor fix; two fields added._

**Sample anchors** (from `p1/events_merged.csv` and `p1/wrds/pull_scope.json`,
computed not assumed — regenerate with `python p1/wrds/universe.py`):

| | |
|---|---|
| Announcement dates | 2020-05-01 → 2026-06-30 |
| Effective dates | 2021-03-26 → 2026-11-20 |
| Event-study `t=0` | **announcement date** (§6 threat T2) |
| β̂ / market-model estimation window | −250 to −21 trading days before `t=0` (spine zero estimates β̂ against **SPY**; the daily spines use `vwretd`) |
| Post-event window | +120 trading days |

⚠️ **Ranges below are anchored on the earliest ANNOUNCEMENT (2020-05-01) minus
the estimation window — not on the earliest effective date.** Anchoring on the
effective date under-pulls daily data by ~11 months and silently shortens the
estimation window for the earliest events. `pull_scope.json` was corrected in
commit `971208f`; the ranges here match it, with buffer.

---

## Tier 1 — MUST HAVE · 12 tables · ¥240

| # | Library.Table | Freq | Date range needed | Key fields | Purpose |
|---|---|---|---|---|---|
| 1 | `crsp.stocknames` | reference | **full history** (no date filter) | `permno`, `ncusip`, `cusip`, **`ticker`**, `namedt`, `nameendt` | CUSIP↔PERMNO. Fills `permno`, blank on all 6,377 rows today. Nothing joins without it. **`ticker` is also required** — TAQ-IID is symbol-keyed, so the spread pull cannot be scoped without it. |
| 2 | `crsp.dsf` | **daily** | **2019-01-01 → 2026-08-31** | `permno`, `date`, `ret`, **`retx`** (CIZ: `DlyRetx`), `prc`, `vol`, `openprc`, **`bid`, `ask`, `bidlo`, `askhi`** | CAR paths, Amihud, 1−R², variance ratio, price delay. The big one. **Ask for bid/ask explicitly** — if they are populated, spine four's quoted spread needs no external vendor at all. |
| 3 | `crsp.dsi` | **daily** | **2019-01-01 → 2026-08-31** | `date`, `vwretd`, `ewretd` | Daily market series for spines one/two/four. **NOT the spine-zero market proxy** — see the note below: the β_h curve's β̂ must be estimated against the SAME traded instrument used for the intraday leg (SPY), not against `vwretd`. Still wanted: cheap, and the daily spines use it. |
| 3b | **SPY daily PRICE returns** — `crsp.dsf` filtered to SPY's `permno` | **daily** | **2019-01-01 → 2026-08-31** | `permno`, `date`, **`retx`** (CIZ: `DlyRetx`) — **not `ret`** | **The spine-zero β̂ estimation series** (D-T3-28/29). The event-window leg is a midquote PRICE return, so β̂ must be fitted on price returns on BOTH legs. No extra table: it is rows of item 2. **Confirm SPY is on CRSP with a resolvable permno.** The source is frozen to the CRSP daily file (v2.1j) — there is no code-level fallback. If SPY does not resolve, stop and raise it as a spec change: alternating between CRSP daily SPY and an intraday-aggregated close-to-close gives two different β̂, hence two different `AR^h`, from identical-looking specification text. |
| 4 | `crsp.dsedelist` | daily events | **2019-01-01 → 2026-08-31** | `permno`, `dlstdt`, `dlret`, `dlstcd` | Delisting return inside the 120-day CAR window. Omitting it silently biases spine two — the main evidence. |
| 5 | `crsp.msf` | **monthly** | **2018-01-01 → 2026-08-31** | `permno`, `date`, `prc`, `ret`, `shrout` | ConvExp denominator, market-cap deciles, monthly reversal strategy. |
| 6 | `comp.fundq` | **quarterly** | **2016-01-01 → 2026-08-31** | `gvkey`, `datadate`, `rdq`, `epspxq`, `niq`, `atq`, `cshoq`, `prccq` | Earnings decomposition, FERC, SUE time-series branch, and the Compustat side of the §4 dual-source announcement-date check. |
| 7 | `comp.funda` | **annual** | **2016-01-01 → 2026-08-31** | `gvkey`, `datadate`, `ceq`, `csho`, `prcc_f`, `at` | **Control group.** §107 matches on size × book-to-market × industry × ETF ownership × Amihud. Book equity is annual. |
| 8 | `crsp.ccmxpf_lnkhdr` | reference | **full history** | `gvkey`, `lpermno`, `linktype`, `linkprim`, `linkdt`, `linkenddt` | Compustat (gvkey) ↔ CRSP (permno). Items 6–7 are unusable without it, **and must be pulled before them** — the fundamentals pull is scoped by gvkey. |
| 9 | `ibes.statsum_epsus` | **monthly snapshots** | **2016-01-01 → 2026-08-31** | `ticker`, `cusip`, `statpers`, `fpedats`, `fpi`, `meanest`, `medest`, `stdev`, `numest` | SUE-IBES (decided primary), analyst dispersion, coverage count. |
| 10 | `ibes.actu_epsus` | per announcement | **2016-01-01 → 2026-08-31** | `ticker`, `cusip`, `pends`, `anndats`, `value` | Reported actual EPS **and the announcement date** — `t=0` for every event in spines one and two. |
| 11 | `ibes.idsum` | reference | **full history** | `ticker`, `cusip`, `cname`, `sdates` | IBES ticker ↔ historical CUSIP. A point-in-time CUSIP on a statsum row is not the mapping history. |
| 12 | TAQ **WRDS Intraday Indicators (IID)** | **daily** | **2019-01-01 → 2026-08-31** | symbol or `permno`, `date`, effective spread, price impact | Spine four + the Saglam–Tuzun replication. **This is the WRDS value-add daily product, NOT raw TAQ** — raw TAQ is terabytes and is not wanted. Confirm which identifier it keys on. |

## Tier 2a — holdings bundle · 3 tables · ¥60 · buy all three or none

| # | Library.Table | Freq | Date range needed | Key fields | Purpose |
|---|---|---|---|---|---|
| 13 | `crsp.holdings` | quarterly reports | **2019-04-01 → 2026-11-30** | `crsp_fundno`, `report_dt`, `permno`, `nbr_shares` | CRSP-identifier twin of the free-path ConvExp |
| 14 | `crsp.fund_hdr` *or* `crsp.fund_names` | reference | **full history** | `crsp_fundno`, **`fund_name`**, `ticker` | Fund identity. **`fund_name` is load-bearing**: `events_merged.csv` carries a real mutual-fund ticker on 8 of 131 rows, so the converting funds can only be selected by name. |
| 15 | `crsp.portnomap` | reference | **full history** | `crsp_portno`, `crsp_fundno` | Portfolio no. ↔ fund no. crosswalk |

## Tier 2b — monthly delisting · 1 table · ¥20 · independent

| # | Library.Table | Freq | Date range needed | Key fields | Purpose |
|---|---|---|---|---|---|
| 16 | `crsp.msedelist` | monthly events | **2018-01-01 → 2026-08-31** | `permno`, `dlstdt`, `dlret`, `dlstcd` | Delisting on the monthly file. Only for the Jegadeesh monthly reversal strategy (§7, 2-7). |

**Total: 16 tables = ¥320.**

### Why the fundamentals reach back to 2016 and prices only to 2019

Prices need one estimation window (−250 trading days) before the earliest
announcement: 2020-05-01 − 250 trading days ≈ 2019-04-10, so 2019-01-01 with
buffer. Fundamentals need more: the SUE time-series branch takes an 8-quarter
lookback, and annual book equity for the §107 control match is stamped at a
fiscal year end that can sit almost two years before an event in the worst
alignment. Three extra years covers both, and the quarterly/annual files are
tiny — this costs nothing but a wider `datadate` filter.

---

## DO NOT BUY

| Item | Why |
|---|---|
| Fama-French factors | **Free** from Ken French's data library. Not used: the spine-zero benchmark is a single traded proxy (SPY), and the daily spines use `vwretd`. |
| **Raw TAQ** (trades/quotes) | Terabytes. IID (item 12) is the daily pre-computed aggregation and is what the spec needs. |
| `ibes.det_epsus` | `statsum` carries `numest` and `stdev`, covering the 4-6 variables. |
| `crsp.ermport` | **Ask before buying; default is DROP** (v2.1g/h). The headline `β_h` curve is beta-adjusted market (SPY) at every horizon, so nothing headline depends on this. **Do not buy it merely to preserve a robustness label** — if no daily series covering the sample exists, DGTW robustness is dropped, not manufactured. Whether it supports DGTW *robustness* is an open question: spec 2-3 builds DGTW from **monthly** portfolios with **monthly** returns, and a daily `[0,+120]` path would need a **daily** benchmark-portfolio series. This container cannot check what `crsp.ermport` contains. **At the window ask: (a) does a daily DGTW benchmark-return series exist, (b) is this the table and at what frequency, (c) what coverage period** (2-3 documents the Wermers distribution as running through 2012; our sample is 2021–2026). If no daily series covers the sample, drop this table and confine DGTW robustness to monthly horizons. |
| US Patents, DealScan, global ownership, word indices | Not in any P1 spine. |

---

## Questions for the seller — settle these BEFORE the window opens

Each of these costs window time if discovered live. All four are answerable by
the seller in a sentence.

1. **Delisting table names.** Is it `crsp.dsedelist` / `crsp.msedelist`, or does
   this account carry the newer CIZ-format equivalent?
2. **IBES adjusted vs unadjusted.** `statsum_epsus` is split-**adjusted**;
   `statsumu_epsus` is unadjusted. For SUE the unadjusted file is usually
   preferred — retroactive split adjustment introduces per-share rounding that
   can dominate a small earnings surprise. **Which one is available?**
3. **TAQ IID.** Confirm the account has the WRDS Intraday Indicators product,
   which identifier it keys on (symbol or permno), and that coverage runs
   2019→2026 including small caps.
4. **Compustat coverage.** Confirm `comp.fundq` / `comp.funda` are the North
   America files (not Global).

## One decision to record before the window, not during it

`crsp.stocknames` carries **both** `ncusip` and `cusip`. The resolver will report
that ambiguous and refuse to pick — deliberately, per meta-rule 1. The answer is
**`ncusip`**: it is the historical CUSIP valid over `[namedt, nameendt]`, which is
what a point-in-time N-PORT holding must match. `cusip` is the current-as-of-today
value and mismatches any security that changed identifiers — and 84% of this
panel sits in market-cap deciles 1–5, exactly where identifier changes cluster.
Paste it from the WRDS web query tool when `resolve` asks; do not type it from
memory. Recorded as a `decision_hint` in `tables.yaml`.


---

## The spine-zero market proxy — one instrument on BOTH legs (v2.1h)

The headline `β_h` curve uses `AR^h = R^h − β̂_i · R^h_m` with **no intercept**,
and the market proxy is frozen as one bundle (`变量规格书` D-T3-25..28):

| | frozen |
|---|---|
| instrument | **SPY** — both legs |
| quote convention | **midquote**, same as the stock leg |
| session | **RTH only**; the overnight gap is in NEITHER leg |
| `close` horizon | that session's **actual** close (13:00 ET on a half day) |
| β̂ source | **SPY's own daily close-to-close PRICE returns** (`RETX` / `DlyRetx`), [−250, −21] |
| return concept | **price return on BOTH legs** — stock `RETX` vs SPY `RETX` |

**Why this is on the request list at all:** the event-window leg must be a
*traded* instrument, because `crsp.dsi`'s `vwretd` has no intraday value — the
same reason DGTW cannot be used intraday. And once the intraday leg is SPY, β̂
must be estimated against SPY too. Estimating β̂ against `vwretd` and multiplying
it into an SPY intraday return puts two different market portfolios in one
formula, and it produces a plausible number rather than an error.

**The return concept has to match too.** A quote midpoint contains no dividend,
so the event-window leg is a **price** return. A β̂ fitted on **total** returns
would carry a dividend-inclusive sensitivity into a dividend-free quantity — and
`ret` and `retx` are equally plausible-looking daily returns, so nothing raises.
Hence `retx` on **both** legs, stock and SPY. `ret` is still pulled: the daily
spines use it. **They are not interchangeable.** Confirm at the window whether
this account's daily file spells it `retx` (legacy) or `DlyRetx` (CIZ).

So the ask is not a new table — it is **SPY's rows of `crsp.dsf`** (item 3b),
plus intraday SPY quotes from the same feed as the stock leg (Databento TBBO,
already scoped in plan §4.1).

**The daily source is frozen: CRSP** (v2.1j). Confirm at the window that SPY
resolves to a permno; if it does not, that is a spec change to raise, not a
fallback to take. The point is reproducibility — an intraday-aggregated β̂ and a
CRSP β̂ are different numbers, so alternating between them changes every `AR^h`
while the written specification stays the same.

**One more ask for the secondary OpenGap outcome**: the gap is a
previous-close→next-open **price** return, so on an **ex-distribution** date it
mechanically contains the distribution drop. Those observations are excluded and
the counts reported (D-T3-31). Note the wording — *ex-distribution*, not
*ex-dividend*: `RET − RETX` also picks up capital-gain distributions and returns
of capital.

Two identification paths, in order of preference:
1. **Preferred — a per-date distribution indicator.** "Did a distribution go ex"
   is a flag question, and a flag answers it directly. **Ask the seller two
   things, not one**: (a) is such a field available (on the daily file or on the
   distributions/events file) — paste the exact table + field; and (b) **which
   date is it keyed to?** We need the **ex-date** — the trading date on which the
   price becomes ex-distribution. **Declaration, record and payment dates are not
   substitutes**: they sit on the same distributions record, all look plausible,
   and keying on one of them drops a clean day while leaving the contaminated
   ex-day in the sample — worse than not screening, because the reported count
   then says a screen ran. If only a non-ex date is available, we do not use the
   field. Optional, not blocking.
2. **Fallback — compare `RET` with `RETX`**, both already in the item-2 ask.
   Usable, but it infers a flag from two rounded numbers, so it runs with a
   tolerance and an explicit undecidable band rather than a float equality test.

The paper reports how many observations were decided each way.

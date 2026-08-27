# Refraction — data requirements (WRDS request + free sources)

> **REVISED 2026-08-19 for Plan v2.2.** The TAQ conclusion below has been
> REVERSED: intraday data are now on the critical path. §4 of this file is
> superseded — see §4′. Everything about the CRSP window and Tier 2a stands.

Companion to P1's `TABLE-REQUEST.md`. Written 2026-08-19 from
`docs/MacroEvent_Chapter_Plan_v2_1_FINAL.md` §4/§6/§7 and
`refraction/frozen_config.yaml`; every date below is computed from the committed
sample frame, not eyeballed.

**Headline: refraction needs no new WRDS tables beyond your P1 list — but it
needs two of them over a wider window, and it promotes P1's optional Tier 2a to
load-bearing.** Both matter now, because a second pull is a second purchase.

---

## 1. The window problem — the same class of bug as P1's `pull_scope.json`

P1's t=0 is the announcement date; refraction's is also an announcement date, but
a *macro* one, and its panel runs from **2017-01-01** to **2026-06-30**
(`sample.announcements_*`). Two things push the daily requirement outside that
window in both directions:

| Direction | Driver | Lands at |
|---|---|---|
| **Backward** | trailing-window characteristics — Amihud, momentum, and the characteristics-implied prior all need a lookback before the FIRST announcement | ~**2016-01-01** (252 trading days before 2017-01-01) |
| **Forward** | spine 2's wedge fingerprint runs to **+60 days**, and the reversal portfolio holds a further **20** | ~**2026-10-27** |

**Against your committed P1 ranges, `crsp.dsf` at `2019-01-01 → 2026-08-31`
under-pulls refraction by three years at the front and two months at the back.**

The front is the expensive end. Announcement-regime betas are estimated on
pre-conversion announcement days, the earliest wave in frame is **2021-03-26**,
and Gate-0's G3 line wants a **median of 30 pre-period announcements** per stock.
At roughly 32 scheduled releases a year, a stock converting in early 2021 needs
its announcement history back through ~2018 just to clear G3 — and the
characteristics lookback sits behind that. Starting the daily file at 2019-01-01
would not error; it would quietly thin the pre-period for the earliest waves,
which is precisely the coupled quantity Gate-0's G2 window is measuring.

The back end is smaller but breaks a headline result rather than a diagnostic:
the +60d leg of the wedge fingerprint — 主证据 for H2 — silently truncates for
every announcement after ~2026-04.

**Ask for `crsp.dsf`, `crsp.dsi` and `crsp.dsedelist` at
`2016-01-01 → 2026-10-31`.** That is a superset of P1's need, so one pull serves
both chapters.

## 2. Tier 2a is optional for P1 and load-bearing for refraction

Your P1 list puts the holdings bundle — `crsp.holdings`, the fund header,
`crsp.portnomap` — in Tier 2a at ¥60, "all three or none."

For refraction that bundle is not a tier, it is the design. β_b^LOO — the
leave-one-out basket response — is built from pre-period holding weights, and
L = β_b^LOO − β_i is the refraction lever itself. Without holdings there is no
lever, no L_tilt, no γ decomposition, and Gate-0's G4 basket-distinctiveness line
cannot be computed at all.

**If a budget cut is coming, Tier 2a is the last thing to drop, not the first.**

## 3. What refraction needs, by tier

Table and field names are **carried over from your P1 request** and are not
independently verified here — they inherit P1's own two open questions (the
delisting table's current name, and adjusted vs unadjusted IBES summary). Where
refraction needs something P1's list does not cover, it is marked **TO CONFIRM**
rather than guessed.

### Tier R1 — Gate-0 minimum (nothing else is needed to reach GATE-PREREG)

| Library.Table | Freq | Date range | Why refraction needs it |
|---|---|---|---|
| `crsp.dsf` | daily | **2016-01-01 → 2026-10-31** | every core spine; `openprc` carries the whole daily timing decomposition (08:30 releases: close→open vs open→close; 14:00 FOMC: prevclose→close vs close→nextopen). Without the open, spine 1 loses its timing content |
| `crsp.dsi` | daily | **2016-01-01 → 2026-10-31** | market return for F_tilt's orthogonalization — the basket's non-market announcement response, the one component no market-compression story can generate |
| `crsp.dsedelist` | daily events | **2016-01-01 → 2026-10-31** | delisting returns folded in per CRSP rules (R2 module 1) |
| `crsp.stocknames` | reference | full history | permno ↔ CUSIP bridge; also the join that reconciles the free-path ConvExp against the WRDS one |
| `crsp.holdings` | quarterly reports | **2019-01-01 → 2026-08-31** | β_b^LOO. Starts earlier than P1's 2020 because basket weights must be **pre-conversion** for the earliest 2021 waves |
| fund header (`fund_hdr`/`fund_names`) | reference | full history | converting fund → `crsp_fundno` |
| `crsp.portnomap` | reference | full history | portfolio ↔ fund mapping |
| **Industry classification** — **TO CONFIRM** | reference/annual | 2016 → 2026 | `δ_{ind×a}` in SPEC-MAIN kills industry macro loadings, and `wave_industry` is a clustering dimension. Not in P1's 15 tables; needs a time-consistent SIC or GICS source named |

Free, no purchase, no WRDS: **SF Fed USMPD** (FOMC surprises), **FOMC/BLS release
calendars**. Both are R1a deliverables and are blocked on a web-capable session,
not on money.

### Tier R2 — main results (needed after Gate-0, not before)

| Library.Table | Freq | Date range | Why |
|---|---|---|---|
| `ibes.statsum_epsus` | monthly | **2015-01-01 → 2026-12-31** | analyst revisions for spine 2's fundamental-anchoring leg; `numest`/`stdev` are two of the five frozen heterogeneity items |
| `ibes.actu_epsus` | per announcement | **2015-01-01 → 2026-12-31** | realized EPS for SUE |
| `ibes.idsum` | reference | full history | IBES ↔ CUSIP |
| `comp.fundq` | quarterly | **2015-01-01 → 2026-12-31** | SUE construction and controls |
| `comp.funda` | annual | **2015-01-01 → 2026-12-31** | book-to-market for the characteristics-implied prior |
| `crsp.ccmxpf_lnkhdr` | reference | full history | Compustat ↔ CRSP link |
| `crsp.msf` | monthly | **2016-01-01 → 2026-10-31** | market cap deciles; shrout |

**Note the IBES/Compustat front dates.** Refraction's announcements start
2017-01-01 and SUE needs an 8-quarter lookback, so **2015**, not P1's 2018. The
forward date runs a quarter past the last announcement because the anchoring test
predicts *next-quarter* SUE.

### Tier R3 — enhancements, explicitly non-blocking

| Source | Status |
|---|---|
| Intraday TAQ | Plan §4: "**off the critical path by design**". Feeds H1′/H5′ only, which §7.5 calls "gated, non-load-bearing", behind R10's own pilot gate (30+30 × 20 days, ≥70% coverage) |
| Creation-basket composition (ETF Global / issuer files) | H4's arbitrage-conduit dose. `NEED_HUMAN: coverage`; a non-blocking bypath in the queue |
| ETF mechanics (shares outstanding, premium/discount) | H4 dose, enhancement layer |
| Russell constituents | robustness only — the 2021Q2–Q3 meme+Russell exclusion |

## 4′. TAQ — REVERSED by Plan v2.2: intraday is now load-bearing

**The v2.1 answer in this file is withdrawn.** It said refraction's TAQ need was weaker than
P1's because the plan routed intraday to non-load-bearing enhancement spines. Plan v2.2 moved
the headline question to **propagation architecture** — direction of price discovery,
adjustment half-life, premium/discount convergence — and none of those can be measured on
daily data. Intraday ETF **and** constituent quotes/trades are therefore required for spines
1–3, which are now the paper.

What this changes for the purchase:

| Item | v2.1 status | v2.2 status |
|---|---|---|
| Intraday ETF + constituent data | enhancement, off the critical path | **critical path**; Gate-0 line **G7** is blocking, failure routes to exit F |
| Creation-basket composition | non-blocking bypath (R9) | **load-bearing** — basket inclusion and weight are first-stage observables for G8 |
| ETF mechanics (creation/redemption, premium/discount) | "enhancement layer" | **load-bearing** — first-stage observables for G8 |
| CPI/NFP consensus | non-blocking | **further demoted** — generalization only, after FOMC works |

**The vendor substitute is admissible, with a condition.** Databento intraday BBO/trades (or
equivalent) may replace TAQ *if* it passes the coverage-and-agreement validation of Plan §4.1
condition 3: on a sampled overlap it must reproduce the reference source's spread and lead-lag
statistics within a tolerance registered in `frozen_config`
(`intraday_vendor_agreement_tol`, currently null and NEED_HUMAN). Cheaper data is fine;
unvalidated data is not, because spine 1's whole claim is a *timing* claim.

**Coverage, not price, is the binding risk.** G7's pass line is ≥70% usable coverage
including small caps. v1.1 of the plan rejected putting intraday on the critical path
precisely because of this risk; v2.2 accepts it deliberately and pre-declares exit F as the
fallback. When scoping the intraday purchase, scope it against **small-cap constituents on
FOMC dates**, not against the ETF tickers — the ETFs will be well covered and will tell you
nothing about whether the design survives.

## 5. Open items this list cannot close

1. **The characteristics set for the Vasicek prior is unregistered.** §4 says
   "characteristics-implied prior" and never names the characteristics.
   `build_betas.py` raises `NeedInfo` rather than degrading to a grand mean, so
   this blocks R2 the moment it runs. Size, book-to-market and momentum are the
   obvious candidates — but the *set is pre-registration content* and belongs in
   `frozen_config` before Gate-0, not after.
2. **The industry classification source is unnamed** (Tier R1, last row).
3. **CPI/NFP consensus** stays `NEED_HUMAN` — Bloomberg ECO at BU vs a
   WRDS-internal substitute. R1a item 3 answers whether the substitute exists.
   FOMC-only results are unblocked either way, so this gates nothing.

## 6. One-line summary for the purchase decision

Refraction adds **no new WRDS tables** to the P1 request — but as of Plan v2.2 it adds an entire **intraday source** (TAQ or a validated vendor) that P1 does not need at all. It asks for **three daily
tables over a wider window** (2016-01-01 → 2026-10-31), **IBES and Compustat from
2015 rather than 2018**, an **industry classification source to be named**, and it
**re-prices Tier 2a from optional to essential**. Widening a range inside the
same purchase window is cheap; discovering the gap after the window closes is a
second purchase.

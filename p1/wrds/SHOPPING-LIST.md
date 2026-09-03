# WRDS table shopping list — ¥20/table

_Seat C, 2026-08-19. Built from `p1/wrds/tables.yaml` + `p1/t3_spec/变量规格书.md`
+ plan §107 (control matching) and §120 (randomisation inference)._

**Tier 1 (must-have): 11 tables = ¥220.** Without any one of these, a named part
of the design cannot be computed.
**Tier 2 (recommended): 4 tables = ¥80.** Validation + refraction.
**Total: ¥300.** Tier 3 lists what NOT to buy, and why.

Evidence column: ✓ = the seller has already listed this table, so the name is
confirmed by someone with the account. ~ = seller listed an abbreviated form;
confirm the full name. ✗ = not yet listed; must be requested.

---

## Tier 1 — MUST HAVE (11 tables, ¥220)

| # | Table | Evidence | What dies without it |
|---|---|:--:|---|
| 1 | `crsp.stocknames` | ✓ | **The whole project.** CUSIP↔PERMNO is what fills `permno`, blank on all 6,377 rows today. Nothing joins without it. |
| 2 | `crsp.dsf` | ✓ | Spine two entirely — CAR paths, Amihud, 1−R², variance ratio, Hou-Moskowitz delay. The single biggest table. |
| 3 | `crsp.dsi` | ✓ | Daily market series for the daily spines. **Not** the spine-zero proxy — the `β_h` curve's β̂ is estimated against SPY, the same traded instrument as its intraday leg (v2.1h, `TABLE-REQUEST.md`). |
| 4 | `crsp.msf` | ✓ | ConvExp denominator (`shrout`), market-cap deciles, monthly reversal strategy. |
| 5 | **`crsp.dsedelist`** (DAILY) | ✗ | **Silently biases spine two.** A stock delisting inside a 120-day CAR window truncates the path. Spec §2-2 requires `dlret`, imputing −30% when missing. Without it → survivorship bias in the main evidence. |
| 6 | `comp.fundq` (Compustat NA Quarterly) | ✓ | Spine one: GNZ earnings decomposition, FERC, and the SUE time-series branch. |
| 7 | `comp.funda` (Compustat NA **Annual**) | ✗ | **Control group construction.** §107 matches controls on 规模 × **账面市值比** × 行业 × ETF ownership × Amihud. Book-to-market needs annual book equity. §120's randomisation inference uses the same matched funds. No controls → no DiD. |
| 8 | CCM link (`crsp.ccmxpf_lnkhdr`) | ✓ | Merges Compustat (gvkey) to CRSP (permno). Items 6 and 7 are unusable without it. |
| 9 | `ibes.statsum_epsus` | ~ | SUE-IBES (the decided primary), analyst dispersion, coverage count. |
| 10 | **`ibes.actu_epsus`** (actuals) | ~ | Reported actual EPS **and announcement dates** — announcement date is `t=0` for every event in spines one and two. |
| 11 | `ibes.idsum` | ✓ | IBES ticker ↔ CUSIP, to reach permno. |

## Tier 2 — RECOMMENDED (4 tables, ¥80)

**2a — the holdings bundle (3 tables, ¥60).** Buy all three or none:
`crsp.holdings` alone cannot be mapped to a fund without the other two.

| # | Table | Evidence | Buys you |
|---|---|:--:|---|
| 12 | `crsp.holdings` | ✓ | The CRSP-identifier twin of the free-path ConvExp |
| 13 | `crsp.fund_hdr` or `crsp.fund_names` | ✗ | Fund identity / ticker |
| 14 | `crsp.portnomap` | ✗ | Portfolio no. ↔ fund no. crosswalk |

**Why:** (a) runs the B5 reconciliation harness — validating the free EDGAR
ConvExp against CRSP is a real credibility item, and the harness is already
written; (b) refraction's R2 needs `holdings_weights`.
**Skip if** refraction stays parked and you accept the free-path ConvExp
without a CRSP cross-check.

**2b — monthly delisting (1 table, ¥20), independent of the bundle.**

| # | Table | Evidence | Buys you |
|---|---|:--:|---|
| 15 | `crsp.msedelist` (MONTHLY) | ✗ | Delisting on the monthly file — only for the Jegadeesh monthly reversal strategy (§7, 2-7). Skip if that variable is dropped |

## Tier 3 — DO NOT BUY

| Item | Why not |
|---|---|
| **Fama-French factors** | **Free** from Ken French's data library. Do not pay ¥20. Not required: spine zero uses a single traded proxy (SPY), the daily spines use `vwretd`. |
| TAQ / WRDS IID | Seller does not have it. Being replaced by Databento BBO. |
| `ibes.det_epsus` (detail) | `statsum` carries `numest` and `stdev`, which covers the 4-6 coverage/dispersion variables. Buy only if the exact "distinct analysts in a 90-day window" rule turns out to matter. |
| `crsp.ermport` | **Ask before deciding; default is DROP** (v2.1g/h). Only relevant to DGTW benchmark portfolios, and the headline is beta-adjusted market at every horizon — nothing headline depends on it. Whether it supports DGTW *robustness* is unverified here. **Do not buy it merely to keep a robustness label alive** (owner, 2026-08-28): if no daily series covering 2021–2026 exists, DGTW robustness is simply dropped, not manufactured. Three questions in the note below. |
| US Patents, DealScan, global ownership, word indices | Not in any P1 spine. |

---

## Note: the CAR benchmark — RESOLVED 2026-08-28 (v2.1f/g)

This list previously flagged a disagreement: T3 spec §2-2/2-3 specified **DGTW
characteristic adjustment**, while `p1/pipeline/outcomes_spine2.py` implements
**market-model adjustment**.

**Resolved, and not by convenience.** The primary benchmark for the headline
`β_h` curve is the **beta-adjusted market abnormal return, with no intercept**
(`AR^h = R^h − β̂_i R^h_m`), at every horizon — the proxy is a single traded
instrument (SPY) on both legs, and it is deliberately *not* called a "market
model", since no intercept is subtracted. The reason is structural: spec 2-3
builds DGTW from monthly characteristic portfolios with monthly value-weighted
returns, so **no DGTW value exists at a finer timestamp**. Subtracting a monthly
benchmark from a five-minute return removes a near-constant — `AR` comes out ≈
the raw return while the table still reads "characteristic-adjusted". Enforced in
code by `p1/pipeline/benchmark_policy.py`.

**DGTW robustness is confined to the frequency it is actually built at —
monthly.** ~~daily-or-longer~~ was this note's previous wording and it was one
assumption too far; see below.

Consequence for this list: **`crsp.ermport` is not required for the headline**,
and whether it is useful at all is now an open question rather than an assumption.

An earlier revision of this note said DGTW "remains the pre-specified robustness
benchmark for spine two's `[0,+120]` path and the daily horizons". **That claimed
something about data nobody had checked.** A daily DGTW path needs a **daily**
benchmark-portfolio return series; spec 2-3 supplies a **monthly** one, and this
container has no egress with which to confirm what `crsp.ermport` actually
contains. Meta-rule 1: no locator, not a fact.

**Ask at the window (three questions, before buying anything):**
1. Does a **daily** DGTW benchmark-portfolio return series exist on WRDS?
2. Which table/file supplies it — is `crsp.ermport` it, and at what frequency?
3. What is its coverage period (the Wermers distribution is documented in 2-3 as
   running through 2012; our sample is 2021–2026)?

If the answer to (1) is no, or (3) does not cover the sample, DGTW robustness is
confined to monthly-resolution horizons and `crsp.ermport` is **dropped**.
**Do not build or buy a daily DGTW series merely to preserve the robustness
label** (owner, 2026-08-28) — a robustness check that exists to be listed is not
a robustness check. Until then the daily `[0,+120]` path is **market-model
adjusted** (α̂ and β̂, dimensionally correct at daily — which is what
`p1/pipeline/outcomes_spine2.py` has always implemented) and must not be
described as characteristic-adjusted. `comp.funda` stays required regardless — it
is needed for **control matching**, not for DGTW.

---

## Names I cannot confirm

Per CLAUDE.md meta-rule 1, a table name written from model memory is a
hallucination. Items 5, 7, 13 and 14 are **not** on the seller's list, and items
9 and 10 appear only in abbreviated form. For those, ask the seller to supply the
exact name rather than accepting mine — the requests below describe *what is
needed* rather than asserting a name.


---

## Addenda 2026-08-19 — two corrections from the owner's questions

**1. Delisting: daily vs monthly.** `crsp.dsedelist` (daily) is Tier 1 — the CAR
path is daily, so `dlret` must land on the delisting day inside [0,+120].
`crsp.msedelist` (monthly) is Tier 2 and only matters for the monthly Jegadeesh
reversal strategy (2-7), which runs off `crsp.msf`.

**2. Does `statsum` already carry actuals and identifiers?** No — checked against
WRDS documentation. IBES on WRDS keeps three separate objects: Summary
(`statsum_epsus`, the monthly consensus snapshot), Detail (`det_epsus`, per-analyst
history) and **Actuals (`ibes.actu_epsus`)**. Reported actual EPS comes from the
actuals file.

This also **corrects this repo's own candidate list**: `tables.yaml` had
`actpsum_epsus` / `act_epsus`; WRDS documentation names it `actu_epsus`. All three
are now listed as candidates so `discover` can resolve whichever exists.

`idsum` stays on the list for a different reason: IBES keys on its own ticker plus
**historical** CUSIP, not permno or gvkey. A point-in-time CUSIP carried on a
statsum row is not the same as the mapping history, and this panel is 84%
deciles 1–5 — exactly where ticker/CUSIP changes are most common. At ¥20 the
asymmetry is decisive: the cost of being wrong is discovering a missing identifier
file partway through a one-day window.

**3. New flag — adjusted vs unadjusted.** `statsum_epsus` is split-**adjusted**;
`statsumu_epsus` is unadjusted. For SUE the unadjusted file is usually preferred,
because retroactive split adjustment introduces per-share rounding that can
dominate a small earnings surprise. Ask the seller which one they have; recorded
as a NEED_HUMAN in `tables.yaml`.

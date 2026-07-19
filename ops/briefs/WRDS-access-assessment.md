# WRDS access — need assessment (P1 + refraction), 2026-07-18

Owner's WRDS account lapsed. Decision: borrow an account (paid) vs. buy specific
data (Xianyu). This maps every WRDS-touching task across the portfolio and
recommends an approach.

## Scope: only P1 and refraction need WRDS. E2 does NOT.
E2 (RWA looping) runs on **on-chain** data (Dune SQL / Morpho & Aave subgraphs) —
zero WRDS. So one WRDS account/dataset serves **P1 + refraction**, and E2 is
unaffected either way.

## Every WRDS-dependent task (the footprint is the whole empirical backbone)
| Task | WRDS data needed | When |
|---|---|---|
| **P1-T2-wrds** (now) | CRSP MF holdings (`crsp.holdings`/`portnomap`/`fund_hdr`), `crsp.stocknames` (CUSIP→PERMNO), `crsp.msf` (shrout, prc, mcap decile) | now |
| **P1-T3** (outcomes) | TAQ **WRDS Intraday Indicators (IID)** — effective spreads; CRSP **daily** (DSF); IBES SUE; possibly Compustat (GNZ earnings decomposition) | wk 4–6 |
| **P1-T4** replication | CRSP daily | after T2 |
| **P1-T5** main | conv_exposure + CRSP **daily** + TAQ **IID** | after T3 |
| **P1-T6 / T7** | consume cached panels — **no fresh WRDS** if pulls complete | later |
| **Refraction R2** | CRSP **daily returns** (with open prices for overnight/intraday split) + frozen P1 files (conv_exposure, holdings_weights, ibes_sue, events_merged) | after P1-T2 |
| **Refraction R10** | TAQ intraday ±90 min around announcements (non-blocking bypass) | optional |

Non-WRDS (don't factor in): USMPD is a **free** SF Fed download; CPI/NFP consensus
is a *separate* Bloomberg-ECO/license question (already a standing NEED_HUMAN).

**Conclusion on "later stages":** yes — WRDS is needed continuously from P1-T2
through T5 and refraction R2/R10. It is **not** a one-shot need; it is the spine
of both papers' empirics. But it collapses to a small set of **distinct data
pulls** that can all be taken in one sitting and cached.

## The five raw pulls that cover everything (take all in one window)
1. CRSP MF holdings for the **131 converting funds**, pre-conversion report periods (+ `fund_hdr`, `portnomap`) — well-bounded.
2. `crsp.stocknames` full CUSIP↔PERMNO reference — small.
3. `crsp.msf` (monthly) 2019–2026, full universe — shrout/prc/decile.
4. `crsp.dsf` (**daily**) for the treated+control universe over event windows — the big one.
5. TAQ **IID** (daily spread metrics) + IBES SUE for the universe/windows.

Everything downstream (conv_exposure, outcomes_panel, returns_ann, panel_ann) is
**derived** from these five and cached to disk — so once pulled, no re-access.

## How long do you need the account?
NOT continuous. The live-connection time is **hours**; the risk is iteration
(fund→PERMNO mapping, report-period alignment, look-ahead/leave-one-out checks).
Two patterns:
- **Naive:** keep the account across P1-T2→T5 + R2 debugging ≈ **3–6 weeks** on/off.
- **Recommended (sprint):** pre-write all pull scripts OFFLINE (they only need the
  connection at runtime), then borrow for **one concentrated block ≈ 3–7 days**,
  execute pulls 1–5 back-to-back, land every raw file immutable with lineage,
  release. T5/T6/T7 and refraction R3+ then run on the cache. I can pre-write the
  T3/T4/R2 pull scripts now (the T2 scaffold already exists), which is what makes
  the 3–7 day window realistic.

## If buying data instead — size
The universe is **endogenous** (defined by which stocks the converting funds held,
i.e. T2's output), so a fixed shopping list can't be fully specified up front.
Rough sizes if scoped to universe+windows:
- MF holdings (131 funds): < 50 MB · stocknames: ~tens of MB · MSF 2019–26: ~100–300 MB
- CRSP **daily** (universe×windows): ~1–3 GB (dominant) · TAQ IID: ~few hundred MB–1 GB · IBES SUE: ~few hundred MB
- **Total ≈ 2–5 GB** scoped; ~5–10 GB if you grab full-universe daily for safety.
(Raw TAQ is terabytes — you do **not** want that; you need the WRDS-computed IID,
which is a WRDS value-add product that's awkward to buy piecemeal.)

## Recommendation: BORROW (one sprint), don't piece-buy
Borrowing is easier and safer here:
1. **Iterative, multi-table, universe-endogenous** pipeline — you can't hand a
   seller a frozen file list; you'll discover you need one more column mid-build.
2. **Meta-rule 1** (the project's core discipline): every number must carry a WRDS
   table+query locator. An account preserves that; purchased CSVs of unknown
   vintage/provenance can fail the standard and can't be re-queried.
3. **One account covers both P1 and refraction** (shared frozen files + shared
   CRSP/TAQ). TAQ IID in particular is a WRDS product, not a loose dataset.
4. Cost is bounded by making it a **3–7 day sprint**, not a subscription.

**When buying is acceptable:** if you only want to unblock **T2 right now** and
defer the rest — a targeted purchase of (MF holdings for the 131 funds +
stocknames + MSF snapshot, < 400 MB, fully specifiable) gets conv_exposure built
and clears kill-switch gate 2. But you'll need CRSP-daily + TAQ + IBES for
T3/T5/R2 regardless, so plan to borrow for that phase.

## Action to compress the rental (offer)
Before you secure the account, seat C can pre-write the offline pull scripts for
P1-T3/T4 and refraction-R2 (like the T2 `holdings_pipeline.py` scaffold), each
landing raw immutable + lineage and refusing to invent table/column names. Then
the borrowed window is pure execution → ~3–5 days, one account, both papers.

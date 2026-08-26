# WRDS table shopping list — ¥20/table

_Seat C, 2026-08-19. Built from `p1/wrds/tables.yaml` + `p1/t3_spec/变量规格书.md`
+ plan §107 (control matching) and §120 (randomisation inference)._

**Tier 1 (must-have): 11 tables = ¥220.** Without any one of these, a named part
of the design cannot be computed.
**Tier 2 (recommended): 3 tables = ¥60.** Validation + refraction.
**Total: ¥280.** Tier 3 lists what NOT to buy, and why.

Evidence column: ✓ = the seller has already listed this table, so the name is
confirmed by someone with the account. ~ = seller listed an abbreviated form;
confirm the full name. ✗ = not yet listed; must be requested.

---

## Tier 1 — MUST HAVE (11 tables, ¥220)

| # | Table | Evidence | What dies without it |
|---|---|:--:|---|
| 1 | `crsp.stocknames` | ✓ | **The whole project.** CUSIP↔PERMNO is what fills `permno`, blank on all 6,377 rows today. Nothing joins without it. |
| 2 | `crsp.dsf` | ✓ | Spine two entirely — CAR paths, Amihud, 1−R², variance ratio, Hou-Moskowitz delay. The single biggest table. |
| 3 | `crsp.dsi` | ✓ | Market-model benchmark (`vwretd`). Without it there are no abnormal returns. |
| 4 | `crsp.msf` | ✓ | ConvExp denominator (`shrout`), market-cap deciles, monthly reversal strategy. |
| 5 | **CRSP delisting returns** | ✗ | **Silently biases spine two.** A stock delisting inside a 120-day CAR window truncates the path. Spec §2-2 requires `dlret`, imputing −30% when missing. Without it → survivorship bias in the main evidence. |
| 6 | `comp.fundq` (Compustat NA Quarterly) | ✓ | Spine one: GNZ earnings decomposition, FERC, and the SUE time-series branch. |
| 7 | `comp.funda` (Compustat NA **Annual**) | ✗ | **Control group construction.** §107 matches controls on 规模 × **账面市值比** × 行业 × ETF ownership × Amihud. Book-to-market needs annual book equity. §120's randomisation inference uses the same matched funds. No controls → no DiD. |
| 8 | CCM link (`crsp.ccmxpf_lnkhdr`) | ✓ | Merges Compustat (gvkey) to CRSP (permno). Items 6 and 7 are unusable without it. |
| 9 | `ibes.statsum_epsus` | ~ | SUE-IBES (the decided primary), analyst dispersion, coverage count. |
| 10 | `ibes.actpsum_epsus` or `ibes.act_epsus` | ~ | Reported actual EPS **and announcement dates** — announcement date is `t=0` for every event in spines one and two. |
| 11 | `ibes.idsum` | ✓ | IBES ticker ↔ CUSIP, to reach permno. |

## Tier 2 — RECOMMENDED (3 tables, ¥60)

These three are a **bundle** — `crsp.holdings` alone is nearly useless without
the other two, because you cannot map a holdings row to a fund.

| # | Table | Evidence | Buys you |
|---|---|:--:|---|
| 12 | `crsp.holdings` | ✓ | The CRSP-identifier twin of the free-path ConvExp |
| 13 | `crsp.fund_hdr` or `crsp.fund_names` | ✗ | Fund identity / ticker |
| 14 | `crsp.portnomap` | ✗ | Portfolio no. ↔ fund no. crosswalk |

**Why worth ¥60:** (a) it runs the B5 reconciliation harness — validating the
free EDGAR ConvExp against CRSP is a real credibility item for the paper, and the
harness is already written; (b) refraction's R2 needs `holdings_weights`.

**Skip if** you have decided refraction is parked and will accept the free-path
ConvExp without a CRSP cross-check.

## Tier 3 — DO NOT BUY

| Item | Why not |
|---|---|
| **Fama-French factors** | **Free** from Ken French's data library. Do not pay ¥20. Not required by the spec — the market model uses `vwretd` from `crsp.dsi`. |
| TAQ / WRDS IID | Seller does not have it. Being replaced by Databento BBO. |
| `ibes.det_epsus` (detail) | `statsum` carries `numest` and `stdev`, which covers the 4-6 coverage/dispersion variables. Buy only if the exact "distinct analysts in a 90-day window" rule turns out to matter. |
| `crsp.ermport` | Only needed for DGTW benchmark portfolios. We are using market-model adjustment (see below), so this is dead weight. |
| US Patents, DealScan, global ownership, word indices | Not in any P1 spine. |

---

## Note: a spec change this list implies

The T3 spec §2-2/2-3 specifies **DGTW characteristic adjustment** for the CAR
benchmark, but `p1/pipeline/outcomes_spine2.py` implements **market-model
adjustment**. They disagree.

Resolving it toward the market model (which the code already does) removes
`crsp.ermport` from the ask and eliminates the inconsistency. `comp.funda` stays
required regardless — it is needed for **control matching**, not for DGTW.

---

## Names I cannot confirm

Per CLAUDE.md meta-rule 1, a table name written from model memory is a
hallucination. Items 5, 7, 13 and 14 are **not** on the seller's list, and items
9 and 10 appear only in abbreviated form. For those, ask the seller to supply the
exact name rather than accepting mine — the requests below describe *what is
needed* rather than asserting a name.

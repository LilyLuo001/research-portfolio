# P1-T2 free-path Gate-2 assessment (seat C, 2026-07-18)

Read of the box's `gate2_human_review_manifest.json`. Bottom line: the pipeline
did its job. The two apparent "gaps" are (1) a **correct sample finding**, not
missing data, and (2) the **expected free-path denominator gap**, cheaply fixable
without WRDS. Coverage is already enough to read the kill-switch once two numbers
are in hand.

## The 31 "need_human" funds are CORRECT exclusions, not missing data
All 31 carry reason `no_share_denominated_equity_in_matched_nport`: the right
series **was** located, and it held **bonds / commodities / derivatives, not
common stock** (JPMorgan Inflation Managed Bond, Neuberger Commodity Strategy, …).
A fixed-income/commodity fund's conversion has **zero equity treatment by
construction** — ConvExp (shares held / shares outstanding of a *stock*) is
undefined for it. Excluding them is mechanically right, and it *validates* the
pipeline: it refused to fabricate stock exposure for a bond fund (meta-rule 4).

Cross-check: `events_merged` asset_class was ~33 fixed_income + several
commodity/derivative "other" → **31 non-equity is exactly what we'd expect.** So
the equity event study runs on the **~100 equity-fund conversions**; that's a
sample-definition fact for the paper (footnote; the 31 could seed a separate
fixed-income sub-analysis), **not a failure**. (The "13" in the feedback is a
typo for 31 = 131 − 100 resolved.)

## The ~5,929 flagged stock cells are missing DENOMINATORS, not missing treatment
Breakdown: `ticker_not_in_sec_map` 4914 + `no_xbrl_shares_outstanding` 660 +
`no_ticker` 337 + `conv_exp>1` 18. **~5,600 of these are the shares-outstanding
lookup failing**, because the free route (SEC XBRL `dei:EntityCommonStock-
SharesOutstanding` via `company_tickers.json`) only covers **US-domestic SEC
registrants that tag that field**. It misses:
- **foreign stocks / ADRs** (international funds hold many — and CRSP wouldn't
  cover most of these either, so they'd leave the US universe anyway),
- **share-class tickers** (BRK.B-style), recent listings, and issuers that don't
  XBRL-tag shares outstanding.

The key point: these dropped because we lacked a **denominator**, not because we
lacked the **holding**. ConvExp still computed for **2,241 distinct US stocks /
6,377 rows**, and the DFA anchor wave is well-populated (**1,546 rows, 24.2%**) —
a healthy treatment universe for a feasibility read. Half the *cells* dropped,
but the surviving half is the US-listed core the study actually keys on.

The 18 `conv_exp>1` (AMRX, CIA, FOX/FOXA, RFL, TRIP) are **garbage XBRL
denominators** (FOXA shares_out=1, AMRX=1000) — the pipeline **correctly
quarantined** them instead of emitting a >100% exposure. Six tickers, trivially
patchable.

## Is this enough to clear the kill-switch? Need two numbers
Gate 2 asks: **how many stocks are meaningfully treated — ConvExp ≥0.5% and
≥1%** (pooled, and on the DFA anchor)? The manifest has them; they weren't in the
pasted summary. With 2,241 stocks and a dense anchor, coverage is almost
certainly sufficient to **read** the gate — but the go/no-go is those counts, not
the drop counts. Please push the manifest (or paste ConvExp≥0.5% / ≥1% for pooled
+ W002) and I'll give the gate verdict.

## Cheap fix that recovers most of the 5,600 — still free, no WRDS
Add a **yfinance / Stooq `sharesOutstanding` fallback** for any ticker that fails
the SEC-XBRL route. Yahoo/Stooq cover foreign ADRs, share classes, and issuers
SEC-XBRL misses — likely recovering a large fraction of the 5,600 and fixing the
6 garbage tickers. This is a bounded second free pass (`build_shares_fallback.py`)
that re-computes ConvExp for the flagged cells only. Recommended **before** the
gate decision so the treated-stock counts aren't understated by a denominator
artifact. A CRSP `shrout` pass would close the last gap, but only for the final
publishable run — not for the gate.

## Recommendation
1. **Accept** the 31-fund exclusion (equity study = ~100 funds; document it).
2. **Don't** read the 5,929 as lost data — they're denominator gaps; run the free
   yfinance fallback to lift coverage.
3. **Push the manifest / paste the ≥0.5% & ≥1% counts** so seat C can call the
   kill-switch. Everything else is on track.

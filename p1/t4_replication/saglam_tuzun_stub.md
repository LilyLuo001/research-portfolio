# A3 — Saglam–Tuzun (2025) FEDS Note

_P1 / seat C / updated 2026-09-03. Prepared for T4 replication._
_Source: official Federal Reserve HTML and accessible-data page, plus the SEC_
_filing cited by the note. No model-memory fill._

---

## Citation

Saglam, M.; Tuzun, T. (2025). "Implications of Growth in ETFs: Evidence from
Mutual Fund to ETF Conversions." *FEDS Notes*, Federal Reserve Board, November 19, 2025.

DOI: [10.17016/2380-7172.3909](https://doi.org/10.17016/2380-7172.3909)

Full text URL:
https://www.federalreserve.gov/econres/notes/feds-notes/implications-of-growth-in-etfs-evidence-from-mutual-fund-to-etf-conversions-20251119.html

Author page (Tuzun): https://www.federalreserve.gov/econres/tugkan-tuzun.htm

**A3 status:** the official note is available and has been transcribed. It is an
HTML FEDS Note, not a 125-event replication package. The note reports a
descriptive aggregate of 125 mutual funds converted by end-2024 but publishes
only the four June 11, 2021 Dimensional conversions used in its empirical
analysis. See `p1/universe_v2/output/event_universe_reconciliation_report.md`.

---

## What is known from the official note (source-locatable)

Source: WebSearch result from federalreserve.gov FEDS Notes index, accessed
2026-08-18. URL: https://www.federalreserve.gov/econres/notes/feds-notes/implications-of-growth-in-etfs-evidence-from-mutual-fund-to-etf-conversions-20251119.html

| Field | Value |
|---|---|
| Sample period | 2019 (SEC rule streamlining ETF creation) through end 2024 |
| N conversions | 125 mutual funds converted to ETFs as of end 2024 |
| AUM converted | ~$80 billion total; ~$1.6B per month on average |
| Key event | June 2021: one large asset manager converted several equity mutual funds, $30B+ of U.S. equities in a single day (DFA) |
| Outcomes studied | Equity market volatility; market liquidity |
| Direction of effects | Conversions improve market quality: ↑ liquidity, ↓ volatility |
| Empirical conversion events | Four predecessor funds, one date (2021-06-11), all Dimensional; Table 1 |
| Impacted stocks | 2,449 in Table 2 (2,448 with volatility available) |
| Identification | Cross-sectional change regression around the one conversion wave; treatment is continuous change in ETF ownership |
| Windows | March 2021 to September 2021 for ownership and outcome changes |
| Controls | Percentage changes in market capitalization and trading volume; alternative cross-controls noted |
| Volatility result | ETF-ownership coefficient -10.39 baseline; -7.96 with both controls |
| Effective-spread result | ETF-ownership coefficient -0.06 baseline; -0.07 with controls |

---

## T4 transcription status

T4's task is a side-by-side comparison: their coefficient estimates vs. ours.
The owner must open the PDF and paste the following for each table they report:

### Table 1 (expected: summary statistics or event sample)
- [x] N impacted stocks: 2,449 (2,448 with volatility)
- [x] Exact event date: 2021-06-11
- [x] The note uses the same four-fund Dimensional wave identified in P1
- [x] Table 1 predecessor/successor names and fund assets transcribed in the
  source-universe reconciliation
- [ ] No separate treated/control stock counts are reported; treatment is a
  continuous ownership change among impacted stocks

### Main results table (expected: DiD regression or similar)
- [x] Effective-spread coefficients: -0.06, -0.07, -0.07; reported robust SEs
  0.02, 0.02, 0.02
- [x] Volatility coefficients: -10.39, -8.66, -7.96; reported robust SEs 2.89,
  2.89, 2.77
- [x] No fixed effects are reported; these are cross-sectional change
  regressions
- [x] Heteroskedasticity-adjusted standard errors; no clustering reported
- [x] HTML locators: Tables 3 and 4

### Variable definitions (from the paper's data section)
- [x] Liquidity: change in TAQ daily trade-weighted effective spread, March to
  September 2021
- [x] Volatility: percentage change in monthly standard deviation of daily
  returns, March to September 2021
- [x] Treatment: continuous change in ETF ownership caused by the four-fund DFA
  conversion wave; no other conversion events enter the empirical design
- [x] Sample: stocks held by the converting mutual funds; no non-converted-fund
  control group is described

### Robustness tables
- [ ] Do they report placebo tests? If so, what is the placebo coefficient and p-value?
- [ ] Do they report the results separately for the June 2021 DFA event alone? If so, include those.

---

## Relevance to our paper

Saglam–Tuzun (2025) is our primary comparator for market-quality results (spine four).
Our design is stronger on identification (conversion date is the treatment, not
fund-level AUM measure) but theirs is the prior work; our T4 replication task is:

1. **Replicate their liquidity/volatility result** using our own data to establish
   credibility ("we can reproduce their finding").
2. **Stack our information-side results** on top to show the information channel
   (spine one: FERC/IPT; spine two: CAR fingerprint) that they did not study.

If our replication of their result (step 1) fails, we must say so openly and
investigate the discrepancy before proceeding — not adjust to match.

---

## Related earlier work (Saglam–Tuzun–Wermers)

A related working paper: Saglam, M.; Tuzun, T.; Wermers, R. "Do ETFs Increase
Liquidity?" SSRN 3142081 / EconStor:
https://www.econstor.eu/bitstream/10419/232547/1/175260993X.pdf

This is an earlier paper on ETF liquidity. The 2025 FEDS Note is specifically
about mutual fund → ETF *conversions*, not general ETF ownership effects.

---

## What unblocks the rest of T4

The source transcription is complete. T4 may resume only after the current
event-universe pause is released; at that point the implementer should reproduce
the four-fund 2021-06-11 benchmark on CRSP/TAQ and compare columns without
specification searching.

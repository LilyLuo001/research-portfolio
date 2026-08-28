# A3 — Saglam–Tuzun (2025) FEDS Note

_P1 / seat C / 2026-08-18. Prepared for T4 coefficient-transcription task._
_Source: web-search extractions with URL locators. PDF is behind federalreserve.gov,_
_which is blocked by the container's egress proxy. Everything below is from WebSearch_
_results (confirmed URLs, no model-memory fill). Cells marked [NEED_PDF] require_
_the owner to open the paper and paste the value here._

---

## Citation

Saglam, M.; Tuzun, T. (2025). "Implications of Growth in ETFs: Evidence from
Mutual Fund to ETF Conversions." *FEDS Notes*, Federal Reserve Board, November 19, 2025.

DOI: [10.17016/2380-7172.3909](https://doi.org/10.17016/2380-7172.3909)

Full text URL (requires browser with unrestricted egress):
https://www.federalreserve.gov/econres/notes/feds-notes/implications-of-growth-in-etfs-evidence-from-mutual-fund-to-etf-conversions-20251119.html

Author page (Tuzun): https://www.federalreserve.gov/econres/tugkan-tuzun.htm

**Note on A3 status**: the FEDS Note PDF is not behind a paywall — it is a
free Fed Note — but the container's egress proxy blocks federalreserve.gov
(confirmed: HTTP 000 via curl, WebFetch EGRESS_BLOCKED). The owner can access it
in any browser, download the PDF, and paste the coefficient tables here.

---

## What is known from WebSearch (source-locatable)

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
| Identification | `[NEED_PDF: DiD specification — did they use a staggered DiD? Event-study? What is the treatment variable? Is it binary (converted/not) or continuous (AUM converted)?]` |
| Controls | `[NEED_PDF: which control variables for the liquidity and volatility regressions?]` |

---

## T4 transcription checklist (what we need from the PDF)

T4's task is a side-by-side comparison: their coefficient estimates vs. ours.
The owner must open the PDF and paste the following for each table they report:

### Table 1 (expected: summary statistics or event sample)
- [ ] N stocks in treated group
- [ ] N stocks in control group
- [ ] Pre-conversion mean liquidity measure and volatility measure
- [ ] Post-conversion mean liquidity measure and volatility measure
- [ ] Exact date range of the June 2021 DFA event (which date was the effective date?)
- [ ] Whether the authors use the same 2021-06 event we identify in events_merged.csv

### Main results table (expected: DiD regression or similar)
- [ ] Coefficient on the treatment indicator for **liquidity outcome** (value, SE, t-stat, significance stars)
- [ ] Coefficient on the treatment indicator for **volatility outcome** (value, SE, t-stat, significance stars)
- [ ] Fixed effects specification (stock FE? time FE? industry-time?)
- [ ] Clustering (stock? stock × time? some other cluster?)
- [ ] Page number of the main results table (for transcription locator)

### Variable definitions (from the paper's data section)
- [ ] Exact liquidity measure: effective spread? Amihud? Bid-ask? Which frequency (daily/monthly)?
- [ ] Exact volatility measure: realized volatility? Implied? Intraday? Daily variance?
- [ ] Treatment variable construction: which conversion events are included beyond DFA 2021?
- [ ] Control group: are non-converted mutual funds the control? Same asset class only?

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

1. Owner downloads the PDF from the URL above
2. Fills in all `[NEED_PDF]` cells in this file
3. Commits the updated file
4. T4 implementer runs our pipeline on CRSP data and compares column by column

The T4 pipeline half (our regressions) is still blocked on WRDS data. This
document unblocks the T4 *transcription* half when the PDF is in hand.

# P2 — 2023 Nasdaq-100 special rebalance: public, outcome-blind evidence

Run date: 2026-09-20. This package contains no price, return, quote, earnings, EPS, forecast, or response data. It did not read SCC/WRDS material, purchase data, or change credentials/certification.

## Bottom line

The public record verifies the key institutional sequence: Nasdaq set July 3 as the pricing/TSO reference date, scheduled index-share announcements and a pro-forma release for July 14, and made the special rebalance effective before the July 24 open. Nasdaq also states that the special rebalance itself added and removed no securities. [Nasdaq's dated announcement](https://indexes.nasdaqomx.com/docs/NDX_SpecialRebalance_2023.pdf) is the primary evidence.

The same period contains a separate membership event: TTD replaced ATVI before the July 17 open, and Nasdaq expressly said that replacement was independent of the July 24 special rebalance. [Nasdaq's TTD/ATVI announcement](https://ir.nasdaq.com/node/106501) is primary evidence. A main H3 member set must therefore not call the entire July interval constant.

The rule is supported by the January 31, 2023 QQQ prospectus filed at SEC: it describes the quarterly two-stage procedure, with a 20% Stage-1 issuer cap when triggered and a Stage-2 48% test resetting the relevant collective weight to 40%. [SEC prospectus](https://www.sec.gov/Archives/edgar/data/1067839/000119312523017732/d365144d485bpos.htm). This is contemporaneous issuer/SEC disclosure, not a backwards inference from a current methodology page.

## Public weight evidence

`P2_SUPPORT_TABLE.csv` preserves nine security-level old/new weight pairs (the seven affected issuers, with Alphabet at security-class level, plus Broadcom) from a public table that attributes its figures to Nasdaq. That table reports: AAPL 12.2→11.6, MSFT 12.8→9.8, AMZN 6.7→5.1, NVDA 7.2→4.2, META 4.3→3.5, TSLA 4.2→3.2, AVGO 2.5→3.1, GOOGL 3.7→2.7, and GOOG 3.6→2.7 percent. [Public table, attributed to Nasdaq](https://www.ii.co.uk/analysis-commentary/how-nasdaq-100-special-rebalance-has-impacted-big-seven-tech-stocks-ii528666).

These are usable as a clearly labeled public **support table**, not as the authoritative 7/14 pro-forma file. The table does not specify the old-weight observation timestamp, and the original 7/14 Nasdaq constituent/index-share pro-forma file was not found at a reproducible public endpoint. Thus, it is not valid to construct a definitive security-level `oldCF → new` treatment vector from this package alone.

Nasdaq's later retrospective describes the largest six as reduced and reports approximately 12% one-way turnover; Invesco's July commentary likewise records seven reduced companies and approximately 12% redistributed to the other 93. [Nasdaq retrospective](https://www.nasdaq.com/articles/all-about-index-concentration), [Invesco commentary](https://www.invescomutualfund.com/docs/default-source/default-document-library/nasdaq-100-commentary---july-2023.pdf?sfvrsn=d53291c2_0). These corroborate direction and scale, but do not replace a dated constituent file.

## Actual tracking-fund implementation evidence

QQQ’s contemporaneous prospectus says the Trust holds all NDX stocks and adjusts its Portfolio Deposit to conform to the index’s identity and relative weights. That is an issuer/SEC statement of the replication mechanism, not a trade blotter. The public SEC N-PORT snapshots then show actual QQQ holdings: the 2023-06-30 report lists ATVI (10,529,573 shares; 0.440386151446% of net assets), while the 2023-09-30 report lists TTD (7,627,965 shares; 0.302175764966%); each filing has 101 named investment records. [Pre-event N-PORT](https://www.sec.gov/Archives/edgar/data/1067839/000175272423198395/xslFormNPORT-P_X01/primary_doc.xml), [post-event N-PORT](https://www.sec.gov/Archives/edgar/data/1067839/000175272423269960/xslFormNPORT-P_X01/primary_doc.xml).

This establishes an actual-fund, public pre/post membership-and-holding snapshot consistent with tracking implementation. It does **not** establish the precise date, size, or venue of QQQ’s July 17/24 trades: the reports are quarter-end snapshots (June 30 and September 30), with the post snapshot 68 days after the special rebalance. No public QQQ holdings file dated July 24 or execution record was located.

## What H3 may and may not claim now

Permissible now: a documented institutional case; a TTD/ATVI-separated member treatment; and sensitivity/support analyses using the nine openly reported weights, always labeled secondary and not reference-date matched.

Blocked now: an authoritative all-security `Z_ij` based on exact 7/14 pro-forma index shares and a verified same-day tracking-fund weight vector. Recovering either requires an archived/public original Nasdaq pro-forma file or an appropriately licensed historical index constituent source; neither should be substituted with estimates.

## Audit notes

`SOURCE_MANIFEST.json` records URLs, access date, source grade, the SCC public-evidence archive, and SHA-256 values. Six retrieved source files were verified after transfer to SCC and are not duplicated in Git. `verify_p2.py` checks JSON, CSV shape/content boundaries, archived-source receipts, and row counts.

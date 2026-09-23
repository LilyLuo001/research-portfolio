# Earnings clock sources and remaining uncertainty

The fixed 48-event manifest was generated without reading returns. Dates and candidate release minutes come from the existing SCC I/B/E/S actuals metadata projection (`anndats`, `anntims`). Duplicate `ANN`/`QTR` rows at the same issuer/date/minute were collapsed into one economic release. No EPS value was read.

Issuer-owned archives and filed exhibits verify that the selected dates are result releases rather than call notices or unrelated corporate events. Examples spanning issuers and years include:

- Apple, [first-quarter 2023 results](https://www.apple.com/newsroom/2023/02/apple-reports-first-quarter-results/) and [fourth-quarter 2024 results](https://www.apple.com/newsroom/2024/10/apple-reports-fourth-quarter-results/);
- Eli Lilly, [quarterly-results archive](https://investor.lilly.com/financial-information/quarterly-results);
- CVS Health, [fourth-quarter/full-year 2023 results](https://investors.cvshealth.com/news/news-details/2024/CVS-HEALTH-REPORTS-FOURTH-QUARTER-AND-FULL-YEAR-2023-RESULTS/default.aspx);
- Cummins, [February 2023 filed release](https://investor.cummins.com/sec-filings/all-sec-filings/content/0000026172-23-000002/0000026172-23-000002.pdf) and [May 2024 filed release](https://investor.cummins.com/sec-filings/all-sec-filings/content/0000026172-24-000019/cmi2024q18-kex99.htm);
- eBay, [fourth-quarter 2022 results](https://investors.ebayinc.com/investor-news/press-release-details/2023/eBay-Inc.-Reports-Better-Than-Expected-Fourth-Quarter-2022-Results/default.aspx);
- News Corp, [third-quarter fiscal-2023 results](https://newscorp.com/2023/05/11/news-corp-reports-third-quarter-results-for-fiscal-2023/).

These public pages generally establish the economic date and release identity, but their rendered archives do not consistently expose a trustworthy first-public timestamp. Conference-call times are later events and are not substituted for the result-release clock. Accordingly, the current minute anchors remain labelled `EXISTING_SCC_IBES_ACTUALS_METADATA_CANDIDATE / NOT_YET_VERIFIED`, and the test cannot support sub-minute ordering claims. The minute anchor is nevertheless fixed before the new quote responses are inspected, so it can support the planned coarse response paths and a candidate-clock conditional-prediction test with this limitation stated explicitly.

The NYSE calendar source for fifth-prior-session controls is the already documented [ICE/NYSE 2023–2025 holiday and early-close calendar](https://ir.theice.com/press/news-details/2022/NYSE-Group-Announces-2023-2024-and-2025-Holiday-and-Early-Closings-Calendar/default.aspx). Early closes remain sessions; full-day closures do not.

# Direct public-clock cross-check — 2026-09-15

**Six of eight checked PRE announcements now have interpretable public timestamps: five match the saved source clock to the displayed minute, one differs by one minute. Two remain date-only. Gate 1 is not passed.** This is a small, nonrandom documentary validation, not the full 852-association session or endpoint census.

## Actual comparison

| Security | PRE announcement date | Public timestamp interpreted in Eastern time | Comparison to saved source |
|---|---|---|---|
| REGI | 2019-03-05 | 16:05 ET | Displayed minute matches |
| MRK | 2020-02-05 | NewsArticle 06:47 −05:00 | Public timestamp is 60 seconds later |
| MRK | 2020-07-31 | NewsArticle 06:45 −04:00 | Displayed minute matches |
| REI | 2021-05-10 | 17:47 EDT | Displayed minute matches |
| AAPL | 2021-04-28 | Date only on checked source | UNKNOWN |
| AAPL | 2022-01-27 | Date only on checked source | UNKNOWN |
| ORCL | 2021-09-13 | 16:05 −04:00 | Displayed minute matches |
| ORCL | 2021-12-09 | 16:05 −05:00 | Displayed minute matches |

Sources are issuer-originated publications, not a return-based timestamp selection:

- [REGI original GlobeNewswire release](https://www.globenewswire.com/news-release/2019/03/05/1748437/21924/en/Renewable-Energy-Group-Reports-Fourth-Quarter-and-Full-Year-2018-Financial-Results.html). The direct HTTP attempt timed out; timestamp-only projection from the subsequent page retrieval succeeded. The failure was preserved, not erased.
- Merck issuer pages for [2020-02-05](https://www.merck.com/news/merck-announces-fourth-quarter-and-full-year-2019-financial-results/) and [2020-07-31](https://www.merck.com/news/merck-announces-second-quarter-2020-financial-results/).
- [Ring Energy issuer release](https://www.ringenergy.com/news-presentations-events/press-releases/detail/7/ring-energy-announces-first-quarter-2021-results), with visible EDT publication label.
- Apple checked pages for [2021-04-28](https://www.apple.com/li/newsroom/2021/04/apple-reports-second-quarter-results/) and [2022-01-27](https://www.apple.com/newsroom/2022/01/apple-reports-first-quarter-results/). A date-only JSON-LD string ending in `Z` was rejected as a timestamp. It must not become midnight UTC. This does not establish that every other Apple or wire source lacks a time.
- Oracle original PR Newswire releases for [2021-09-13](https://www.prnewswire.com/news-releases/oracle-announces-fiscal-2022-first-quarter-financial-results-301375644.html) and [2021-12-09](https://www.prnewswire.com/news-releases/oracle-announces-fiscal-2022-second-quarter-financial-results-301441790.html).

## Concrete parser defect prevented

Merck's page has two `datePublished` nodes with the same local clock but different offsets. The `WebPage` node uses `+00:00`; the `NewsArticle` node uses the season-appropriate `−05:00` or `−04:00`. A flattened metadata parser loses those object roles and could create a four-/five-hour error. The new probe retains JSON-LD path and object type. The comparison uses the article-publication node for this documentary question, while preserving the page node and recording the distinction. It does not rewrite IBES timestamps or proclaim the article timestamp the first public dissemination instant.

The one-minute Merck discrepancy remains unresolved. A webpage publication delay, later republication, minute rounding, or source error could explain it; this probe does not distinguish those explanations. No blanket one-minute shift or new tolerance was applied.

## What the evidence permits

Together with the manufacturer manual, the winter/summer comparisons provide direct evidence supporting an Eastern-time interpretation for the successfully compared source records. They do not certify every WRDS record, a first-public-release guarantee, or a bounded seconds-level error. Displayed-minute equality is weaker than five-minute endpoint measurement validity.

No RTH/non-RTH count, empirical power, headline coefficient or Gate 1 PASS is reported. No source clock values or prior receipts were overwritten. No price/return/EPS values or article bodies were exported. The source roster is unchanged. Two targeted search rounds for original Apple wire locators did not find usable exact links; no unrelated result was substituted.

## Tests and deliverables

- `clock_comparison.csv`: eight source-linked comparison rows.
- `public_timestamp_candidates.json`: metadata-only extraction evidence, including the initial timeout.
- `merck_metadata_roles.json`: retained WebPage/NewsArticle roles and timestamp offsets.
- `regi_wire_timestamp.json`: timestamp-only fallback evidence.
- `comparison_receipt.json`: counts, input scope, and code hash.
- Six parser golden fixtures pass: summer/winter offset handling, article/page distinction, date-only rejection, naive-time rejection and conflicting-article rejection. These are parser tests, not a completed research pilot.

## One concrete next action

Send the prepared narrow question to WRDS/LSEG, citing the newly documented convention and the observed one-minute discrepancy, to resolve the precise actuals-field semantics and rounding policy. Do not send licensed rows or financial values. External contact has **not** been made and requires the user's authorization; this report does not pretend that another local script can supply a missing provider guarantee. Alternatively, an explicit PI-approved uncertainty policy would require its own golden sample and pilot before the full endpoint run.

# Canaries benchmark source audit — 2026-08-19

## Determination

The requested `0.19` benchmark is **not verified**. No inspected primary
Canaries paper or DAX proposal version contains an exact `19%` relative
employment-decline statement with a dated page/section/table locator. The
executable benchmark therefore remains `null`, `version_status` remains
`UNRESOLVED`, and Gate 1 cannot pass.

This is not a choice of `0.13` by convenience. The PI-directed version choice
was `0.19`; replacing it with an older sourced number requires an explicit
signed amendment, even though the older number is verifiable.

## Exact verified locators

| Value | Title and version | Exact locator | URL and file identity | Determination |
|---|---|---|---|---|
| 0.13 | Erik Brynjolfsson, Bharat Chandar, and Ruyu Chen, *Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of Artificial Intelligence*, August 26, 2025 | Abstract, printed p.1: “13 percent relative decline in employment”; Section 5, “Conclusion,” printed p.26, fourth bullet: “13% relative employment decline” | [archived copy of the authored paper](https://govextra.gov.il/media/uhkbolnl/canaries_brynjolfssonchandarchen.pdf), 57 pages, SHA-256 `75012cdca09a734e64e6dd75e635551286549343dd7549252284dea9dc454a7d` | Exact relative-employment figure verified. |
| 0.13 | *Dynamic AI Exposure: Capability, Cost, and the Timing of U.S. Labor-Market Adjustment*, DAX ERE Proposal v3 | §1 “Research Question and Motivation,” `docs/DAX_ERE_Proposal_v3.md:12`; full Canaries reference at line 100 | repository proposal | Proposal figure verified and explicitly refers to relative employment, not payroll dollars. |
| 0.16 | Same Canaries title, November 13, 2025 revision | Abstract, printed p.1; Section 5, “Conclusion,” printed p.16, fourth bullet | [official Stanford PDF](https://digitaleconomy.stanford.edu/wp-content/uploads/2025/11/CanariesintheCoalMine_Nov25.pdf), 65 pages, SHA-256 `3b342bf604ed5c8fad8a232c9879345bcb7b71583f33d2acead28d531467a188` | Later revision states 16%, not 19%. |

The Stanford publication page dates the working paper November 13, 2025 and
summarizes the 16% result:
<https://digitaleconomy.stanford.edu/publication/canaries-in-the-coal-mine-six-facts-about-the-recent-employment-effects-of-artificial-intelligence/>.

## 0.19 search result

The audit inspected the dated August 26 and November 13 paper versions, the
official Stanford publication page, the DAX proposal, and the authors' June 24,
2026 presentation slides hosted by the Bank of England
(<https://www.bankofengland.co.uk/-/media/boe/files/events/2026/b-chandar-slides.pdf>).
Searches for `19%`, `19 percent`, and an August 2026 paper version produced no
exact primary-source statement. The June slides' “How much does each
alternative explain the pattern?” table (slide 21) reports a quintile-5
coefficient and covers changes through April 2026, but it does not state a 19%
relative decline; deriving or rounding a new benchmark from a different
coefficient would not satisfy the requested exact-locator rule.

Missing evidence is recorded as missing: there is no title/version/date/page/
section/table/URL tuple for `0.19` to enter `power_standard.json`.

## Resolution paths

Only one of these can resolve the benchmark:

1. supply an authored paper/proposal artifact that states exactly `0.19`, with
   its version date and page/section/table locator; or
2. obtain a signed amendment selecting one of the sourced versions (0.13 or
   0.16) for a substantive reason fixed before the power result is seen.

Until then, no break-even bar or adequate-power verdict may be emitted.

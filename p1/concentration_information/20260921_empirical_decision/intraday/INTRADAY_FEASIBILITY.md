# Limited minute-data feasibility decision

Status: **HOLD_DATA — no minute-response estimation.** This document is a
bounded diagnostic of the preselected six candidate issuer dates and the nine
already acquired native DBN files. It is not a return result, a new purchase,
or a relaxation of the Phase 3 scientific gates.

## Rule frozen before this diagnostic

The only permissible minute comparison is issuer-event, venue, and horizon
specific. Both legs of a HIGH/LOW matched pair must have a valid baseline and
endpoint under the same venue-specific BBO definition. A multi-horizon curve
uses a fixed receiver set within an issuer-event/venue curve; venue comparisons
use their intersection, not different surviving baskets. The previous
``20-of-20`` requirement is retained only as a strict sensitivity, not a
blanket eligibility gate. Missingness must be reported against pre-event size,
liquidity, and connection before it could support a scientific comparison.

The current point-clock rule is not released: a public timestamp identifies a
publisher's publication record, not the global first-public instant. A
scientific event needs a source-specific interval with documented timestamp
semantics, a baseline before its lower end, a post endpoint after its upper end,
and an independently understood quote state. The two previously used Exxon
dates are exposed development diagnostics, never a validation sample.

## Public-clock sweep (preselected candidates only)

The sweep was limited to Apple 2023-02-02 and 2023-08-03, Microsoft 2023-04-25,
UnitedHealth 2023-04-14, and Exxon 2023-01-31 and 2023-07-28. Candidates were
given by the frozen calendar, not chosen after quote or return inspection.

| Candidate | Most specific public evidence found | Scientific use |
| --- | --- | --- |
| Apple, 2023-02-02 | [Apple newsroom release](https://www.apple.com/newsroom/2023/02/apple-reports-first-quarter-results/) gives the date and a 2:00 p.m. PT call, not a release-publication time. | No first-public interval; ineligible for minute work. |
| Apple, 2023-08-03 | Apple newsroom page is date-stamped; bounded check found no public publisher timestamp. | No first-public interval; ineligible. |
| Microsoft, 2023-04-25 | [SEC 8-K](https://www.sec.gov/Archives/edgar/data/789019/000119312523115280/d321368d8k.htm) says a release was issued that date. The SEC acceptance value is only a filing upper endpoint. | No release-publication interval; ineligible. |
| UnitedHealth, 2023-04-14 | [SEC exhibit](https://www.sec.gov/Archives/edgar/data/731766/000073176623000026/a2023q1exhibit991.htm) identifies the date and an 8:45 a.m. ET call, not a release-publication timestamp. | No first-public interval; ineligible. |
| Exxon, 2023-01-31 | [Exxon IR archive](https://investor.exxonmobil.com/company-information/press-releases?page=8) lists **5:30 a.m. CST** for the results release. | Publisher/IR-page timestamp, minute precision at best; not independently certified global first-public. Conditional PRE diagnostic only. |
| Exxon, 2023-07-28 | [Exxon 2023 IR archive](https://investor.exxonmobil.com/company-information/press-releases?page=1&year=2023) lists **5:30 a.m. CDT**. A prior Exxon release said results would be available at 5:30 a.m. CT, but a scheduled availability time is not an actual publication receipt. | Publisher/IR-page timestamp, not certified global first-public. Conditional PRE diagnostic only. |

For the two Exxon rows, the appropriate uncertainty representation is the
publisher-record minute, not a claim that all market participants first learned
the information then. The archived Phase 3 page metadata gave 06:30:00--:59 ET
on 2023-01-31 and 06:00:00--:59 ET on 2023-07-28; the current IR archive gives
5:30 a.m. Central for each. The January values agree after time-zone conversion;
the July page-metadata value differs by 30 minutes from the current IR listing.
That conflict is itself a reason not to freeze either as a scientific clock.

## Existing-file initialization and state diagnostic

The check opened the nine already acquired SCC DBN files with the designated
Databento runtime and emitted only the aggregate in
`EXISTING_FILE_INITIALIZATION_DIAGNOSTIC.csv`. No new/H2 quote response path
was read. All file records were `BBOMsg`; there was no separate halt,
withdrawal, or trade-status feed.

Each available file begins at most ten minutes before the intended baseline.
At the baseline, only 9/23 XNAS and 8/23 ARCX mapped **requested symbols** on
2023-01-31, and 8/23 XNAS and 6/23 ARCX symbols on 2023-07-28, had any
observed update. These 23-symbol record-presence counts include three
references and do not test two-sided validity or receiver response. They are
therefore different from the prior 20-receiver valid-endpoint counts. The
BATS, XNYS and derived EQUS files had zero symbols with an update on or before
baseline; several start after the baseline. This is a file-coverage and
initialization finding, **not evidence that those securities had no earlier
quotes**. With no earlier history and no state feed, carried BBO liveness,
halts, withdrawals, and feed gaps remain unknown.

The July baseline in the file is the old 06:00 ET conditional page-metadata
anchor (thus 05:55 ET), not the current IR archive's 06:30 ET publisher time.
Consequently its coverage counts cannot be read as coverage around the newer
publisher timestamp.

The existing `quote_state.py` behavior remains appropriate for a diagnostic:
it prohibits future fill and cross-session carry, treats undefined or crossed
sides as invalid, and does not infer halts from flags. It cannot turn a missing
pre-window state into proof of no quote. No repair iteration was justified:
this is an input-coverage limitation, not an implementation error.

`run_existing_file_initialization_diagnostic.py` reproduces the aggregate
diagnostic from the nine paths in `SCC_DBN_SOURCE_MANIFEST.csv`; it deliberately
does not emit symbols, quotes, prices, or response rows.

## Acquisition and next minimal input

SCC connectivity and the supplied Databento runtime were available. The
`DATABENTO_API_KEY` environment variable was absent; no credential was sought,
no quote API call was made, and no purchase was attempted. This is an
authorization/credential state, not a conclusion about vendor data
availability. Existing receipts total $0.015124082565 quoted usage, while
actual billing remains unverified.

If authorization and a key later become available, the minimal source-specific
supplement is not a broad tick purchase: first re-price the two **conditional**
Exxon publisher-clock diagnostics only, requesting the exact same 23 symbols
and venue-specific `bbo-1s` schema from 30 minutes before through 60 minutes
after each documented publisher-time interval, plus a status-capable record
sufficient to assess liveness. This is a conditional technical request, not a
claim of a globally certified first-public clock. Do not request the presently
clock-ineligible Apple/Microsoft/UNH windows merely to fill a count. Quote first
and stop if the total is above the remaining authorized USD 10 ceiling or
existing available funds.

## Targeted Nasdaq source check

[Nasdaq's July 7 notice](https://ir.nasdaq.com/node/106481) and its
[contemporaneous schedule PDF](https://indexes.nasdaqomx.com/docs/NDX_SpecialRebalance_2023.pdf)
confirm that a pro-forma file and index-share announcement were scheduled for
2023-07-14, based on July 3 reference shares. Neither public source supplies
the dated full pro-forma constituent/share vector. Thus H3 remains `HOLD_DATA`;
there is no authority to construct a treatment vector from secondary weights.

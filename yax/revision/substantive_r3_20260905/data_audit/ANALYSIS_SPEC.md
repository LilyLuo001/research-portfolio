# R3 corrected-calendar data and cell audit

Status: post-outcome descriptive audit. This module does not estimate a new
preferred outcome coefficient.

## Fixed inputs and population

- Basic Monthly CPS extracts are the authenticated wide file and the separately
  authenticated March 2017--2021 Basic repair.
- The repair is an explicit source replacement: wide `03s` rows in those five
  months are removed before positive-weight eligibility, then `03b` rows are
  added. No ASEC weight or ASEC variance procedure is used.
- Employed people ages 18--65 with positive final person weight are routed to
  Census-2018 occupation codes. The headline cell audit then uses ages 22--25
  and 26--65 and the 468-occupation historical primary support.
- The observed source calendar is January 2017--July 2026 with October 2025
  absent. December 2022 is observed but excluded from the static estimand as a
  transition month. It is never treated as missing or interpolated.

## Objects to generate

1. A month-by-month expected/observed/retained calendar.
2. Cell counts and the p10, median, and p90 of routed respondent-equivalent
   counts, both including structural zeros on the 468-by-113 grid and among
   positive cells.
3. A sample-flow table distinguishing source records, fractional routed
   descendants, aggregate age cells, model-positive cells, one-sided zero
   cells, and both-zero grid cells.
4. An occupation support/exclusion file and bridge-conservation audit.

`respondent_equivalent` is exact record count only for direct Census-2018
records from 2020 onward. Before 2020 it is the sum of fractional bridge routes;
it is not a count of distinct survey respondents. CPS final weights form cell
stocks once; route probabilities divide, rather than multiply again, each
source record's stock across compatible target codes.

One-sided zero cells are valid grouped-binomial outcomes and remain in the
model. Both-zero occupation-month cells contain no likelihood contribution and
are absent from the fitted-row set but counted on the complete grid.

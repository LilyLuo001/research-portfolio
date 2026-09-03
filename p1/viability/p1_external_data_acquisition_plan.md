# P1 external event-data acquisition plan

## Decision context

The present 82-event recovery pool can plausibly repair the frozen 33-stock K2
count if work is sharply targeted, but it cannot supply the hundreds of
independent non-Dimensional waves required by the clustered MDE audit.  External
data therefore should not be purchased on the assumption that a larger event
list alone will make the current headline design viable.  Any purchase must
first pass a small coverage-and-field pilot.

## Ranked strategy

### 1. Morningstar Direct conversion fields — best event-discovery source

Morningstar is the only evaluated source that publicly documents the exact
fields P1 needs: a converted-from-mutual-fund flag, conversion date, predecessor
fund name, and predecessor share-class ID.  Morningstar also says the converted
tags are checked against SEC filings.  See the official
[Morningstar conversion-field description](https://www.morningstar.com/business/insights/blog/mutual-funds-etf-conversions#how-to-find-converted-etfs-in-morningstar-direct).

Request a pilot export containing all U.S. ETFs with:

- converted-from-mutual-fund flag and conversion date;
- predecessor name and share-class ID;
- successor fund/share-class ID, ticker, adviser, category, inception date;
- AUM immediately before conversion if available;
- CUSIP/ISIN and any SEC series/class identifiers;
- coverage start/end dates and historical revision policy.

Acceptance test: recover at least 70 of P1's 74 verified exact-day events with
the same day, identify materially new completed conversions, and demonstrate
that predecessor/successor IDs can be crosswalked to SEC series IDs.  Confirm
license terms permit research extracts and reproducibility tables before buying.

### 2. Systematic SEC filing recovery — best marginal-cost action

Run only against the ranked 82-event file, not a new broad manual search.  Use
the known predecessor/successor CIK and series IDs to search N-14 variants,
497/497K/485BPOS completion supplements, and filings immediately around the
existing month or bracket.  Extract explicit closing/effective language and
retain accession, form, filing date, quoted context, and a final-versus-proposed
flag.  Investor.gov confirms that converting funds notify investors through
fund documents; those documents are the authoritative evidence layer.  See the
[SEC investor bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/mutual-fund-conversion-exchange-traded-fund).

Start with the top 25 rows in `p1_nonexact_82_priority.csv`, emphasizing proposed
days and narrow brackets.  Promote a day only when a completion filing or other
authoritative post-closing evidence confirms it; a proposed date alone remains
ineligible.

### 3. Adviser and fund press-release archives — targeted corroboration

For priority rows not closed by EDGAR, search the adviser newsroom, fund page,
Internet Archive snapshots, and exchange launch notices within the frozen date
window.  These sources often state first trading day or completion day and can
locate the relevant SEC filing.  They are corroboration/discovery sources, not a
replacement for a completion filing when wording is prospective.

### 4. ETF Global / ICE — conditional supplement, not first purchase

ETF Global's public materials document extensive ETF reference, holdings,
flow, and classification data, but the public data dictionary does not establish
a predecessor-mutual-fund or conversion-date field.  See the official
[ETF Global data dictionary](https://media.etfg.com/files/AWS%20Junto/1.1.21%20-%20ETF%20Global%20Data%20Dictionary%20-%202021.pdf)
and [ICE product page](https://developer.ice.com/fixed-income-data-services/catalog/etf-global).
Request a field-level sample containing known P1 events.  Purchase only if it
demonstrates predecessor identity plus exact effective date; ETF inception date
alone is not sufficient.

### 5. Other commercial fund-reference products — request samples only

LSEG/Lipper and comparable fund-reference products cover mutual funds and ETFs
and provide identifiers, but their public descriptions do not establish a
conversion-lineage event table.  The
[LSEG funds catalogue](https://www.lseg.com/en/data-catalogue/funds) is therefore
a lead, not evidence that the required event fields exist.  Ask vendors to
return the four Dimensional June 2021 events plus ten randomly selected P1 rows
before discussing a license.

### 6. WRDS fund databases — verification, not source-list construction

Continue using CRSP and `wrds_mutualfund` for identifier, history, AUM, return,
and fund-type validation.  Do not infer MF-to-ETF conversions from termination,
name, ticker, or ETF flags without an explicit predecessor-successor event and
effective date.  ETF Global data available through WRDS can be evaluated under
the same field-demo rule above.

## Acquisition sequence and stop rule

1. Ask the institution whether Morningstar Direct is already licensed and run
   the pilot export.
2. In parallel only if no new purchase is required, recover the top 25 ranked
   SEC/adviser rows.
3. Recompute exact dates, waves, N-PORT eligibility, and the viability audit.
4. Do not buy ETF Global/LSEG solely for P1 unless the sample proves the four
   lineage fields.
5. Stop acquisition for the frozen headline design if the pilot confirms that
   the attainable universe remains near the current 247 structural members;
   that ceiling is far below the clustered 0.5-SD power rescue target.

Morningstar is thus the best source for measuring whether P1's event universe is
complete.  It is not expected to overturn the present power classification by
itself.

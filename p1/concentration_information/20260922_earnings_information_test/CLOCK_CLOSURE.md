# Bounded clock adjudication — 2026-09-23

The 48 existing event anchors remain candidate I/B/E/S announcement minutes. No anchor was moved using a quote response. All 48 retain `primary_first_public_clock_status=NOT_YET_VERIFIED` in the original event manifest. The supplied six-issuer sample has only premarket and after-hours events, with three issuers in each session; session and issuer composition cannot be disentangled by a raw session contrast.

## What the sources establish

- The archived [field-and-version evidence](../20260921_ibes_pit_semantics/FIELD_AND_VERSION_EVIDENCE.md) distinguishes announcement from vendor activation and documents nominal seasonal US Eastern time. This supports using America/New_York for the candidate timestamp; it does not certify first public dissemination or a one-minute error bound. This is reused documentary evidence, not a new WRDS connection.
- [Apple's 2023 first-quarter release](https://www.apple.com/newsroom/2023/02/apple-reports-first-quarter-results/) supports the event date and distinguishes the later earnings call. A fresh HTML metadata check returned `datePublished: 2023-02-02Z`, without a release time. It therefore does not verify the manifest's 16:30 ET minute.
- [Cummins' 2023 first-quarter issuer release](https://investor.cummins.com/news/detail/607/cummins-reports-record-first-quarter-2023-results) supports May 2, 2023 and links to its original Business Wire distribution. The retrieved issuer text supplies a release date but no independently established first-public minute. Direct attempts to inspect issuer/wire HTML timestamp metadata failed certificate verification in the local runtime; verification was not disabled. The manifest's 08:02 ET anchor remains unverified, not contradicted or silently corrected on the basis of secondary search snippets.
- The other issuer-owned sources retained in [OFFICIAL_CLOCK_SOURCES.md](OFFICIAL_CLOCK_SOURCES.md) are documentary event-identity references. They do not constitute a completed 48-event timestamp audit. No conference-call, SEC acceptance, webpage-modification or availability-notice time is substituted for the first release time.

## Consequence for this completed pilot

The estimates describe next-second prediction within fixed **candidate-clock windows on earnings dates**. A one-second prediction horizon is not a claim that the news clock is accurate to one second. The labels PRE and POST in historical outputs are offsets from the candidate anchor, not verified pre-information and post-information states.

The corrected pre-anchor path uses the fixed grid center at candidate minus one second. It is an auditable pre-anchor benchmark, but cannot be called certainly pre-publication. Anchor-based paths are retained as a separate sensitivity. Neither path proves the location at which information first entered the market, and a persistent change is not an independently observed fundamental value.

This limitation does not prevent completing conditional prediction, support, deletion sensitivity and descriptive paths from the already acquired windows. It does prevent claiming precisely timed announcement absorption or a structural ETF leadership result. No additional quotes, event types, years or clock optimization are authorized by this adjudication. If a future study targets first-public absorption, the specific missing input is an independently sourced release-time record for its fixed events, obtained before choosing new quote windows.

## Closure scope

Date/identity documentary checks are partial; first-public clock accuracy is unresolved for every event. The original row-level status is preserved rather than upgraded. No EPS, forecast or financial values enter the empirical analysis or the returned clock adjudication. No new market-data purchase was made for this check.

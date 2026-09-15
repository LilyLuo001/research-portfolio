# One bounded provider question — prepared, not sent

Please confirm the field contract for **WRDS `ibes.actu_epsus` (unadjusted US quarterly EPS actuals), `anndats` + `anntims`, observation years 2019–2024**:

1. Does `anntims` represent first public earnings dissemination, broker/vendor receipt, comparable-actual creation, or another event? Is the definition stable across these years?
2. Are `anndats` and `anntims` jointly stored in America/New_York with historical daylight saving, fixed EST (UTC−05), UTC, issuer-local time, or a per-record zone? If record-specific, name the offset/zone field and source table.
3. Are times rounded, truncated or imputed to minutes? What is the documented uncertainty or fallback rule? Are `00:00:00`, scheduled releases, revisions and retrospective updates marked?
4. How does this timestamp differ from `actdats/acttims`, and how is first release distinguished from subsequent actual corrections/restatements?

We need a dictionary version, official help page or written source-specific confirmation. No earnings values, forecasts, quotes, prices or returns are requested. We will use the answer only to validate the already acquired fixed event calendar and outcome-blind coverage masks, not to authorize treatment estimation.

The actual audit has 852 source-matched quarterly associations, all `anntims` on minute boundaries and 56 with later activation dates. These are aggregate diagnostics, not evidence that a timezone or minute-precision rule is known.

# Next decision — E007 earnings-metadata retrieval seed

**Task status:** `METADATA_PROJECTED / ECONOMIC_EVENT_RULE_PENDING`.
This is an E007-only `EARNINGS_METADATA_RETRIEVAL_SEED_ONLY` result, not an
approved analysis population. Research remains `HOLD_DESIGN + HOLD_DATA`.

The executed seed contains 8,801 primary-ready stock-wave rows and 3,440
PERMNOs. Its date-valid PIT bridge mapped 8,516 seed rows, left 285 unmapped,
and yielded 3,344 CUSIPs. The restricted eight-column IBES projection found
103,876 source records for 3,339 candidate CUSIPs. This measures source
records only: the bridge validates mapping at the E007 effective date, not at
each source record date. No economic-event de-duplication, timezone rule,
exchange calendar/session classification, quote coverage, or response outcome
has been created.

The single next decision is to document the IBES economic-event/revision rule
and announcement-time timezone convention against the licensed source, then
run that rule only on the existing protected metadata output. It must retain
source provenance and cannot select a primary session, inference method,
margins, H3, or causal interpretation. Final new-clock membership still needs
package-specific announcement evidence, pre-announcement holdings, and
denominator/corporate-action evidence listed row-by-row in
`NEW_CLOCK_MEMBERSHIP_GAPS.csv`.

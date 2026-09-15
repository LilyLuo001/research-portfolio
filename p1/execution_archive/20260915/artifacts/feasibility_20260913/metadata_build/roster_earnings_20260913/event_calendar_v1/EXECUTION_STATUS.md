# Executed event-date envelope — bounded result

**Status:** `DATE_LINKAGE_EXECUTED; SESSION_CENSUS_NOT_RUN`.

The SCC-only run used the pinned E007 seed (3,440 PERMNOs), the reviewed v2
eight-column metadata projection, and the full historical CRSP–IBES link after
predicate filtering to those seed PERMNOs.  It re-evaluated historical-link
validity at each returned `anndats` date.  All row-level envelope data and the
new-CUSIP delta remain on SCC at:

`/projectnb/econdept/qluo/P1_Refraction_WRDS/p1_roster_earnings_20260913/event_calendar_v1/run/`

Only `event_calendar_aggregate_receipt.json` was copied locally.

| Aggregate | Count |
|---|---:|
| Retained v2 metadata source records | 103,876 |
| Records with date-valid seed-filtered PIT link | 96,573 |
| Ambiguous valid PIT-link records | 0 |
| Parseable announcement dates / clock strings | 103,876 / 103,876 |
| `pdicity=QTR` / `ANN` source records | 82,300 / 21,576 |
| Historical CUSIPs for seed PERMNO envelope | 5,040 |
| Existing v2 CUSIPs | 3,344 |
| New historical CUSIP delta | 1,696 |

No query was run for the 1,696 new CUSIPs.  The envelope remains source-record
level and has no economic-event count, revision rule, session label or outcome.

The exact session blocker is documentary: reviewed IBES metadata has no verified
timezone semantics, while the archived exchange-calendar schema has no market
open/close or early-close intervals.  `ANNTIMS` clock strings alone are not a
session classification source.

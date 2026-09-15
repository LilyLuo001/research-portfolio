# Event-date linkage and session census — executed date linkage; session pending

The historical-ID envelope is source-record level.  It re-evaluates each
candidate CUSIP-to-PERMNO link at the IBES `anndats` date, rather than treating
the conversion-effective-date bridge as an earnings-date bridge.  It preserves
all date-valid links and flags zero or multiple links.  It does not choose an
economic-event/revision rule.

`ANNTIMS` strings are not sufficient to classify RTH/non-RTH.  The reviewed
receipt explicitly leaves timezone unverified, and the archived exchange
calendar schema has no open/close or early-close instants.  Therefore every
session count is `NOT_RUN` until a source-pinned exchange-timezone/calendar
interval adapter and a signed session rule are supplied.  No raw rows should
leave SCC; the local deliverable may contain only aggregate counts and hashes.

The source-side event-date linkage was executed on 2026-09-13 with the pinned
seed, v2 metadata, historical link and v2 CUSIP input. Its aggregate receipt
is `receipts/event_calendar_aggregate_receipt.json`; the row-level envelope
remains on SCC. The executable requires all four pinned inputs:
`source_side_event_envelope.py --seed <pinned seed> --metadata <pinned metadata> --bridge <pinned historical link> --v2-cusips <pinned v2 CUSIP list> --out-dir <new SCC task directory>`.

The remaining session operation is blocked specifically by unverified
`ANNTIMS` timezone/provenance and the absence of a source-pinned historical
exchange open/close/early-close interval input—not by SSH access.

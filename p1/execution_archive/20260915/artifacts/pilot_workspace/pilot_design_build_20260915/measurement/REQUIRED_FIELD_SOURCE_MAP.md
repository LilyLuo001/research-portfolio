# P2 metadata input contract

The adapter takes the existing local `union_v2_earnings_inputs/selected_event_metadata.csv` only as an association manifest. Its required columns are `association_id`, `wave_id`, `permno`, `sample_period`, `announcement_date`, `announcement_times_all`, `mapping_status`, `date_valid_raw_symbol`, and `date_valid_ncusip`. These establish a row key and existing identity metadata; they do **not** establish timezone, public-release semantics, seconds precision, session, or RTH eligibility.

The named Gate 1 receipts supply the source map:

| Required P2 input | Exact source / field | State |
|---|---|---|
| Association key and period | local union-V2 `selected_event_metadata.csv`: `association_id`, `sample_period` | available locally |
| Date/time candidate | local union-V2: `announcement_date`, `announcement_times_all`; SCC actuals projection: `anndats`, `anntims` | candidate only; clock semantics unresolved |
| Source identity checks | Gate 1 `identity_clock_receipt.json`: actuals projection `permno,cusip,pends,pdicity,anndats,anntims,actdats,acttims` | receipt-only locally; row values SCC-only |
| Timezone and bounded uncertainty interval | a custodian projection with `source_id,source_timezone,interval_lower,interval_upper` | absent; no ET or seconds bound is inferred |
| Calendar/session boundaries | approved exchange-calendar projection with `calendar_id,session_date,calendar_timezone,open_local,close_local` | absent from the input contract; must be supplied for each source/date |
| Existing core-leg repair scope | Gate 1 `core_mapping_gap_locators.csv`; CRD mapping receipt | local candidate scope only; no retry/purchase authority |

An interval is definitive only if all four clock fields and a matching calendar session are present. The classifier is deliberately conservative: an interval crossing the RTH-60 boundary is `UNKNOWN`, not rounded into either side. It does not manufacture a full-population seconds-error bound from the eight-event cross-check.

The existing `union_v2_event_calendar_actions/trading_calendar.csv` is version `7a791bb56ce116ddc196d40bb2b7eb2a8b2a4b333e1377d582c7c6162e26b770` and supplies observed trading dates, but it has no `calendar_id`, `calendar_timezone`, `open_local`, or `close_local` fields. Consequently it cannot support a `source_clock_session_IF_EASTERN` count without inventing intraday session rules. `prepare_existing_metadata_diagnostic.py` instead creates a time-of-day aggregate with no market-session labels, alongside the strict all-unknown receipt. The manufacturer manual and matched public records are preserved only as a candidate Eastern/DST interpretation for the checked records, not a full-population source-timezone, public-release, or precision certification.

The post-custodian deliverable is a metadata-only CSV with the six interval fields above plus a session-calendar CSV with the four calendar fields. The next permitted operation is that narrow SCC metadata projection and approved calendar projection, returning classifications/counts and a receipt only. Existing `pilot_config.json` permits `local_metadata_projection` and `scc_connectivity_check`, while `remote_raw_value_scan`, POST response access, and spend remain false. The historical named-custodian proposal covers PRE-only SUE/response/covariance calibration and a POST non-response mask **only after approval**; it is not an authorization for this agent to decode native files or export raw values.

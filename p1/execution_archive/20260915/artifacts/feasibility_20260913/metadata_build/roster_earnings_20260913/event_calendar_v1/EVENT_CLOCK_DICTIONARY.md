# Event-clock dictionary

| Field / concept | Source locator | Status | Permitted use | Not established |
|---|---|---|---|---|
| `anndats` | `meta/schema__ibes__actu_epsus.csv` | DATE_PARSEABLE | source-record announcement date; PIT-link evaluation date | economic-event identity or public-release provenance |
| `anntims` | same schema | CLOCK_STRING_PARSEABLE | diagnostic count only | timezone, exchange-local time, precision, RTH/non-RTH |
| `pends`, `pdicity` | same schema | SOURCE_RECORD_FIELDS | period/reported periodicity diagnostic | revision/economic-event selection rule |
| `sdate`, `edate` | `meta/schema__wrdsapps_link_crsp_ibes__ibcrsphist.csv` | VERIFIED_INTERVAL_FIELDS | inclusive PIT security-link check at `anndats` | economic identity quality or score threshold |
| `score` | same bridge schema | RETAINED_UNFILTERED | descriptive provenance | analysis eligibility cutoff |
| exchange trading status | `meta/schema__crsp__metaexchangecalendar.csv` | INSUFFICIENT_FOR_SESSION | calendar/holiday documentation only | open, close, early-close instant or session interval |

An `ANNTIMS` clock string is not converted to a timezone or session.  No entry
in this dictionary is an authorization to collapse source records to economic
events.

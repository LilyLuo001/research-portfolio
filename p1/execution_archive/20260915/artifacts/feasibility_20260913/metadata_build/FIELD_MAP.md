# Field map

| Returned census field | Source field(s) | Permitted meaning | Limitation |
|---|---|---|---|
| `wave_id`, `effective_date` | free exposure parquet | conversion-wave membership/calendar | implementation date is not announcement instant |
| `exposure_cells`, `unique_stocks` | `cusip`, `wave_id` | stock-wave support counts | no earnings-event join |
| provisional tier counts | `pre_etf_ownership` | deterministic positive-dose tercile feasibility | holdings are not verified strictly before `A_w` |
| date-linked constituent count/date presence | `events_merged.csv` `fund_name`, `announce_date`, `effective_date` | provisional effective-date linkage, not verified package membership | date only; no time/timezone/uncertainty |
| reuse | `cusip` across `wave_id` | repeated exposure membership | not economic dependence components |
| reconstructed PRE-effective readiness | `primary_ready`, `pre_report_date_min/max` | 8,801 positive ready cells of 8,826 reconstructed cells | not a public-announcement clock |
| adviser proxy | `advisers`, `is_dimensional` | unsigned descriptive proxy only | not a signed economic-sponsor cluster |

Known source schemas do not implement final session, clean-control, signed-sponsor, response-leg or inference semantics.  They are `NOT_IMPLEMENTED` for this census, rather than inferred from an absent column.  Announcement times/timezones and holdings/denominator dates relative to an announcement are also unavailable for new-clock eligibility.  Unknown numeric cells are blank in generated CSVs, never zero.

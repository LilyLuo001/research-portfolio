# Current P1 universe output

> **Universe-finalization pause (2026-09-03):** the 74 exact-day / 71 Gate0
> subsets remain measured and internally valid, but they are not declared the
> final global universe while the Fed note's unpublished 125-event aggregate
> remains unreconciled. Exposure construction and K2 are suspended. See
> `event_universe_reconciliation_report.md`.

These files are the 2026-09-03 event/date authority:

- `event_master_final_reconciled.csv`: 247 structural members, including 156
  completed conversions; 74 rows are verified exact-day/timing eligible.
- `event_master_reconciliation.csv`: row-level transition audit.
- `date_transition_matrix.csv`: old-to-final precision counts.
- `date_conflict_audit.csv`: unresolved conflicts retained without overwrite.
- `wave_membership_v2.csv`: the 74 exact-day events assigned to 49 waves.
- `fed_source_event_universe.csv`: the Fed's 125 reported aggregate units,
  represented as four published Table 1 rows plus 121 explicitly unidentified
  placeholders; no names or dates are invented.
- `fed_to_p1_event_crosswalk.csv`: four exact empirical-source matches and 121
  source rows that cannot be matched because the note does not publish them.
- `excluded_82_source_date_audit.csv`: source-specific audit of every completed
  P1 event excluded for non-exact timing.
- `event_universe_reconciliation_summary.csv` and
  `event_universe_reconciliation_report.md`: count/decision reconciliation.

The root `p1/events_merged.csv` and `p1/t2_wrds/waves*.csv` are legacy
baselines. Do not substitute their 172-event/96-wave counts for this output.

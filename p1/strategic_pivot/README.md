# P1 strategic pivot audit

The current research authority is
`POST_V3_RESEARCH_DECISION-2026-09-06.md`; read it first. It preserves the
production locks and classifies fund-level construction as `NOT YET` and a full
Gate 0/1 rewrite now as `NO`.

The remaining files preserve the outcome-blind 2026-09-03 redesign and its
evidence. `strategic_recommendation.md` is retained as a superseded decision
record, not as execution authority.

The CSVs are evidence tables; the Markdown files state identification, failure gates, and design rankings. `build_strategic_audit.py` reproduces dose and conditional-power tables from frozen exposure outputs. `build_vanguard_census.py` reproduces the Vanguard census from a licensed CRSP fund header and the public SEC mutual-fund ticker mapping; raw licensed data are never committed.

No file here reports a treatment coefficient. Conditional MDE rows are sensitivity calculations, not final outcome-specific power, because TAQ outcomes do not exist in the current archive and untreated/preperiod residual variance has not been observed.

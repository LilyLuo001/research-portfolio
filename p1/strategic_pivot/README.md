# P1 strategic pivot audit

This directory freezes the outcome-blind 2026-09-03 redesign. Read `strategic_recommendation.md` first.

The CSVs are evidence tables; the Markdown files state identification, failure gates, and design rankings. `build_strategic_audit.py` reproduces dose and conditional-power tables from frozen exposure outputs. `build_vanguard_census.py` reproduces the Vanguard census from a licensed CRSP fund header and the public SEC mutual-fund ticker mapping; raw licensed data are never committed.

No file here reports a treatment coefficient. Conditional MDE rows are sensitivity calculations, not final outcome-specific power, because TAQ outcomes do not exist in the current archive and untreated/preperiod residual variance has not been observed.

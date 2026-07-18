# P1-T1 Human Gate 1 (spotcheck) — results

Owner reviewed `p1/t1_spotcheck_sample.json` (57 rows: all 47 M/L + a
deterministic 10% of the 92 H). Verified for internal consistency and against
the extraction evidence (live SEC fetch unavailable at review time).

## Rulings applied (via p1/t1_arb/apply_spotcheck.py, then re-assemble)
**Not an event — ETF-to-ETF (target already an ETF), removed from events_merged:**
- American Energy Independence ETF — 0000894189-19-007768 (evidence: "Both are ETFs")
- Cambria Core Equity ETF — 0000894189-19-007642, -006521
- American Customer Satisfaction ETF — 0000894189-21-002216, -001425 (Tidal trust move)
- Nationwide Nasdaq-100 Risk-Managed Income ETF — 0001999371-24-004354
- iM DBi Managed Futures Strategy ETF & iM DBi Hedge Strategy ETF —
  0001193125-21-250290, -217182 (per-event removal inside multi-fund N-14s)

**Recheck (quarantined, kept out of the clean set pending source confirmation):**
- iM Dolan McEniry Corporate Bond Fund — 0001193125-21-250290, -217182. Deepseek's
  evidence for this row is the DBi-ETF text (multi-fund evidence bleed); cannot
  confirm the target was a mutual fund without the source. Held for full-text check.

**Deferred (source future-dated vs the 2026-07-18 gate):**
- Zevenbergen Growth Fund & Zevenbergen Genea Fund — all filings (0001999371-26-012937
  etc., filed 2026-07-28). Real MF→ETF per evidence, but unverifiable as of the gate.

**Field fix — over-merge (structural, fixed in assemble.py grouping):**
- Emerging Markets Portfolio (Sanford C. Bernstein) had announce_date 2022-12-15
  copied from Mirae's "Emerging Markets Fund" — both normalized to "emerging
  markets" under the name-only key. Grouping now keys on (fund_name, family);
  corrected announce_date is 2025-08-22 (Sanford's own earliest filing).

## Corpus-wide safety sweep (beyond the sampled rows)
Scanned every event filing's evidence for "target is/both are an ETF" language.
Nine hits total — all belong to the conversions the owner flagged (incl. the
duplicate amendment filings of Cambria and the two iM N-14s). No additional
ETF-to-ETF false positives survive in events_merged.csv.

## Result
events_merged.csv: **173 conversions** (was 178), contract PASS, PK-unique,
deterministic. 47 M/L rows fully reviewed; 10/92 H sampled clean. Provisional
rows the owner would re-confirm against SEC pages (future-dated effective dates
especially) remain flagged in `arb_report.md`.

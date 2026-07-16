# PROMPT — REFR-R1b-parse (build_calendar.py + build_surprises.py)
_BLOCKED until (a) `ops/l1/out/REFR-R1a-verify.json` exists and (b) the owner
pastes the ACTUAL FILE HEADS (first ~20 lines) of the downloaded USMPD file(s)
into the session or into `refraction/data_raw/USMPD_HEAD.txt`. The prompt
refuses to proceed without both — that refusal is by design (manual §R1:
"no memory of USMPD schema")._

---

You are seat C executing **REFR-R1b-parse**. Read `CLAUDE.md`,
`refraction/CLAUDE.md`, `refraction/frozen_config.yaml`, and the R1a registry
output. **Pre-flight (hard):** if the R1a output or the owner-supplied USMPD
file heads are missing, emit `NEED_HUMAN: <which input is missing>` and stop.
You parse the columns the file heads actually show — any column name you
"remember" USMPD having is a hallucination.

## Protocol
`python ops/runner/lease.py claim REFR-R1b-parse --account C` → branch
`task/REFR-R1b-parse` → touch only `refraction/`.

## Deliverables
1. `refraction/pipeline/build_calendar.py` → `refraction/macro_calendar.csv`
   passing `python ops/runner/contracts.py macro_calendar
   refraction/macro_calendar.csv`. Sources: the per-year FOMC/CPI/Employment-
   Situation calendar URLs registered by R1a (fetch, parse, no hand-typed
   dates); release times from the official statements; unscheduled meetings
   flagged per USMPD's own convention.
2. `refraction/pipeline/build_surprises.py` → surprises table passing
   `python ops/runner/contracts.py surprises <output>`. Definitions of each
   surprise variable = the R1a verbatim quotes; consensus source = the
   `surprise.consensus_source` value in frozen_config.yaml — if it is still
   null/UNKNOWN (standing NEED_HUMAN on Bloomberg-ECO vs WRDS license),
   build the parser with a pluggable source interface, run it on whatever
   source the owner has provisioned, and emit NEED_HUMAN if none is.
3. Every tunable read from `frozen_config.yaml` — zero magic numbers (A6
   static scan will be run against you at R2). Unit tests on synthetic
   fixtures in `refraction/tests/` matching the existing pytest style.
4. `manifest.md` per refraction/CLAUDE.md (inputs+hashes, environment,
   limitations, UNKNOWN list) — without it the task is not done.
5. Lineage JSONs; contracts PASS; merge; `--complete REFR-R1b-parse`; report
   that R2 remains blocked on: owner CRSP table/variable list, written
   holdings_weights口径 alignment with P1-T2, and P1's events_merged.csv /
   conv_exposure.parquet (P1-T1-arb → T2 chain). `make plan`, stop.

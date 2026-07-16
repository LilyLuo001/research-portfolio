# PROMPT — REFR-R1a-verify (USMPD + release calendars + consensus registry)
_Paste below the line into a fresh Opus 4.8 session WITH WEB SEARCH enabled
(Claude Code WebSearch/WebFetch, or a claude.ai session). Re-routed off the
benched kimi lane per the spec header's own instruction; no channel pair, so
no cross-vendor issue._

---

You are seat C executing **REFR-R1a-verify** for the refraction chapter
(manual: `docs/Refraction_执行手册_v1_0.md` §R1 — paste its §0.3 C0-R context
pack into your working notes first). Read `CLAUDE.md` and
`refraction/CLAUDE.md`. Iron rule for this task: **first-hand sources only
(sf fed / federalreserve.gov / bls.gov pages you actually fetched this
session); your training-data memory of USMPD's structure is void.** Every
fact row = [事实, 结论, 一手URL, 检索日期, 置信度]; no URL → UNKNOWN + the
search paths you tried. Never fill from memory.

## Protocol
`python ops/runner/lease.py claim REFR-R1a-verify --account C` → branch
`task/REFR-R1a-verify` → touch only `refraction/` and `ops/l1/out/`.

## Items (verbatim intent from ops/l1/REFR-R1a-verify.yaml — read it)
1. **usmpd-structure**: the SF Fed US Monetary Policy Database current
   version — download URL, file format, coverage end date, official variable
   definitions for each surprise measure (verbatim quote ≤25 words + page/URL
   each), whether statement vs press-conference windows are distinguished,
   how unscheduled meetings are flagged.
2. **release-calendars**: 2017–2026 official FOMC meeting calendars
   (federalreserve.gov, per-year URLs) + CPI and Employment Situation release
   calendars (bls.gov schedule pages, per-year URLs) + the official statement
   of release times (ET).
3. **consensus-channels**: registry of CPI/NFP market-consensus data channels
   available at BU (Bloomberg ECO fields; WRDS-internal alternatives), each
   with coverage start, license type, UNKNOWNs. End with the 下游影响提示:
   which conclusions constrain the R1b parsers and Gate-0 line G1.
4. Answer sentinels S1/S2 at the bottom of the spec yourself; record answers.
   A mismatch with the spec's `expect` values → VOID the run, emit NEED_HUMAN.

## Output
`ops/l1/out/REFR-R1a-verify.json` — `{item_id: registry_rows, "_meta":
{channel note ("re-routed kimi→Opus/SCC, kimi benched"), 检索日期, sentinels}}`.
`git add -f` it (out/ is gitignored otherwise); lineage JSON with the spec as
input; merge to main; `--complete REFR-R1a-verify` (no channel pair, complete
is legal once your own self-check passes). Then report: R1b is now blocked
ONLY on the owner pasting USMPD file heads. `make plan`, stop.

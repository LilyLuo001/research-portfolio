# manifest — REFR-R13-scan (monthly collision monitor)

Deliverable of queue node `REFR-R13-scan` (manual `docs/Refraction_执行手册_v1_0.md`
§R13, Prompt R13a). Per §0.4 a deliverable without this file is not delivered.

## What was built

| Path | Role |
|---|---|
| `refraction/scan.py` | the scanner: arXiv API + Semantic Scholar bulk API + generated SSRN search URLs, over the §R13a bilingual keyword list; computes the §R13b 毛刺 flag and per-hit ALERT threshold before any model sees the row |
| `refraction/tests/test_scan.py` | 23 pytest cases on synthetic payloads; `scan.urlopen` is poisoned in every test so the suite can never touch the network |
| `refraction/scans/` | output directory (`hits_*.csv/.jsonl`, `burr_*.md`, `ssrn_manual_*.txt`, `seen_ids.json`) |

## Inputs (no data inputs — this is monitoring infrastructure)

| Input | SHA256 | Use |
|---|---|---|
| `docs/Refraction_执行手册_v1_0.md` | see `refraction/scan.py.lineage.json` | §R13a keyword list (English phrases verbatim), §R13b 毛刺 rule and the 40%/60% ALERT thresholds |
| `e2/scan.py` | see lineage | architecture carried over unchanged per §R13 ("E2 T11 修正后架构原样搬用"); READ-ONLY, not edited |
| `ops/runner/queue.yaml` | see lineage | node definition (`worker: script`, `depends_on: []`, resident) |

Row counts: not applicable (code deliverable). Output row counts are printed by
each run and recorded in that run's `hits_*.jsonl`.

## Environment

Written and tested under Python 3.11.15 / pytest 9.1.1 in the session container;
kept **Python 3.6-compatible** (no f-strings, no dataclasses, stdlib only)
because the always-on box venv is 3.6, same constraint as `e2/scan.py`.
`refraction/tests`: 42 passed (19 pre-existing + 23 new).

## Design decisions worth knowing

1. **No LLM in the discovery path.** The scanner is deterministic; a model
   enters only at `REFR-R13-triage`, and only to judge overlap. This is the
   E2-T11 correction (a model with no native web access cannot be the
   discovery layer) applied as-is.
2. **毛刺 flag computed in the script, not the prompt.** §R13b says Marta/Riva
   authors and `replication technique`/`switch` titles go into the 毛刺节
   regardless of provisional overlap, at a 40% ALERT threshold. Because that
   is the single highest-value alarm in the chapter, the flag is computed
   mechanically and written into every output row, so a triage model cannot
   silently drop it.
3. **Author matching is token-exact, title matching is deliberately broad.**
   `Rivas`/`Martarelli` do not fire the author rule (a 毛刺节 full of
   false-positive authors trains the owner to stop reading it); a bare
   `switch` in a title does fire, because a missed priority hit is the
   expensive error and a spurious one costs 30 seconds.
4. **Window = 35 days** (monthly cadence + 5-day overlap) so a run that slips
   by a few days cannot open a coverage hole. Override with `--window-days`.
5. **Config placement.** Keywords and thresholds live in `scan.py` as
   constants citing §R13a/§R13b, NOT in `frozen_config.yaml`. `frozen_config`
   is the analysis config that freezes at GATE-PREREG; a resident monitor's
   keyword list must stay editable after that freeze without counting as a
   pre-registration deviation. `assert A6`'s static scan is unaffected (it
   scans for `w_shrink` literals only; this file contains none).
6. **Exit codes.** 0 on a clean run — zero new hits is a normal outcome — and
   1 only when *every* source leg failed, so cron surfaces a dead monitor
   instead of a silent green.

## Limitations

- **SSRN is a human click-through, by design.** SSRN has no stable public API
  and the spec forbids fabricating one, so the SSRN leg emits search URLs
  only. The Marta–Riva working paper (SSRN 4079302) lives there — the priority
  risk this monitor exists for is therefore only half-automated. Someone must
  actually open `ssrn_manual_*.txt` each cycle; if that does not happen the
  40% hair trigger is watching arXiv/S2 only.
- **The Chinese keywords are translations, not sourced terms.** arXiv and S2
  full-text search will return few or no hits on them; they are carried
  because §R13a asks for 中英双语 and cost nothing.
- **Not run live in this session.** The session container's egress policy
  blocks `export.arxiv.org` and `api.semanticscholar.org` (see the NEED_HUMAN
  entry in `ops/decisions.md`, 2026-08-18). The scanner has therefore been
  verified against synthetic payloads only; its first live run must be
  eyeballed once on the box.
- Semantic Scholar's unauthenticated pool rate-limits hard; set `S2_API_KEY`
  on the box for reliability (the code already sends it when present).

## UNKNOWN list

- Live behaviour of both APIs (payload shapes are handled as documented by the
  E2-T11 live run of 2026-07-09; not re-verified this session — no egress).
- Whether the S2 bulk endpoint's `publicationDateOrYear` prefilter still
  accepts the open-ended `YYYY-MM-DD:` form (local date filter is authoritative
  either way, so a change degrades efficiency, not correctness).

## Downstream notes / handoff

1. **Seat D — cron wiring.** R13 is resident from R0 onward, but the box
   schedule is `ops/box/cron_night.sh`, which is seat D's path; this seat owns
   `refraction/` only and did not edit it. Needed, monthly rather than nightly:
   `python refraction/scan.py` alongside the existing `e2/scan.py` call, with
   its outputs committed by the 21:00 digest tick (same treatment `e2/scans/`
   already gets).
2. **REFR-R13-triage** consumes `hits_YYYYMMDD.jsonl`. Every row already
   carries `burr`, `burr_reason` and `alert_threshold`; the triage prompt must
   use the row's own threshold, never a global 60%.
3. The node stays READY forever — `REFR-R13-scan` is resident and must NOT be
   `runner.py --complete`d, exactly as `E2-T11-scan` is not.

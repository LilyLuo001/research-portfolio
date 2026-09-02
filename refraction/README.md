# refraction/ — "One Shock, Many Prices" (macro-event standby chapter)

Manual: `docs/Refraction_执行手册_v1_0.md` (tasks **R0–R14**; C0-R context pack in §0.3).
Plan: `docs/MacroEvent_Chapter_Plan_v2_1_FINAL.md` (v2.1 final).
Queue: nodes `REFR-*` in `ops/runner/queue.yaml`; two human gates
(`REFR-GATE-PREREG`, `REFR-GATE-e2verdict`) enforce §0.5's DAG.

## What is already landed (R0's repo-contract part, this PR)

| Artifact | Purpose |
|---|---|
| `frozen_config.yaml` | Single source for every tunable. `prereg.*` and `beta.w_shrink` stay null until GATE-PREREG; Gate-0 thresholds pre-filled from Plan §9, owner confirms via ops/decisions.md |
| `guards/prereg_guard.py` | Iron rules 4–5 as program invariants: `assert_prereg_ok()` (R6+ startup hard check: OSF timestamp + URL + frozen w_shrink + clock after timestamp) and `assert_no_lookahead()` (A4 semantics). CLI: `python guards/prereg_guard.py check frozen_config.yaml` |
| `pipeline/assert_panel.py` | R2's 14 assertions (A1–A14) as importable checks + CLI; panel may be written only if all hard asserts pass |
| `scan.py` + `scans/manifest.md` | R13a resident collision monitor: arXiv + Semantic Scholar APIs + generated SSRN search URLs over the §R13a bilingual keywords; computes the §R13b Marta–Riva/replication-switch 毛刺 flag and the 40%/60% ALERT threshold per hit, before any model sees the row. No LLM in the discovery path |
| `tests/` | 19 + 23 pytest cases on synthetic fixtures: clean world passes; each tampered world (dup keys, lookahead, magic w_shrink, broken LOO/lever/weights, ConvExp drift, silent drops, wrong release time, upstream mutation) is caught |
| `ops/contracts/{macro_calendar,surprises,panel_ann,gate_report,refr_results}.yaml` | Mechanical output contracts for R1–R6 |
| `ops/l1/REFR-R0-collide.yaml`, `ops/l1/REFR-R1a-verify.yaml` | L1 dispatch specs (parked pending the kimi-bench decision, see file headers) |

## Task → status map (R0–R14)

| Task | Status | Blocked on |
|---|---|---|
| R0 collision sweep | L1 spec ready (parked: kimi bench) | bench decision or re-route |
| R0 repo landing | **DONE (this PR)** | — |
| R1a USMPD/calendar verification | L1 spec ready (parked, same) | — |
| R1b parsers | not started (DeepSeek) | R1a output + owner-pasted file heads |
| R2 panel/beta/lever build | not started (Claude Code, ~1 seat-week) | R1b; owner-pasted CRSP table/variable list; holdings_weights口径 alignment with P1-T2 (manual §2.3 残余风险①) |
| R3 Gate-0 diagnostics | not started (DeepSeek + Sonnet 判读起草) | R2 `--sweep` output |
| GATE-PREREG | human | R3 gate_report |
| R4 OSF prereg | not started (Opus draft; human submits) | GATE-PREREG |
| R5 econometric design 双旗舰 | not started (GPT-5 × Opus, by hand) | R3 |
| R6 dual implementation Py/R | **guard-blocked by design** | OSF timestamp in frozen_config + GATE-e2verdict |
| R7 spines / R8 grid | not started | R6 |
| R9 creation baskets | `NEED_HUMAN`: ETF Global access at BU | — (bypass, non-blocking) |
| R10 TAQ pilot | not started (Claude Code) | R2 permno list (bypass, non-blocking) |
| R11 writing / R12 red team | not started | R7/R8 |
| R13 collision scan script | **scanner DONE** (`scan.py`, 23 tests, manifest); **cron wired** (`ops/box/cron_night.sh` + evening commit list); triage un-run | a triage lane |
| R14 Meta-QA | not started (Flash-Lite/豆包, mechanical only) | — (resident) |

## Open NEED_HUMAN items (also surface in the digest)

1. CPI/NFP consensus license — Bloomberg ECO at BU vs WRDS alternative
   (`frozen_config.yaml: surprise.consensus_source`).
2. ETF Global / issuer daily basket files access (gates R9).
3. holdings_weights.parquet weight-basis alignment with P1-T2, in writing,
   before R2 is dispatched.
4. Gate-0 thresholds confirmation in ops/decisions.md (config values are the
   Plan §9 provisional lines).
5. OSF account + submission at GATE-PREREG (+48h), then fill `prereg.*` and
   `beta.w_shrink` in frozen_config.yaml in the same commit.
6. **Egress policy blocks R0-collide-A and R1a from web-sandboxed sessions**
   (found 2026-08-18).
   `frbsf.org`, `federalreserve.gov`, `bls.gov`, `export.arxiv.org` and
   `api.semanticscholar.org` all return 403 at the CONNECT stage from the
   Claude-on-the-web container. R1a's iron rule is first-hand pages fetched in
   session, and search-result snippets do not meet it, so R1a cannot be run
   from this lane at all — it needs the box, the SCC lane, or an egress
   allowlist. `refraction/scan.py` is unaffected: it runs on the box, where
   those hosts are reachable. Found independently by both seats working the
   refraction lane on 2026-08-18.
7. **`ops/runner/lease.py` misreports lease failures** (found 2026-08-18). Its
   `claim` treats *any* nonzero `git push` return as "another seat claimed it
   first", so an unrelated push failure (no upstream configured on the current
   branch, auth, network) is reported as a lost race — and it then runs
   `git reset --hard origin/main`, which discards uncommitted work on a
   non-`main` branch. Observed against `REFR-R1a-verify`, which is NOT leased
   by anyone. Suggested fix: inspect the push stderr for `non-fast-forward` /
   `fetch first` before declaring a lost race, and refuse to hard-reset when
   `HEAD` is not on the branch the lease targets.

8. **CUSIP→PERMNO bridge for R2** (found 2026-08-18, amendment v2.2 §4).
   `p1/conv_exposure_free.parquet` carries cusip/ticker/stock_cik but `permno`
   is blank in all 6,377 rows, and the R2 panel joins CRSP on it. Needs a
   CRSP-licensed crosswalk — not constructible from public files, so it rides
   with the standing WRDS access item. Also gates R10.

## WRDS requirements for R2/R10

R2's task prompt (执行手册 §R2) requires the owner to paste "你可用的数据表名与
变量名清单". That list — for both chapters, with date ranges and derivations — is
`p1/wrds/DATA-REQUIREMENTS-v2.1.md`; the agent prompt that produces it from a live
account is `p1/wrds/EXECUTION-PROMPT.md`. Three refraction-specific items in it are
not in P1's older request list: the daily CRSP window must start **2014-01-01**
(this chapter's announcements start 2017-01 and its placebo-in-time runs on
2017–2020 fake conversion dates with ±8 quarters, assert A2), `crsp.holdings`
supplies the missing `holdings_weights.parquet` for β_b^LOO, and `pre_etf_ownership`
must be rebuilt rather than reused — in the P1 parquet it currently *equals*
`conv_exp` (P1 plan §6.1.1 NEED_HUMAN).

Frozen P1 inputs (read-only, hash-registered when they exist): events_merged.csv,
**conv_exposure_free.parquet** (the built free-path file; the plan's
`conv_exposure.parquet` name does not exist — amendment v2.2 §3),
holdings_weights.parquet, ibes_sue.parquet.

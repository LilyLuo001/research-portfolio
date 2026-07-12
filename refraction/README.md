# refraction/ — "One Shock, Many Prices" (macro-event chapter)

One of the portfolio's four strictly parallel, equal-importance projects (with
P1, E2, DAX — see System_Master_Handover.md §2). `REFR-GATE-e2verdict` below is
a workflow/scheduling gate sequencing this project's heavy estimation phase
against the E2 decision window; it is not a fallback trigger.

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
| `tests/` | 19 pytest cases on synthetic fixtures: clean world passes; each tampered world (dup keys, lookahead, magic w_shrink, broken LOO/lever/weights, ConvExp drift, silent drops, wrong release time, upstream mutation) is caught |
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
| R13 collision scan script | not started (script + kimi triage) | — (resident) |
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

Frozen P1 inputs (read-only, hash-registered when they exist): events_merged.csv,
conv_exposure.parquet, holdings_weights.parquet, ibes_sue.parquet.

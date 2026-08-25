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
| `pipeline/build_betas.py` + `pipeline/build_basket.py` | R2's vendor-free core: announcement-regime betas (pre-period only, lookahead enforced per (permno, wave) by the guard), shrinkage toward a characteristics-implied prior with the w_shrink sweep Gate-0's G2 consumes, leave-one-out basket response, the L = L_mkt + L_tilt decomposition, and F_tilt. Point estimates REFUSE to run while `w_shrink` is null; sweep mode runs, because that is what Gate-0 reads |
| `pipeline/surprises.py` + `R1b_input_requirements.md` | R1b's schema-free half: S_std standardization per type, the scheduled-window policy from frozen_config, and five acceptance assertions (duplicate keys, calendar reconciliation, non-finite S_std, release-time/timezone slip, sample window). `parse_usmpd()` raises NeedInfo listing exactly what the owner must paste rather than guessing USMPD's columns |
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
| R1b parsers | **transform + assertions DONE** (`pipeline/surprises.py`, 20 tests); parse stage unimplemented BY DESIGN | R1a output + the owner paste-list in `R1b_input_requirements.md` |
| R2 panel/beta/lever build | **modules 2–3 built** (`build_betas.py`, `build_basket.py`, 26 tests; output passes A4/A7/A8/A9). Modules 1 & 4 need a price vendor | R1b; CRSP prices; holdings_weights口径 alignment with P1-T2 (manual §2.3 残余风险①) |
| R3 Gate-0 diagnostics | not started (DeepSeek + Sonnet 判读起草) | R2 `--sweep` output |
| GATE-PREREG | human | R3 gate_report |
| R4 OSF prereg | not started (Opus draft; human submits) | GATE-PREREG |
| R5 econometric design 双旗舰 | not started (GPT-5 × Opus, by hand) | R3 |
| R6 dual implementation Py/R | **guard-blocked by design** | OSF timestamp in frozen_config + GATE-e2verdict |
| R7 spines / R8 grid | not started | R6 |
| R9 creation baskets | `NEED_HUMAN`: ETF Global access at BU | — (bypass, non-blocking) |
| R10 TAQ pilot | not started (Claude Code) | R2 permno list (bypass, non-blocking) |
| R11 writing / R12 red team | not started | R7/R8 |
| R13 collision scan script | **scanner DONE** (`scan.py`, 23 tests, manifest); triage un-run | cron wiring (seat D) + a triage lane |
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
6. R0/R1a retrieval lane: the seat-C container's egress policy blocks every
   primary source (frbsf/federalreserve/bls/ssrn/doi/arxiv/s2) — both tasks
   need a web-capable lane or a widened allowlist (ops/decisions.md 2026-08-18).
7. **PI counter-signature** on the four Gate-0 decisions taken under delegation
   2026-08-19 (`DECISIONS-2026-08-19.md`): G4 mass share 0.50, G6 flatness
   (joint p ≥ 0.10 + Holm), the G2/G3 conflict resolution, and the sample frame
   (4 post-quarters → `waves_end` 2025-06-30, 53 waves). Recorded and
   machine-enforced; binding only once signed. Nothing downstream has run, so
   reversing any of them is still free.

Frozen P1 inputs (read-only, hash-registered when they exist): events_merged.csv,
conv_exposure.parquet, holdings_weights.parquet, ibes_sue.parquet.

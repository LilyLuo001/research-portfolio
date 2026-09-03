# docs/ — the design corpus and its precedence order

Every task brief says "paste the verbatim prompt from the manual/amendment".
This file says WHICH manual, and who wins when two documents disagree.

## The rule

Within a project, **later documents override earlier ones where they overlap;
where they don't overlap, the earlier document stays authoritative.** Across
all projects, `Agent_Architecture_24x7.md` §4 overrides every per-manual model
assignment (the budget remap), and each project's 研究计划/proposal is the
single source of truth for research substance (a prompt that conflicts with
the proposal is wrong — report the conflict, per each manual's C0/CONTEXT PACK).

## P1 — fund conversions

> **P1 does NOT follow the "later overrides earlier" rule above.** Its patch
> memos were **deleted** on 2026-09-03 (git history at `351d327` and earlier)
> because agents were reading them and executing superseded rules. There is no
> delta to reconstruct and nothing to diff. Read these two files and stop.

1. `基金转换实验_博士研究计划.md` — **the plan. Single source of truth for all
   research substance**, and already current: every amendment through 2026-09-03
   is merged into the body, with no version history left in it. If something you read anywhere else contradicts it,
   the plan wins and the conflict is a bug to report.
2. `Project_1.md` — execution manual: the five meta-rules, the CONTEXT PACK,
   the T0–T12 task prompts, §5 contracts, §6 rhythm. **Process only.** It was
   written 2026-07-10 against the v1.0 research design, so where it touches
   research substance — outcome variables, hypotheses, what T3/T5 estimate —
   it is stale and the plan overrides it.

Measured progress and current empirical inputs live in
`p1/STATUS-2026-09-03.md`, `p1/universe_v2/output/`, and `p1/exposure/`.
Implementation detail lives in `p1/t3_spec/变量规格书.md` (the D-T3-xx decision
table is the per-variable authority), `p1/t5_spec/估计蓝图.md`,
`p1/NON_WRDS_BLOCKERS.md`, and the executable guards in `p1/pipeline/` +
`p1/tests/test_spec_consistency.py`. The root `events_merged.csv` and
`conv_exposure_free.parquet` are legacy reconciliation baselines, not current
estimation inputs.

## E2 — RWA looping

1. `E2_研究计划_RWA内嵌杠杆.md` — the proposal (C0 declares it authoritative).
2. `E2_执行手册_Prompt与Agent指派.md` — manual **v1.0**. Still authoritative
   for: §0 routing philosophy + three iron laws, **the C0 context pack**
   (paste it verbatim at the top of every E2 prompt), the §0.4
   manifest/output contract, the **T1/T2/T3/T5 verbatim prompts** (v1.1 says
   "prompt 已在 v1.0" and does not restate them), and the §2 continuity
   matrix / anti-hallucination protocol.
3. `E2_执行手册_v1_1_完整版.md` — v1.1: adds the T4, T6–T14 prompts v1.0
   lacked, plus appendix A (capability review). **Supersedes v1.0 where they
   overlap** — notably: T11 must NOT use DeepSeek's API for web search (no
   native search) and 豆包 is restricted to mechanical checklist work (T14).
4. `E2_修订补丁_v1_2.md` — v1.2 patch: H1 downgraded / LP-on-monetary-shocks
   promoted, new T15 note, T9a productization clause, randomization-inference
   pre-commitment, model remap. Overrides both manuals where stated.

So: to brief an E2 task, take C0 from v1.0 §0.3, the task prompt from v1.0
(T1/T2/T3/T5) or v1.1 (T4, T6–T14) or v1.2 (T15), then apply any v1.2 prompt
modifications (T8a/T12/T13) and the Arch §4 model assignment.

## DAX — AI exposure

1. `DAX_ERE_Proposal_v3.md` — the proposal.
2. `DAX_Execution_Plan_with_AI_Agents.md` — execution plan: W0–W11 workstream
   prompts, agent roster, schedule, risk controls.
3. `DAX_Amendment_v1_1.md` — amendment: EIV workstream, δ calibration, W10a/b
   split, W0.5 feasibility gate, model remap. Overrides the plan where stated.

## Refraction — macro-event standby chapter

1. `MacroEvent_Chapter_Plan_v2_1_FINAL.md` — the plan (v2.1 final). Single
   source of truth for research substance, same standing as P1's 研究计划 and
   the DAX proposal; a prompt that conflicts with it is wrong.
2. `Refraction_执行手册_v1_0.md` — execution manual: §0.3 C0-R context pack
   (paste at the top of every REFR prompt), R0–R14 task prompts, §0.5 DAG,
   §2 Meta continuity audit.
3. `Refraction_Chapter_Plan_Amendment_v2_2.md` — amendment: sample scale
   recomputed from the built P1 inputs, wave-concentration finding, input
   contract corrections (`conv_exposure_free.parquet`, missing `permno`),
   post-2025 wave filter. **Overrides the plan where stated**; every item
   bearing on a pre-committed §9/§10 line is flagged `[PI-DECISION]` and
   changes nothing until the owner rules.

So: to brief a REFR task, take C0-R from the manual §0.3, the task prompt from
the manual's R-block, then apply any v2.2 amendment item and the Arch §4 model
assignment. Gate-0 thresholds always come from `refraction/frozen_config.yaml`,
never from a document and never from the model.

## Portfolio runtime

- `Agent_Architecture_24x7.md` — the four-layer runtime all three projects run
  inside. Its §4 master model table **supersedes every older per-task model
  assignment**; its §5 phase rotation drives queue.yaml's phasing.

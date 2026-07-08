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

1. `基金转换实验_博士研究计划.md` — the proposal (single source of truth; the
   CONTEXT PACK in the manual §3 declares it so).
2. `Project_1.md` — execution manual v1.0: five meta-rules, CONTEXT PACK,
   T0–T12 prompts, §5 contracts, §6 rhythm.
3. `P1_修订补丁_v1_1.md` — patch: T0 moved to week 0, new T2a and T13, T5
   Russell confound, §2 model remap. Overrides v1.0 where stated.

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

## Portfolio runtime

- `Agent_Architecture_24x7.md` — the four-layer runtime all three projects run
  inside. Its §4 master model table **supersedes every older per-task model
  assignment**; its §5 phase rotation drives queue.yaml's phasing.

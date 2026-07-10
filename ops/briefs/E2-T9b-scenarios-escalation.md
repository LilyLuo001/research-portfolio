# PRIME-BLOCK BRIEF — E2-T9b-scenarios (Anthropic-lane execution)

_hand-written 2026-07-10. Owner-directed lane change: the Wave-0 plan had
this on gemini_free (¥0, nightly driver), but the box's L1 lane is DOWN
(2026-07-10T02:03 inbox run failed before dispatch — `.venv/bin/python`
missing, no python3 module on the SCC; see ops/box/inbox_log.md) and the
owner asked for an execution-agent-ready batch. This task has NO
dual-channel pair, so an Anthropic run violates no cross-vendor constraint
(precedent: E2-T1-facts channel A, ops/l1/out/E2-T1-facts.json). If the
box lane comes back first and produces a clean gemini output, that output
wins and this brief is void._

- **project**: e2 — writes limited to `ops/l1/out/E2-T9b-scenarios.json`
  (+ lineage), nothing else in seat B's tree
- **worker**: Anthropic session with web retrieval (was: kimi ×strikes,
  then gemini_free never-dispatched)
- **depends_on**: none. **human gate**: false, but output feeds
  `scenarios.yaml` for T9a only after owner spot-check.

## the task
Stress-scenario calibration retrieval — 4 independent parameters, each
needing a first-hand source URL. Verbatim item prompts are in
`ops/l1/E2-T9b-scenarios.yaml` (items: clo-drawdown, private-credit-nav,
tbill-nav-move, defi-rate-spike). Discipline per prompt header: 一手来源
(监管报告、基金年报、学术论文、指数发布方); 无一手来源 → UNKNOWN; 禁止凭
记忆给数; 推断显式标注.

Known context: the kimi run answered all four UNKNOWN *and* missed both
sentinels (out/E2-T9b-scenarios.void.json) — all-UNKNOWN is an acceptable
honest outcome for the items, but only with the sentinels PASSING; the kimi
void shows what a dead retrieval channel looks like.

## sentinel protocol (fence integrity on the honor system)
Answer S1 and S2 from `ops/l1/E2-T9b-scenarios.yaml` by your OWN retrieval
BEFORE reading their `expect:` values, then compare and report honestly.
S2 (FalconX CV launch) is the exact fact a grounded gemini run got wrong
once — if you miss it, that is the fence working: record the failure,
write the void file, do NOT deliver parameter values.

## definition of done
- output at `ops/l1/out/E2-T9b-scenarios.json`, shaped like
  `ops/l1/out/E2-T1-facts.json`: top-level `_meta` (task, channel, worker,
  检索日期, sentinels incl. result, note) + one key per item id + `S1`/`S2`
- every value carries [参数, 建议取值区间, 一手来源URL(逐条), 来源类型,
  置信度, 备注] or is UNKNOWN with the search path in 备注
- lineage JSON emitted (`python ops/runner/lineage.py <output> <inputs...>`)
- branch `task/E2-T9b-scenarios`, merge → main,
  `python ops/runner/runner.py --complete E2-T9b-scenarios`
- no repo access? Return the JSON in-chat verbatim; the owner commits it.

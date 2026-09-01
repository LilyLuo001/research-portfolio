# YAX Phase 3 implementation-fix ledger

**POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.**

The binding pre-result implementation commit is `2683af26768c343af6060988689728d88878d568`. No specification, estimand, support rule, seed, draw count, component formula, classification threshold, or interpretation rule changed after that commit.

## Fix 1 — SCC interpreter path

The first launch used the legacy `.venv-old/bin/python`, which is Python 3.6.8 and stopped at parse time on `from __future__ import annotations`. The passing pytest wrapper's shebang identifies `/usr3/graduate/qluo/portfolio/.venv/bin/python` (Python 3.13.8). Execution was relaunched with that interpreter. No input file was read and no result was produced by the failed launch. No code or estimand changed.

## Fix 2 — Pandas `sample` attribute collision

The first computational run completed the two frozen hard-benchmark loops and wrote their JSON, then stopped before component classification, stock estimation, or joint inference. In `summarize_switch_components`, `f_rows.sample` resolved to the DataFrame method rather than the column named `sample`, raising `AttributeError: 'function' object has no attribute 'eq'`.

The first repair changed:

`f_rows.sample.eq(...)` → `f_rows["sample"].eq(...)`.

The underlying table, row selection, and all calculations are identical. A source regression test protects bracket access. The entire program is rerun from the beginning; the earlier partial hard-benchmark file is not reused.

The next full rerun exposed a second access to the same column in the immediately following direction-group selection: `result.sample.eq(...)`. It failed at the same stage, again before the stock or joint-inference exercises. That access is likewise replaced by `result["sample"].eq(...)`. The regression test now forbids any `.sample.eq` occurrence in the runner. The program is again rerun from the beginning without reusing either partial benchmark file.

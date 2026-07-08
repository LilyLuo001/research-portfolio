# ops/l1 — batch specs for the overnight L1 driver

`ops/runner/l1_driver.py` runs the cheap-model batches the scheduler marks READY.
For each ready L1 task it looks here for `ops/l1/<task_id>.yaml`. No file → the
task is "waiting for input" and is skipped (not failed).

A spec describes one sentinel-fenced batch:

```yaml
worker: kimi            # optional — defaults to the task's worker in queue.yaml
est_cost: 0.5           # ¥ estimate, for the budget pre-check
items:                  # the real batch (each needs a unique id)
  - {id: r001, prompt: "Verify: <issuer> NAV publish frequency? cite the doc."}
  - {id: r002, prompt: "..."}
sentinels:              # REQUIRED known-answer fence (drawn from YOUR domain)
  - {id: S1, prompt: "What is 2+2? number only.", expect: "4"}
  - {id: S2, prompt: "<a fact you already verified>", expect: "<its answer>"}
```

Output (the model's `id -> answer` map) is written to `ops/l1/out/<task_id>.json`.
`out/` is git-ignored — L1 output is **raw extraction**: a downstream code step
validates it against the task's `output_contract` and a human clears any gate
before the task is marked `--complete`. The driver never completes tasks itself.

Rules it enforces (CLAUDE.md §5, arch §3):
- **No sentinels → skipped.** Cheap models are only trusted inside a fence; if
  the sentinels come back wrong the whole batch is voided, not written.
- **Budget-capped.** Each batch is checked against the daily / per-vendor / monthly
  caps before it's sent (see `budget.py`).
- **Dual-channel** tasks are just two separate task ids (A + its `channel_of` B) —
  give each its own spec; they run independently on their two vendor families.

Run it:
```
python ops/runner/l1_driver.py           # dry-run — show what would run, no key
python ops/runner/l1_driver.py --live     # real dispatch on the box
```
Cron runs `--live` nightly (see ops/box/crontab).

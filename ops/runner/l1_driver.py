#!/usr/bin/env python3
"""
l1_driver.py — run the overnight L1 batches the scheduler says are ready.

This is what makes the box's cheap-model layer autonomous. Each night it asks the
runner which L1 tasks are READY (deps green, not gated, not already leased), and
for each one looks for a batch spec at ops/l1/<task_id>.yaml:

    worker:    (optional) override the queue's worker tier for this batch
    est_cost:  ¥ estimate for the budget pre-check
    items:     list of {id, prompt, ...} — the batch to send
    sentinels: list of {id, prompt, expect} — REQUIRED known-answer fence

It dispatches the batch (sentinel-fenced + budget-capped via dispatch.run_batch),
writes the answer map to ops/l1/out/<task_id>.json, and prints a per-task line.

Deliberately conservative:
  - A ready task with NO spec is "waiting for input" — skipped, not failed. (Its
    inputs are a task deliverable; the driver lights up when they exist.)
  - A spec with NO sentinels is skipped as unsafe — cheap models are only
    trustworthy inside a fence (CLAUDE.md rule 5 / arch §3).
  - It does NOT mark tasks complete. L1 output is RAW extraction; a downstream
    code step validates it against the task's contract and a human clears any
    gate. Completion stays an explicit, reviewed step.

  python ops/runner/l1_driver.py           # dry-run: show what would run (no key needed)
  python ops/runner/l1_driver.py --live     # real dispatch (on the box, keys set)
"""
import argparse, json, pathlib, sys
import yaml
import runner, dispatch, budget

ROOT = pathlib.Path(__file__).resolve().parents[2]
L1 = ROOT / "ops" / "l1"
OUT = L1 / "out"

_MARK = {"DONE": "✓", "VOID-SENTINEL": "✖", "SKIP-BUDGET": "⏸",
         "SKIP-NOKEY": "·", "ERROR": "✖"}


def ready_l1(q, state):
    """READY tasks whose worker is a cheap non-Anthropic vendor tier — i.e. the L1
    layer. Excludes Claude seats (code_pro/project_pro map to 'anthropic'),
    deterministic scripts (not a vendor family), and human gates."""
    ready = runner.ready_set(q, state)[0]
    vf = q["meta"]["vendor_families"]
    return [t for t in ready
            if vf.get(t.get("worker")) not in (None, "anthropic")
            and not t.get("human_gate")]


def run(live=False):
    q = runner.load(runner.RUN / "queue.yaml")
    state = runner.load_state()
    tasks = ready_l1(q, state)
    OUT.mkdir(parents=True, exist_ok=True)

    print(f"L1 driver — {len(tasks)} ready L1 task(s), mode={'LIVE' if live else 'dry-run'}")
    dispatched = 0
    for t in tasks:
        tid = t["id"]
        spec_path = L1 / f"{tid}.yaml"
        if not spec_path.exists():
            print(f"  · {tid:<20} waiting for input (create ops/l1/{tid}.yaml)")
            continue
        spec = yaml.safe_load(spec_path.read_text()) or {}
        sentinels = spec.get("sentinels")
        if not sentinels:
            print(f"  ✖ {tid:<20} SKIP: spec has no sentinels (unsafe without a fence)")
            continue
        worker = spec.get("worker", t["worker"])
        items = spec.get("items", [])
        est = float(spec.get("est_cost", 0.0))
        outp = OUT / f"{tid}.json"

        status, detail, _ = dispatch.run_batch(worker, items, sentinels,
                                               est_cost=est, live=live, out=str(outp))
        print(f"  {_MARK.get(status, '?')} {tid:<20} [{status}] {detail}")
        if status == "DONE":
            dispatched += 1

    if live:
        print(f"  spent today: {budget.today_spend():.3f} / {budget.DAILY_CAP:.0f} daily cap "
              f"(MTD {budget.mtd_spend():.1f} / {budget.MONTHLY_CAP:.0f})")
        print(f"  {dispatched} batch(es) written to ops/l1/out/ — validate + gate "
              f"downstream before --complete.")
    else:
        print(f"  {dispatched} batch(es) would run (dry-run writes nothing). "
              f"Run with --live on the box.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="run ready L1 batches (sentinel-fenced, budget-capped)")
    ap.add_argument("--live", action="store_true", help="actually POST (needs keys); default is dry-run")
    a = ap.parse_args()
    return run(live=a.live)


if __name__ == "__main__":
    sys.exit(main())

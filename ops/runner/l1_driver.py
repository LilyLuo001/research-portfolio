#!/usr/bin/env python3
"""
l1_driver.py — run the overnight L1 batches the scheduler says are ready.

This is what makes the box's cheap-model layer autonomous. Each night it asks the
runner which L1 tasks are READY (deps green, not gated, not already leased), and
for each one looks for a batch spec at ops/l1/<task_id>.yaml:

    worker:     (optional) override the queue's worker tier for this batch
    est_cost:   ¥ estimate for the budget pre-check
    web_search: true to enable Kimi's $web_search builtin round-trip
    manual:     true = human-run channel (Gemini web UI); driver skips it and
                ops/l1/gemini_helper.py produces the output instead
    items:      list of {id, prompt, ...} — the batch to send
    sentinels:  list of {id, prompt, expect} — REQUIRED known-answer fence

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
  - A task whose output ops/l1/out/<task_id>.json already exists is NOT re-sent
    (a still-open task would otherwise re-bill every night). Re-arm a batch by
    deleting its output (or --force to re-run everything ready).
  - VOID-SENTINEL in live mode records a failed attempt in state.json
    (runner --fail), so two bad nights surface the task in the ESCALATED section
    of the plan and digest (arch §3 two-strike ladder). ERROR (HTTP / quota /
    billing) does NOT strike — it isn't evidence about the model's work — and a
    DONE clears any stale strikes. Reset counters by hand with
    `runner.py --clear-fail <task>` (e.g. after fixing vendor billing).

Each run writes ops/l1/out/_last_night.json (per-task statuses); the evening
digest folds it into the "overnight L1 results" section (arch §2 L3 item ①).

  python ops/runner/l1_driver.py           # dry-run: show what would run (no key needed)
  python ops/runner/l1_driver.py --live     # real dispatch (on the box, keys set)
"""
import argparse, datetime, json, pathlib, sys
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


def run(live=False, force=False):
    q = runner.load(runner.RUN / "queue.yaml")
    state = runner.load_state()
    tasks = ready_l1(q, state)
    OUT.mkdir(parents=True, exist_ok=True)

    print(f"L1 driver — {len(tasks)} ready L1 task(s), mode={'LIVE' if live else 'dry-run'}")
    dispatched = 0
    night = {}
    for t in tasks:
        tid = t["id"]
        spec_path = L1 / f"{tid}.yaml"
        outp = OUT / f"{tid}.json"
        if not spec_path.exists():
            print(f"  · {tid:<20} waiting for input (create ops/l1/{tid}.yaml)")
            night[tid] = "NO-SPEC"
            continue
        if outp.exists() and not force:
            print(f"  ✓ {tid:<20} output already at {outp.name} — not re-sending "
                  f"(validate + --complete it, or delete the file / --force to re-run)")
            night[tid] = "HAS-OUTPUT"
            continue
        spec = yaml.safe_load(spec_path.read_text()) or {}
        if spec.get("manual"):
            # human-run channel (e.g. Gemini web UI grounding, not wired in
            # models.py) — never auto-dispatch; gemini_helper.py owns it.
            print(f"  · {tid:<20} manual channel — run: python ops/l1/gemini_helper.py {tid}")
            night[tid] = "MANUAL"
            continue
        sentinels = spec.get("sentinels")
        if not sentinels:
            print(f"  ✖ {tid:<20} SKIP: spec has no sentinels (unsafe without a fence)")
            night[tid] = "NO-SENTINELS"
            continue
        worker = spec.get("worker", t["worker"])
        items = spec.get("items", [])
        est = float(spec.get("est_cost", 0.0))

        status, detail, _ = dispatch.run_batch(worker, items, sentinels,
                                               est_cost=est, live=live, out=str(outp),
                                               web_search=bool(spec.get("web_search")),
                                               max_items_per_call=spec.get("max_items_per_call"))
        print(f"  {_MARK.get(status, '?')} {tid:<20} [{status}] {detail}")
        night[tid] = status
        if status == "DONE":
            dispatched += 1
            if live:
                runner.cmd_clear_fail(tid, quiet=True)   # success wipes stale strikes
        elif live and status == "VOID-SENTINEL":
            # Only a tripped fence strikes: the model completed and failed the
            # known-answer check. ERROR (HTTP/quota/billing) says nothing about
            # the model's work — it stays visible in the night report + digest
            # but must not burn the task's two-strike ladder.
            runner.cmd_fail(tid)

    if live or force:
        (OUT / "_last_night.json").write_text(json.dumps(
            {"date": datetime.date.today().isoformat(), "live": live,
             "results": night}, indent=2))

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
    ap.add_argument("--force", action="store_true",
                    help="re-run tasks even if their output already exists")
    a = ap.parse_args()
    return run(live=a.live, force=a.force)


if __name__ == "__main__":
    sys.exit(main())

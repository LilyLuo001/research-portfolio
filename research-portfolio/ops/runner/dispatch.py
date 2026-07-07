#!/usr/bin/env python3
"""
dispatch.py — the L1 overnight layer. Runs on your always-on box under NO Claude
credential; talks only to the cheap non-Anthropic APIs via models.py, under each
vendor's own commercial terms (see ops/COMPLIANCE.md). This is the half of the
architecture that is actually 24/7.

It ties together the three pieces the box needs:
  - models.py   : the thin per-vendor client (dry-run until keys are set)
  - budget.py   : the 80%-of-envelope hard stop, so a runaway loop can't overspend
  - sentinels   : known-answer items mixed into every batch; if the model misses
                  them the WHOLE batch is voided rather than poisoning downstream.

Usage:
  python ops/runner/dispatch.py --smoke          # keyless end-to-end self-test (SH-l1-smoke)
  python ops/runner/dispatch.py --task E2-T6b-nav --items items.jsonl   # real batch
  python ops/runner/dispatch.py --workers                              # show which keys are live

A batch is COMPLETE only if (a) budget allowed it, (b) every sentinel came back
correct. Anything else prints VOID and writes nothing downstream.
"""
import argparse, json, os, sys, pathlib
import models, budget

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Two known-answer sentinels. In a real batch these are drawn from the task's own
# domain (a holding you already verified, an event whose date you know); here they
# are trivially checkable so the fence itself can be tested without a live model.
SMOKE_SENTINELS = [
    {"id": "S1", "prompt": "Reply with exactly: 2+2", "expect": "4"},
    {"id": "S2", "prompt": "Reply with exactly: capital of France", "expect": "Paris"},
]


def worker_status():
    """Which L1 vendors have a key present in the environment (box-only .env)."""
    out = {}
    for worker, (key_env, _url) in models.ENDPOINTS.items():
        out[worker] = bool(os.getenv(key_env))
    return out


def _answer_sentinels(result, sentinels, corrupt=False):
    """Extract this batch's sentinel answers. On a live run this parses `result`;
    in dry-run there is no model output, so we simulate the correct answers (or a
    corrupted one when `corrupt` is set, to prove the fence actually voids)."""
    answers = {}
    for i, s in enumerate(sentinels):
        if corrupt and i == 0:
            answers[s["id"]] = "WRONG"
        else:
            answers[s["id"]] = s["expect"]
    return answers


def sentinels_pass(sentinels, answers):
    bad = [s["id"] for s in sentinels
           if answers.get(s["id"], "").strip() != s["expect"]]
    return (len(bad) == 0), bad


def run_batch(worker, items, sentinels, est_cost=0.0, live=False, _corrupt=False):
    """Dispatch one sentinel-fenced batch. Returns (status, detail).
    status in {'DONE','VOID-SENTINEL','SKIP-BUDGET','SKIP-NOKEY'}."""
    key_env, _url = models.ENDPOINTS[worker]
    if live and not os.getenv(key_env):
        return "SKIP-NOKEY", f"{worker}: no {key_env} in env"
    if live:
        ok, why = budget.can_dispatch(worker, est_cost)
        if not ok:
            return "SKIP-BUDGET", f"{worker}: {why}"

    fenced = items + [{"id": s["id"], "prompt": s["prompt"]} for s in sentinels]
    prompt = json.dumps(fenced, ensure_ascii=False)
    ok, result = models.dispatch(worker, prompt, sentinels=sentinels, dry_run=not live)

    answers = _answer_sentinels(result, sentinels, corrupt=_corrupt)
    passed, bad = sentinels_pass(sentinels, answers)
    if not passed:
        return "VOID-SENTINEL", f"{worker}: sentinels failed {bad} — batch discarded"

    if live:
        budget.log(worker, est_cost)
    mode = "LIVE" if live else "dry-run"
    return "DONE", f"{worker}: {len(items)} items + {len(sentinels)} sentinels OK ({mode})"


def cmd_smoke():
    """SH-l1-smoke: one sentinel-fenced dummy batch end-to-end against every L1
    worker, keyless (dry-run). Also proves the fence voids a corrupted batch."""
    st = worker_status()
    print("L1 worker keys present:", {w: ("yes" if v else "no") for w, v in st.items()})
    dummy = [{"id": "d1", "prompt": "echo ok"}]
    print("\n▶ dry-run batch per worker (proves the dispatch path + sentinel fence):")
    failures = 0
    for worker in models.ENDPOINTS:
        status, detail = run_batch(worker, dummy, SMOKE_SENTINELS, live=False)
        print(f"   [{status:>13}] {detail}")
        if status not in ("DONE",):
            failures += 1

    print("\n▶ negative control (inject a wrong sentinel — MUST void):")
    status, detail = run_batch("deepseek", dummy, SMOKE_SENTINELS, live=False, _corrupt=True)
    print(f"   [{status:>13}] {detail}")
    fence_works = (status == "VOID-SENTINEL")

    print()
    if failures == 0 and fence_works:
        print("✓ SH-l1-smoke PASS — every worker dispatches and the sentinel fence voids bad batches.")
        return 0
    print("✖ SH-l1-smoke FAIL — see above.")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="keyless end-to-end self-test")
    ap.add_argument("--workers", action="store_true", help="show which L1 keys are live")
    ap.add_argument("--task", help="task id this batch feeds")
    ap.add_argument("--worker", help="which L1 vendor to dispatch to")
    ap.add_argument("--items", help="path to a JSONL of batch items")
    ap.add_argument("--cost", type=float, default=0.0, help="estimated ¥ cost of this batch")
    ap.add_argument("--live", action="store_true", help="actually POST (needs the key + models.py wired)")
    a = ap.parse_args()

    if a.smoke:
        return cmd_smoke()
    if a.workers:
        for w, live in worker_status().items():
            print(f"{w:<12} {'LIVE' if live else 'no key'}")
        return 0
    if a.worker and a.items:
        items = [json.loads(l) for l in pathlib.Path(a.items).read_text().splitlines() if l.strip()]
        status, detail = run_batch(a.worker, items, SMOKE_SENTINELS, est_cost=a.cost, live=a.live)
        print(f"[{status}] {detail}")
        return 0 if status == "DONE" else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

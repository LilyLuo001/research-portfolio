#!/usr/bin/env python3
"""
dispatch.py — the L1 overnight layer. Runs on your always-on box under NO Claude
credential; talks only to the cheap non-Anthropic APIs via models.py, under each
vendor's own commercial terms (see ops/COMPLIANCE.md). This is the half of the
architecture that is actually 24/7.

It ties together the pieces the box needs:
  - models.py : per-vendor client (real POST when a key is set; dry-run otherwise)
  - budget.py : monthly + daily + per-vendor caps, checked before each live batch
  - sentinels : known-answer items mixed into every batch; if the model misses
                them the WHOLE batch is voided rather than poisoning downstream.

Usage:
  python ops/runner/dispatch.py --smoke                     # keyless self-test (SH-l1-smoke)
  python ops/runner/dispatch.py --workers                   # which keys are live
  python ops/runner/dispatch.py --worker kimi --items batch.jsonl --live \
         --cost 0.5 --out answers.json                      # one real batch

A batch is COMPLETE only if (a) budget allowed it, (b) every sentinel came back
correct. Anything else prints VOID/SKIP/ERROR and writes nothing downstream.
Each JSONL item in --items is an object with at least an "id" and a "prompt".
"""
import argparse, json, os, sys, pathlib
import models, budget

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Trivially-checkable sentinels for the keyless self-test. In a real batch these
# are drawn from the task's own domain (a holding you already verified, an event
# whose date you know) so the fence proves the model handled real content.
SMOKE_SENTINELS = [
    {"id": "S1", "prompt": "What is 2+2? Reply with only the number.", "expect": "4"},
    {"id": "S2", "prompt": "What is the capital of France? Reply with only the city name.",
     "expect": "Paris"},
]


def worker_status():
    """Which L1 vendors have a key present in the environment (box-only .env)."""
    return {w: bool(os.getenv(env)) for w, (env, _u) in models.ENDPOINTS.items()}


def build_prompt(items, sentinels):
    """One batch prompt: the real items plus the sentinels, as a JSON array. The
    model is asked (by models.SYSTEM) to return an id -> answer JSON object."""
    fenced = list(items) + [{"id": s["id"], "prompt": s["prompt"]} for s in sentinels]
    return json.dumps(fenced, ensure_ascii=False)


def _simulate_answers(items, sentinels, corrupt=False):
    """Dry-run only: fabricate a correct answer map (or a wrong sentinel, to prove
    the fence voids a bad batch) so the harness runs offline with no key."""
    ans = {it["id"]: "ok" for it in items}
    for i, s in enumerate(sentinels):
        ans[s["id"]] = "WRONG" if (corrupt and i == 0) else s["expect"]
    return ans


def run_batch(worker, items, sentinels, est_cost=0.0, live=False, _corrupt=False, out=None,
              web_search=False):
    """Dispatch one sentinel-fenced batch.
    Returns (status, detail, answers) with status in
    {DONE, VOID-SENTINEL, SKIP-BUDGET, SKIP-NOKEY, ERROR}."""
    key_env, _url = models.ENDPOINTS[worker]
    if live and not os.getenv(key_env):
        return "SKIP-NOKEY", f"{worker}: no {key_env} in env", None
    if live:
        ok, why = budget.can_dispatch(worker, est_cost)   # pre-check with your estimate
        if not ok:
            return "SKIP-BUDGET", f"{worker}: {why}", None

    prompt = build_prompt(items, sentinels)
    ok, res = models.dispatch(worker, prompt, sentinels=sentinels, dry_run=not live,
                              web_search=web_search)
    if not ok:
        return "ERROR", f"{worker}: {res.get('error', 'dispatch failed')}", None

    if live:
        answers = models.parse_answers(res["text"])
        cost = models.estimate_cost(worker, res.get("usage"))
        budget.log(worker, cost)      # tokens are billed whether or not the fence passes
    else:
        answers = _simulate_answers(items, sentinels, corrupt=_corrupt)
        cost = 0.0

    passed, bad = models.verify_sentinels(answers, sentinels)
    if not passed:
        why = f"sentinels failed {bad}"
        if live and res.get("finish_reason") == "length":
            why = (f"reply TRUNCATED at the output-token cap before the "
                   f"sentinels (finish_reason=length; missed {bad})")
        elif live and not answers:
            why = "reply had no parseable JSON answer-map (all sentinels void)"
        if live and out:
            # discarded downstream, but keep the raw reply for the morning
            # post-mortem — a voided batch you can't inspect can't be fixed.
            void = pathlib.Path(out).with_suffix(".void.json")
            void.write_text(json.dumps(
                {"worker": worker, "bad_sentinels": bad, "parsed_answers": answers,
                 "finish_reason": res.get("finish_reason"),
                 "raw_text": res["text"], "usage": res.get("usage", {})},
                ensure_ascii=False, indent=2))
            why += f" — raw reply kept at {void.name}"
        return "VOID-SENTINEL", f"{worker}: {why} — batch discarded", None

    if live:
        if out:
            pathlib.Path(out).write_text(json.dumps(answers, ensure_ascii=False, indent=2))

    mode = f"LIVE ¥{cost:.3f}" if live else "dry-run"
    return "DONE", f"{worker}: {len(items)} items + {len(sentinels)} sentinels OK ({mode})", answers


def cmd_smoke():
    """SH-l1-smoke: one sentinel-fenced dummy batch per L1 worker, keyless
    (dry-run), plus a negative control proving the fence voids a bad batch."""
    st = worker_status()
    print("L1 worker keys present:", {w: ("yes" if v else "no") for w, v in st.items()})
    dummy = [{"id": "d1", "prompt": "echo ok"}]
    print("\n▶ dry-run batch per worker (proves the dispatch path + sentinel fence):")
    failures = 0
    for worker in models.ENDPOINTS:
        status, detail, _ = run_batch(worker, dummy, SMOKE_SENTINELS, live=False)
        print(f"   [{status:>13}] {detail}")
        if status != "DONE":
            failures += 1

    print("\n▶ negative control (inject a wrong sentinel — MUST void):")
    status, detail, _ = run_batch("deepseek", dummy, SMOKE_SENTINELS, live=False, _corrupt=True)
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
    ap.add_argument("--worker", help="which L1 vendor to dispatch to")
    ap.add_argument("--items", help="path to a JSONL of batch items ({id, prompt, ...})")
    ap.add_argument("--sentinels", help="JSONL of DOMAIN known-answer items ({id, prompt, expect}) "
                                        "— required for a meaningful fence on real batches")
    ap.add_argument("--cost", type=float, default=0.0, help="estimated ¥ cost (budget pre-check)")
    ap.add_argument("--out", help="write the answer map to this path on success")
    ap.add_argument("--live", action="store_true", help="actually POST (needs the key set)")
    a = ap.parse_args()

    if a.smoke:
        return cmd_smoke()
    if a.workers:
        for w, live in worker_status().items():
            print(f"{w:<12} {'LIVE' if live else 'no key'}")
        return 0
    if a.worker and a.items:
        items = [json.loads(l) for l in pathlib.Path(a.items).read_text().splitlines() if l.strip()]
        if a.sentinels:
            sentinels = [json.loads(l) for l in
                         pathlib.Path(a.sentinels).read_text().splitlines() if l.strip()]
        else:
            sentinels = SMOKE_SENTINELS
            if a.live:
                print("WARNING: live batch with only the trivial smoke sentinels — "
                      "the fence proves dispatch works, NOT that the model handled "
                      "your domain content. Pass --sentinels with known-answer "
                      "items drawn from this task's own data.")
        status, detail, _ = run_batch(a.worker, items, sentinels,
                                      est_cost=a.cost, live=a.live, out=a.out)
        print(f"[{status}] {detail}")
        return 0 if status == "DONE" else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

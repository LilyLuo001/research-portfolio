#!/usr/bin/env python3
"""
gemini_helper.py — the human API for manual Gemini specs (the FALLBACK path).

Gemini grounding IS wired in models.py (google_search tool), so channel-B
tasks normally auto-dispatch through the nightly driver. Mark a spec
`manual: true` to route it here instead — when the free grounding quota is
exhausted, GEMINI_API_KEY is absent, or a task needs documents uploaded into
the web UI (e.g. issuer legal files for E2-T6b-nav). This script does
everything around that one copy-paste:

  1. finds the manual specs whose queue task is READY and has no output yet;
  2. prints the exact, complete prompt — ops/l1/C0.md (the shared context
     pack, verbatim from the E2 v1.0 manual §0.3) + the spec's rules + every
     item AND sentinel as a numbered list — for you to copy into Gemini;
  3. waits for you to paste Gemini's raw reply back (finish with a line
     containing only END);
  4. parses the id→answer JSON out of the paste (tolerates prose/fences),
     verifies the sentinel fence, and only then writes
     ops/l1/out/<task_id>.json — the same schema dispatch.py writes, so the
     driver sees HAS-OUTPUT and downstream validation proceeds normally.

The raw paste is always kept at ops/l1/out/<task_id>.gemini-raw.txt (out/ is
box-local, gitignored) so a failed parse or tripped fence loses nothing.

Like the driver, this does NOT mark the task complete — validate the output
against its contract and run `python ops/runner/runner.py --complete <task>`
as the explicit, reviewed step.

  python ops/l1/gemini_helper.py              # list pending manual tasks
  python ops/l1/gemini_helper.py <task_id>    # run one task interactively
  python ops/l1/gemini_helper.py --all        # run every pending one in turn
"""
import argparse, json, pathlib, sys

import yaml

L1 = pathlib.Path(__file__).resolve().parent
ROOT = L1.parents[1]
OUT = L1 / "out"
sys.path.insert(0, str(ROOT / "ops" / "runner"))
import models, runner  # noqa: E402

C0_PATH = L1 / "C0.md"

ANSWER_FORMAT = (
    "回答格式(硬性): 逐条回答下面每一个条目(含 S 开头的核对条目)。最终输出\n"
    "一个单一 JSON 对象, 键 = 条目 id, 值 = 该条目的完整回答(字符串, 内部可用\n"
    "Markdown 表格/换行)。除这个 JSON 对象外不要输出任何其他文本。示例:\n"
    '{"t1a-oracles": "…完整回答…", "S1": "2025-08"}'
)


def load_spec(tid):
    p = L1 / f"{tid}.yaml"
    if not p.exists():
        return None
    return yaml.safe_load(p.read_text()) or {}


def pending_manual_tasks():
    """Manual-spec tasks that are READY in the queue and have no output yet.
    Returns [(task_id, spec, reason_if_blocked)] for everything with a manual
    spec so the listing can also explain why something is NOT runnable."""
    q = runner.load(runner.RUN / "queue.yaml")
    state = runner.load_state()
    ready_ids = {t["id"] for t in runner.ready_set(q, state)[0]}
    rows = []
    for p in sorted(L1.glob("*.yaml")):
        spec = yaml.safe_load(p.read_text()) or {}
        if not spec.get("manual"):
            continue
        tid = p.stem
        if (OUT / f"{tid}.json").exists():
            rows.append((tid, spec, "done (output exists — delete it to re-run)"))
        elif tid not in ready_ids:
            rows.append((tid, spec, "blocked (queue deps not green yet)"))
        else:
            rows.append((tid, spec, None))
    return rows


def build_prompt(tid, spec):
    """The complete text to paste into the Gemini web UI: C0 + task rules +
    every item and sentinel, plus the strict answer-format contract."""
    c0 = C0_PATH.read_text().strip()
    parts = [c0, ""]
    note = (spec.get("manual_note") or "").strip()
    if note:
        parts += [f"【任务 {tid} · 人工执行须知】", note, ""]
    parts += [ANSWER_FORMAT, "", "条目清单:"]
    fenced = list(spec.get("items", [])) + [
        {"id": s["id"], "prompt": s["prompt"]} for s in spec.get("sentinels", [])]
    for it in fenced:
        parts += [f"--- id: {it['id']} ---", str(it["prompt"]).strip(), ""]
    return "\n".join(parts)


def read_paste():
    print("Paste Gemini's raw reply below. When done, type END on a line by itself:")
    print("-" * 72)
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def run_task(tid, spec):
    items = spec.get("items", [])
    sentinels = spec.get("sentinels", [])
    outp = OUT / f"{tid}.json"
    OUT.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print(f"TASK {tid} — copy EVERYTHING between the markers into the Gemini web UI")
    if spec.get("web_search"):
        print("        (turn grounding / web search ON in the UI for this task)")
    print("=" * 72)
    print(build_prompt(tid, spec))
    print("=" * 72)

    raw = read_paste()
    rawp = OUT / f"{tid}.gemini-raw.txt"
    rawp.write_text(raw)
    if not raw.strip():
        print(f"✖ {tid}: empty paste — nothing saved (raw kept at {rawp}).")
        return False

    answers = models.parse_answers(raw)
    if not answers:
        print(f"✖ {tid}: could not find a JSON id→answer object in the paste — "
              f"nothing saved. Ask Gemini to re-emit ONLY the JSON object, then "
              f"re-run this task (raw kept at {rawp}).")
        return False

    missing = [it["id"] for it in items if it["id"] not in answers]
    if missing:
        print(f"⚠ {tid}: answers missing for item(s): {', '.join(missing)}")
        if input("  save anyway? [y/N] ").strip().lower() != "y":
            print(f"  not saved (raw kept at {rawp}).")
            return False

    ok, bad = models.verify_sentinels(answers, sentinels)
    if not ok:
        print(f"✖ {tid}: sentinel fence FAILED on {bad} — output NOT saved "
              f"(CLAUDE.md rule 5: a batch that misses known answers is not "
              f"trustworthy). Raw kept at {rawp} for post-mortem.")
        return False

    outp.write_text(json.dumps(answers, ensure_ascii=False, indent=2))
    print(f"✓ {tid}: {len(items)} item(s) + {len(sentinels)} sentinel(s) OK → {outp}")
    print(f"  Next: validate downstream, then `python ops/runner/runner.py --complete {tid}`.")
    return True


def main():
    ap = argparse.ArgumentParser(description="human-run Gemini channel: print prompt, "
                                             "paste reply, verify, save")
    ap.add_argument("task_id", nargs="?", help="manual task to run (omit to list)")
    ap.add_argument("--all", action="store_true", help="run every pending manual task in turn")
    a = ap.parse_args()

    rows = pending_manual_tasks()
    if not rows:
        print("No manual (Gemini web UI) specs found in ops/l1/.")
        return 0

    if a.task_id:
        spec = load_spec(a.task_id)
        if spec is None or not spec.get("manual"):
            print(f"✖ {a.task_id}: no manual spec at ops/l1/{a.task_id}.yaml")
            return 1
        blocked = next((r for t, s, r in rows if t == a.task_id), None)
        if blocked:
            print(f"⚠ {a.task_id} is {blocked}")
            if input("  run anyway? [y/N] ").strip().lower() != "y":
                return 1
        return 0 if run_task(a.task_id, spec) else 1

    runnable = [(t, s) for t, s, r in rows if r is None]
    if not a.all:
        print("Manual Gemini tasks:")
        for tid, _spec, reason in rows:
            print(f"  {'·' if reason else '▶'} {tid:<20} {reason or 'PENDING — ready to run'}")
        if runnable:
            print(f"\nRun one:  python ops/l1/gemini_helper.py {runnable[0][0]}")
            print("Run all:  python ops/l1/gemini_helper.py --all")
        return 0

    if not runnable:
        print("Nothing pending — every manual task is done or blocked.")
        return 0
    failures = 0
    for tid, spec in runnable:
        if not run_task(tid, spec):
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

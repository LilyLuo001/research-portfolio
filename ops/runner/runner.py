#!/usr/bin/env python3
"""
runner.py — deterministic backbone for the P1/E2/DAX portfolio.

This is the L0 layer. It runs 24/7 on your own always-on box under NO Claude
credential. It does four things and nothing else:

  1. compute the READY set from queue.yaml (deps' contracts pass, gate cleared)
  2. assign each ready L2 task to the ONE seat that owns it (no two seats can
     ever get the same task — leases + ownership guarantee it)
  3. plan L1 dispatch (cheap China-model batches) for the overnight shift
  4. emit prepared briefs + a daily digest for your 30 human minutes

It NEVER calls a Claude subscription. L2 tasks become briefs you paste into the
official app on the owning account. L1 tasks would be dispatched by models.py
(own API keys, own commercial terms) — stubbed here as dry-run.

Usage:
  python runner.py --plan                 # show ready set + assignment (offline)
  python runner.py --brief DAX-W5-index   # write ops/briefs/DAX-W5-index.md
  python runner.py --digest               # write ops/digest/<date>.md
  python runner.py --complete E2-T6a-panel  # mark done (AFTER contracts.py passed)
  python runner.py --fail E2-T4b-impl     # record a failed attempt (2-strike ladder)
  python runner.py --apply-decisions      # apply gate verdicts from ops/decisions.md
  python runner.py --reap                 # expire stale leases

State (completed / gates / attempts) lives in ops/runner/state.json and is
GIT-TRACKED: the repo is the only shared state, so a fresh seat clone must see
what is already done or the runner would re-assign finished work.
"""
import argparse, json, os, sys, datetime, pathlib, subprocess
import yaml
import budget

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUN = ROOT / "ops" / "runner"
LEASES = ROOT / "ops" / "leases"
BRIEFS = ROOT / "ops" / "briefs"
DIGEST = ROOT / "ops" / "digest"
STATE = RUN / "state.json"

def load(p):
    with open(p) as f:
        return yaml.safe_load(f)

def load_state():
    s = json.loads(STATE.read_text()) if STATE.exists() else {}
    s.setdefault("completed", [])
    s.setdefault("gates_cleared", [])
    s.setdefault("gates_failed", [])
    s.setdefault("attempts", {})       # task id -> failed-attempt count (two-strike ladder)
    return s

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

def live_leases():
    now = datetime.datetime.utcnow()
    live = {}
    for f in LEASES.glob("*.lease"):
        try:
            d = json.loads(f.read_text())
            exp = datetime.datetime.fromisoformat(d["expires_at"])
            if exp > now:
                live[d["task"]] = d
        except Exception:
            continue
    return live

def remote_task_branches():
    """In-flight lease signal read straight from the shared git remote.

    Every seat works task <id> on branch `task/<id>` (CLAUDE.md, lease.py). So an
    OPEN `task/<id>` branch on origin means some seat — possibly on a different
    machine or Pro account — is already on that task. Treating the branch
    namespace itself as a lease closes the one gap the local .lease files can't:
    two seats that never share a filesystem still can't be handed the same task.

    `--plan` is documented as offline-friendly, so any failure (no network, no
    remote, git absent) degrades silently to "" and we fall back to local leases.
    Merged branches are irrelevant: a completed task is filtered by `state` before
    the leased check, so a leftover merged `task/<id>` branch never blocks anything.
    """
    try:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "ls-remote", "--heads", "origin", "task/*"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return set()
    if r.returncode != 0:
        return set()
    prefix = "refs/heads/task/"
    ids = set()
    for line in r.stdout.splitlines():
        ref = line.split("\t")[-1].strip()      # "<sha>\trefs/heads/task/<id>"
        if ref.startswith(prefix):
            ids.add(ref[len(prefix):])
    return ids

# ---------------------------------------------------------------------------

def index_tasks(q):
    return {t["id"]: t for t in q["tasks"]}

def deps_satisfied(t, done):
    return all(d in done for d in t.get("depends_on", []) or [])

def escalations(q, state):
    """Tasks whose failed-attempt count hit max_attempts: the two-strike ladder
    (arch §3 rule 4). They stay READY but must be re-assigned one tier up —
    L1 workers escalate to the next L1 tier or a Claude Code block on seat D;
    a failed L2 task escalates to the human."""
    out = []
    for t in q["tasks"]:
        n = state["attempts"].get(t["id"], 0)
        if n >= t.get("max_attempts", 2) and t["id"] not in state["completed"]:
            out.append((t, n))
    return out


def ready_set(q, state):
    tasks = index_tasks(q)
    done = set(state["completed"])
    gates = set(state["gates_cleared"])
    # A task is "leased" if a local .lease file is live OR an open task/<id>
    # branch exists on the remote. The branch namespace IS the lease, so two
    # seats on different machines/accounts can never be assigned the same task.
    branch_leases = remote_task_branches()
    leased = set(live_leases().keys()) | branch_leases
    ready, gated, blocked = [], [], []
    in_flight = []                         # not-yet-done tasks someone already holds
    for t in q["tasks"]:
        tid = t["id"]
        if tid in done:
            continue
        if not deps_satisfied(t, done):
            blocked.append(tid); continue
        # a human_gate task that isn't cleared is surfaced to the human, not assigned
        if t.get("human_gate") and tid not in gates:
            gated.append(tid); continue
        if tid in leased:
            in_flight.append(tid)
            continue
        ready.append(t)
    return ready, gated, blocked, in_flight

def vendor_of(worker, q):
    return q["meta"]["vendor_families"].get(worker, "unknown")

def check_cross_vendor(q):
    """Every channel_of B-task must be a different vendor family than its A-task."""
    tasks = index_tasks(q)
    problems = []
    for t in q["tasks"]:
        a = t.get("channel_of")
        if not a:
            continue
        at = tasks.get(a)
        if not at:
            problems.append(f"{t['id']}: channel_of {a} not found"); continue
        if vendor_of(t["worker"], q) == vendor_of(at["worker"], q):
            problems.append(f"{t['id']} and its A-channel {a} share vendor "
                            f"'{vendor_of(t['worker'], q)}' — independence violated")
    return problems

def assign(ready, accounts, q):
    """Deterministic seat assignment. L2 -> owning seat; L1 -> overnight dispatch."""
    seats = accounts["seats"]
    prio = {p: i for i, p in enumerate(q["meta"]["priority_order"])}
    def key(t):  # dax before e2 before p1
        return prio.get(t["project"], 99)
    ready = sorted(ready, key=key)

    l2, l1 = [], []
    busy = set()
    for t in ready:
        if t["worker"] in ("code_pro", "project_pro"):
            seat = t.get("owner_account")
            chosen = None
            # 1. concrete owner seat, if idle
            if seat in seats and seat not in busy:
                chosen = seat
            # 2. writing/judgment floater (E) may absorb ANY project's project_pro
            #    task when the owner seat is busy — only one project writes at a
            #    time (arch §5), and it lands on a task branch, merged after review.
            elif t["worker"] == "project_pro" and "E" in seats and "E" not in busy:
                chosen = "E"
            # 3. null-owner escalations/arbitration float to D (infra/escalation).
            elif seat in (None, "float", "D") and "D" in seats and "D" not in busy:
                chosen = "D"
            if chosen:
                busy.add(chosen)
                l2.append((t, chosen))
            else:
                l2.append((t, f"WAIT(seat {seat} busy)"))   # portfolio never blocks; task queues
        elif t["worker"] == "script":
            l1.append((t, "L0-script"))
        else:
            l1.append((t, f"L1:{t['worker']}"))
    return l2, l1

# ---------------------------------------------------------------------------

def cmd_plan(q, accounts):
    state = load_state()
    ready, gated, blocked, in_flight = ready_set(q, state)
    problems = check_cross_vendor(q)
    l2, l1 = assign(ready, accounts, q)

    print("=" * 70)
    print(f"PORTFOLIO PLAN  ({datetime.date.today()})   "
          f"completed={len(state['completed'])}  ready={len(ready)}  "
          f"in_flight={len(in_flight)}  gated={len(gated)}  blocked={len(blocked)}")
    print("=" * 70)
    print("\n▶ L2 — human-driven prime blocks (each on its OWNED seat, no collision):")
    if not l2: print("   (none ready)")
    for t, seat in l2:
        print(f"   [{seat:>18}]  {t['id']:<20} {t['worker']:<12} :: {t.get('notes','')[:52]}")
    print("\n▶ L1 — overnight cheap-model / script batches (own API keys, 24/7):")
    if not l1: print("   (none ready)")
    for t, tag in l1:
        print(f"   [{tag:>12}]  {t['id']:<20} :: {t.get('notes','')[:56]}")
    print("\n▷ IN FLIGHT — a seat already holds these (live lease or open task/<id> branch):")
    if not in_flight: print("   (none)")
    for tid in in_flight: print(f"   ↻ {tid}")
    print("\n⏸ HUMAN GATES waiting on you (branch parked, portfolio still moving):")
    for g in gated: print(f"   ⚑ {g}")
    esc = escalations(q, state)
    if esc:
        print("\n⇧ ESCALATED (two-strike ladder — re-assign one tier up / seat D):")
        for t, n in esc:
            print(f"   ⇧ {t['id']:<20} {n} failed attempts on '{t['worker']}'")
    if problems:
        print("\n✖ CROSS-VENDOR INDEPENDENCE PROBLEMS:")
        for p in problems: print("   ", p)
    else:
        print("\n✓ cross-vendor independence: all dual-channel pairs use distinct families")
    print()

def cmd_brief(q, tid):
    t = index_tasks(q).get(tid)
    if not t:
        print(f"no such task {tid}"); return
    BRIEFS.mkdir(exist_ok=True)
    contract = t.get("output_contract")
    body = f"""# PRIME-BLOCK BRIEF — {tid}
_generated {datetime.datetime.utcnow().isoformat()}Z — a fresh session needs zero
conversational memory; the repo state IS the state._

- **project**: {t['project']}
- **owner seat**: {t.get('owner_account')}
- **worker**: {t['worker']}
- **depends_on (all must be green)**: {t.get('depends_on') or '—'}
- **output contract**: {contract or '—'}  (task is DONE only when this passes `contracts.py`)
- **human gate**: {t.get('human_gate', False)}

## before you start
1. `git pull` on this seat's worktree.
2. claim the task:  `python ops/runner/lease.py claim {tid} --account {t.get('owner_account')}`
   (if this errors non-fast-forward, another seat beat you — pick the next brief)
3. `git switch -c task/{tid}`  (or reuse the worktree for this task)

## the task
{t.get('notes','(see the manual/amendment section referenced in queue.yaml)')}

Paste the corresponding verbatim prompt from the manual/amendment for {tid} here,
then work. Plan → execute → **commit early and often** (if the 5h window or weekly
cap cuts the session, the next one resumes from the last commit, losing minutes).

## definition of done
- output written to its contracted path; `python ops/runner/contracts.py {contract or '<none>'} <path>` returns PASS
- lineage JSON emitted: `python ops/runner/lineage.py <output> <inputs...>` (inputs, hashes, code version, timestamp)
- merge task/{tid} → main; `python ops/runner/runner.py --complete {tid}`
- `/clear` before the next task; one task per session.
"""
    out = BRIEFS / f"{tid}.md"
    out.write_text(body)
    print(f"wrote {out}")

def cmd_digest(q, accounts):
    state = load_state()
    ready, gated, blocked, in_flight = ready_set(q, state)
    l2, l1 = assign(ready, accounts, q)
    DIGEST.mkdir(exist_ok=True)
    d = datetime.date.today().isoformat()
    lines = [f"# Daily digest — {d}", ""]
    lines.append(f"progress: **{len(state['completed'])} done**, {len(ready)} ready, "
                 f"{len(gated)} awaiting you, {len(blocked)} blocked upstream\n")
    lines.append("## ⚑ decisions needed (reply in ops/decisions.md — one `gate <TASK> pass|fail` per line; the box applies it on its next cycle)")
    lines += [f"- **{g}** — clear with `gate {g} pass`" for g in gated] or ["- none"]
    esc = escalations(q, state)
    lines.append("\n## ⇧ escalated (two-strike ladder — needs a tier-up re-assignment)")
    lines += [f"- `{t['id']}` — {n} failed attempts on `{t['worker']}`" for t, n in esc] or ["- none"]
    lines.append("\n## in flight (a seat already holds these — do not re-assign)")
    lines += [f"- `{tid}`" for tid in in_flight] or ["- none"]
    lines.append("\n## tomorrow's proposed prime blocks")
    lines += [f"- seat **{s}** → `{t['id']}` ({t['worker']})" for t, s in l2] or ["- none"]
    lines.append("\n## overnight L1 results (last driver run)")
    night_p = ROOT / "ops" / "l1" / "out" / "_last_night.json"
    if night_p.exists():
        night = json.loads(night_p.read_text())
        lines.append(f"- run of {night.get('date')} ({'live' if night.get('live') else 'dry-run'}):")
        for tid, status in sorted(night.get("results", {}).items()):
            note = {"DONE": "output in ops/l1/out/ — validate + complete",
                    "HAS-OUTPUT": "output awaiting validation/--complete",
                    "NO-SPEC": "waiting for input — write ops/l1/<id>.yaml",
                    "NO-SENTINELS": "spec needs verified sentinels",
                    "VOID-SENTINEL": "batch VOIDED (fence tripped) — attempt recorded",
                    "ERROR": "dispatch error — attempt recorded",
                    "SKIP-BUDGET": "budget cap hit",
                    "SKIP-NOKEY": "no API key on box"}.get(status, "")
            lines.append(f"    - `{tid}`: {status}" + (f" — {note}" if note else ""))
    else:
        lines.append("- no driver run recorded yet")
    lines.append("\n## L1 queue (ready for the next overnight run)")
    lines += [f"- {tag} → {t['id']}" for t, tag in l1] or ["- none"]
    lines.append("\n## budget")
    lines += budget.report()
    out = DIGEST / f"{d}.md"
    out.write_text("\n".join(lines))
    print(f"wrote {out}")

def cmd_complete(q, tid):
    t = index_tasks(q).get(tid)
    if t and t.get("output_contract"):
        print(f"reminder: {tid} is DONE only if its output passed "
              f"`contracts.py {t['output_contract']} <path>` — completing on your word.")
    s = load_state()
    if tid not in s["completed"]:
        s["completed"].append(tid)
    s["attempts"].pop(tid, None)
    save_state(s)
    print(f"marked complete: {tid}  (state.json is git-tracked — commit it with your merge)")

def cmd_fail(tid):
    """Record one failed attempt (the two-strike ladder's counter)."""
    s = load_state()
    s["attempts"][tid] = s["attempts"].get(tid, 0) + 1
    save_state(s)
    n = s["attempts"][tid]
    print(f"recorded attempt {n} for {tid}"
          + (" — ESCALATE (shows in plan/digest)" if n >= 2 else ""))

def cmd_clear_fail(tid, quiet=False):
    """Reset a task's failed-attempt counter. For strikes that turned out to be
    infrastructure (vendor billing/outage), not the model failing the task —
    e.g. after fixing depleted Gemini credits — or after a later success."""
    s = load_state()
    had = s["attempts"].pop(tid, None)
    if had is not None:
        save_state(s)
    if not quiet:
        print(f"cleared {had or 0} recorded attempt(s) for {tid}")

def cmd_gate(tid, verdict):
    s = load_state()
    if verdict == "pass" and tid not in s["gates_cleared"]:
        s["gates_cleared"].append(tid)
        s["completed"].append(tid)   # a cleared gate is also 'done' for downstream deps
    elif verdict == "fail" and tid not in s["gates_failed"]:
        s["gates_failed"].append(tid)   # kill-switch record; branch stays parked
    save_state(s)
    print(f"gate {tid} -> {verdict}")

def cmd_apply_decisions():
    """Parse ops/decisions.md (the L3 reply channel) and apply gate verdicts.
    Recognized lines:  gate <TASK> pass|fail   |   complete <TASK>
    Applied lines are prefixed '# applied:' so they are never re-run."""
    dec = ROOT / "ops" / "decisions.md"
    if not dec.exists():
        print("no ops/decisions.md — nothing to apply"); return
    q = load(RUN / "queue.yaml")
    known = set(index_tasks(q))
    out, applied = [], 0
    for line in dec.read_text().splitlines():
        parts = line.strip().split()
        if parts and not line.lstrip().startswith("#"):
            if (len(parts) == 3 and parts[0] == "gate"
                    and parts[2] in ("pass", "fail") and parts[1] in known):
                cmd_gate(parts[1], parts[2]); applied += 1
                out.append(f"# applied: {line}"); continue
            if len(parts) == 2 and parts[0] == "complete" and parts[1] in known:
                cmd_complete(q, parts[1]); applied += 1
                out.append(f"# applied: {line}"); continue
            if parts[0] in ("gate", "complete"):
                print(f"IGNORED (unknown task id): {line.strip()}")
        out.append(line)
    dec.write_text("\n".join(out) + "\n")
    print(f"applied {applied} decision(s) from {dec}")
    _run_inbox_hook()


def _run_inbox_hook():
    """Remote-hands bootstrap: the box's ALREADY-INSTALLED 30-min cron calls
    --apply-decisions, so invoking the inbox runner from here deploys the
    ops/box/inbox.sh channel with no crontab reinstall — whatever lands on
    main reaches the box within one cycle. run_inbox.sh itself is a no-op
    unless the inbox content changed (hash marker)."""
    hook = ROOT / "ops" / "box" / "run_inbox.sh"
    if not hook.exists():
        return
    try:
        subprocess.run(["bash", str(hook)], timeout=1560, check=False)
    except Exception as e:          # a broken inbox must never break decisions
        print(f"inbox hook failed: {e}")

def cmd_reap():
    now = datetime.datetime.utcnow()
    reaped = []
    for f in LEASES.glob("*.lease"):
        d = json.loads(f.read_text())
        if datetime.datetime.fromisoformat(d["expires_at"]) <= now:
            reaped.append(d["task"]); f.unlink()
    print("reaped stale leases:", reaped or "none")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--digest", action="store_true")
    ap.add_argument("--brief")
    ap.add_argument("--complete", nargs="+", metavar="TASK",
                    help="mark one or more tasks complete")
    ap.add_argument("--fail", metavar="TASK",
                    help="record one failed attempt (two-strike escalation counter)")
    ap.add_argument("--clear-fail", nargs="+", metavar="TASK",
                    help="reset failed-attempt counter(s) — for strikes caused by "
                         "vendor billing/outage rather than the task itself")
    ap.add_argument("--gate", nargs=2, metavar=("TASK", "pass|fail"))
    ap.add_argument("--apply-decisions", action="store_true",
                    help="apply gate/complete lines from ops/decisions.md")
    ap.add_argument("--reap", action="store_true")
    a = ap.parse_args()
    q = load(RUN / "queue.yaml")
    accounts = load(ROOT / "ops" / "accounts.yaml")
    if a.plan: cmd_plan(q, accounts)
    elif a.digest: cmd_digest(q, accounts)
    elif a.brief: cmd_brief(q, a.brief)
    elif a.complete:
        for tid in a.complete:
            cmd_complete(q, tid)
    elif a.fail: cmd_fail(a.fail)
    elif a.clear_fail:
        for tid in a.clear_fail:
            cmd_clear_fail(tid)
    elif a.gate: cmd_gate(a.gate[0], a.gate[1])
    elif a.apply_decisions: cmd_apply_decisions()
    elif a.reap: cmd_reap()
    else: ap.print_help()

if __name__ == "__main__":
    main()

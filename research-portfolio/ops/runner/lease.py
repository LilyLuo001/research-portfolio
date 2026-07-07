#!/usr/bin/env python3
"""
lease.py — distributed lock via git. The ONLY coordination primitive between
seats. No message bus, no agent-to-agent chat. A seat claims a task by
committing a lease file and pushing; if the push is rejected non-fast-forward,
someone already claimed it — that seat backs off and takes the next brief.

Because seats run 1–2 blocks/day (not milliseconds apart), git's push
atomicity is more than enough. This is the whole "don't repeat work" mechanism.

  python lease.py claim <task_id> --account A [--ttl 6]
  python lease.py release <task_id>
  python lease.py list
"""
import argparse, json, os, datetime, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEASES = ROOT / "ops" / "leases"

def _git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True)

def claim(task, account, ttl):
    LEASES.mkdir(exist_ok=True)
    f = LEASES / f"{task}.lease"
    if f.exists():
        d = json.loads(f.read_text())
        exp = datetime.datetime.fromisoformat(d["expires_at"])
        if exp > datetime.datetime.utcnow():
            print(f"REFUSED: {task} already leased by seat {d['account']} "
                  f"until {d['expires_at']}Z"); return 1
    now = datetime.datetime.utcnow()
    lease = {
        "task": task, "account": account,
        "started_at": now.isoformat(),
        "expires_at": (now + datetime.timedelta(hours=ttl)).isoformat(),
        "worktree": f"task/{task}",
    }
    f.write_text(json.dumps(lease, indent=2))
    # git dance: the push is the real lock. Rejection => someone beat you.
    _git("add", str(f))
    c = _git("commit", "-m", f"lease: {task} by {account}")
    p = _git("push")
    if p.returncode != 0:
        # non-fast-forward: another seat committed a lease first
        f.unlink(missing_ok=True)
        _git("reset", "--hard", "origin/main")
        print(f"REFUSED: push rejected — another seat claimed {task} first. "
              f"Pull and take the next ready task."); return 1
    print(f"CLAIMED {task} for seat {account} (ttl {ttl}h). Work on branch task/{task}.")
    return 0

def release(task):
    f = LEASES / f"{task}.lease"
    if f.exists():
        f.unlink()
        _git("add", "-A"); _git("commit", "-m", f"release: {task}"); _git("push")
        print(f"released {task}")
    else:
        print(f"no lease for {task}")

def lst():
    now = datetime.datetime.utcnow()
    for f in sorted(LEASES.glob("*.lease")):
        d = json.loads(f.read_text())
        exp = datetime.datetime.fromisoformat(d["expires_at"])
        state = "LIVE" if exp > now else "STALE"
        print(f"{state:5} {d['task']:<22} seat {d['account']}  expires {d['expires_at']}Z")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("claim"); c.add_argument("task"); c.add_argument("--account", required=True); c.add_argument("--ttl", type=int, default=6)
    r = sub.add_parser("release"); r.add_argument("task")
    sub.add_parser("list")
    a = ap.parse_args()
    if a.cmd == "claim": raise SystemExit(claim(a.task, a.account, a.ttl))
    elif a.cmd == "release": release(a.task)
    elif a.cmd == "list": lst()

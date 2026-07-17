#!/usr/bin/env python3
"""Run a single named L1 spec outside the queue (mop-up re-runs).

Usage (on the box, from repo root, with worker keys in env):
    python ops/l1/run_mopup.py P1-T1-events-B-mopup --live
    python ops/l1/run_mopup.py P1-T13-ant-B-mopup  --live

Mirrors l1_driver.run() for one spec file: sentinel-fenced, budget-capped,
writes ops/l1/out/<name>.json (+ .void.json post-mortem on a tripped fence).
Does NOT touch queue state or the two-strike ladder — mop-ups are outside
the scheduler's bookkeeping; merge + validation happen in merge_mopup.py.
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops" / "runner"))
import yaml  # noqa: E402
import dispatch  # noqa: E402

L1 = ROOT / "ops" / "l1"
OUT = L1 / "out"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("name", help="spec name, e.g. P1-T1-events-B-mopup (ops/l1/<name>.yaml)")
    ap.add_argument("--live", action="store_true", help="actually POST (needs keys); default dry-run")
    a = ap.parse_args()

    spec_path = L1 / f"{a.name}.yaml"
    if not spec_path.exists():
        sys.exit(f"no spec at {spec_path}")
    spec = yaml.safe_load(spec_path.read_text()) or {}
    sentinels = spec.get("sentinels")
    if not sentinels:
        sys.exit("spec has no sentinels (unsafe without a fence)")
    outp = OUT / f"{a.name}.json"
    if outp.exists():
        sys.exit(f"output already at {outp} — delete it to re-run")

    OUT.mkdir(parents=True, exist_ok=True)
    status, detail, _ = dispatch.run_batch(
        spec["worker"], spec.get("items", []), sentinels,
        est_cost=float(spec.get("est_cost", 0.0)), live=a.live, out=str(outp),
        web_search=bool(spec.get("web_search")),
        max_items_per_call=spec.get("max_items_per_call"))
    print(f"{a.name}: [{status}] {detail}")
    return 0 if status == "DONE" else 1


if __name__ == "__main__":
    sys.exit(main())

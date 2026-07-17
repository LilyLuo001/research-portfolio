#!/usr/bin/env python3
"""Fold a mop-up output back into its parent channel output.

Usage (on the box, after run_mopup.py reports DONE):
    python ops/l1/merge_mopup.py P1-T1-events-B
    python ops/l1/merge_mopup.py P1-T13-ant-B

Reads ops/l1/out/<task>-mopup.json, merges its answers into
ops/l1/out/<task>.json, then:
  - drops keys not present in the spec ID set (removes the two mangled
    accession keys gemini fabricated, e.g. 0001133125-… for 0001193125-…);
  - verifies every spec ID now has a parseable answer;
  - reports remaining gaps (if the mop-up itself dropped an ID, re-run it).
Then: git add -f ops/l1/out/<task>.json ops/l1/out/<task>-mopup.json && commit.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
L1 = ROOT / "ops" / "l1"
OUT = L1 / "out"
SENT = {"S1", "S2", "S3"}


def spec_ids(task):
    return [m.group(1) for line in (L1 / f"{task}.yaml").open(encoding="utf-8")
            for m in [re.match(r'\s+- id: "([^"]+)"', line)] if m]


def parseable(v):
    if isinstance(v, dict):
        return True
    if isinstance(v, str):
        try:
            json.loads(v)
            return True
        except ValueError:
            return False
    return False


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    task = sys.argv[1]
    main_p = OUT / f"{task}.json"
    mop_p = OUT / f"{task}-mopup.json"
    ids = set(spec_ids(task))
    base = json.loads(main_p.read_text())
    mop = json.loads(mop_p.read_text())

    merged = {k: v for k, v in base.items() if k in ids or k in SENT}
    dropped = sorted(set(base) - set(merged))
    replaced = 0
    for k, v in mop.items():
        if k in SENT:
            continue
        if k not in ids:
            print(f"  ! mop-up answer for non-spec id {k} — ignored")
            continue
        if k in merged and parseable(merged[k]):
            replaced += 1
        merged[k] = v

    gaps = sorted(i for i in ids if i not in merged or not parseable(merged[i]))
    main_p.write_text(json.dumps(merged, indent=1, ensure_ascii=False))
    print(f"{task}: merged {len(mop) - len(SENT & set(mop))} mop-up answers "
          f"({replaced} overwrote unparseable/stale); dropped bogus keys: {dropped or 'none'}")
    if gaps:
        print(f"  STILL MISSING/UNPARSEABLE ({len(gaps)}): {gaps}")
        print("  → re-run these (subset the mop-up yaml) before arb.")
        return 1
    print(f"  coverage complete: {len(ids)}/{len(ids)} parseable. "
          f"git add -f ops/l1/out/{task}.json && commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

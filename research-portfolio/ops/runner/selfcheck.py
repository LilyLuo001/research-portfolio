#!/usr/bin/env python3
"""
selfcheck.py — static integrity gate for the portfolio backbone.

`contracts.py` validates a *data output* against its schema, but there are no
data outputs in the repo yet (they are produced task-by-task). So the check that
actually protects every PR today is a linter over the coordination substrate
itself: queue.yaml, ops/contracts/, ops/accounts.yaml. If the DAG is malformed —
a dangling `depends_on`, an `output_contract` with no schema file, a dual-channel
pair that collapsed onto one vendor — a seat can silently do the wrong work.

CI runs this on every pull request. Exit 0 = clean, exit 1 = one or more
problems (all printed, not just the first).

  python ops/runner/selfcheck.py
"""
import sys, pathlib, yaml

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACTS = ROOT / "ops" / "contracts"

# reuse the runner's own DAG helpers so the linter and the scheduler agree
sys.path.insert(0, str(HERE))
from runner import index_tasks, check_cross_vendor  # noqa: E402

# workers that are executed by a human-driven Claude seat or by deterministic
# code; everything else must be a declared L1 vendor family.
NON_VENDOR_WORKERS = {"code_pro", "project_pro", "script"}
# owner_account values that are legal without naming a concrete seat
FLOAT_OWNERS = {None, "float", "D", "E"}


def load(p):
    with open(p) as f:
        return yaml.safe_load(f)


def main():
    problems = []

    q = load(ROOT / "ops" / "runner" / "queue.yaml")
    accounts = load(ROOT / "ops" / "accounts.yaml")
    seats = set(accounts.get("seats", {}).keys())
    vendor_families = set(q["meta"]["vendor_families"].keys())
    known_workers = vendor_families | NON_VENDOR_WORKERS

    # 1. unique task ids
    ids = [t["id"] for t in q["tasks"]]
    seen = set()
    for tid in ids:
        if tid in seen:
            problems.append(f"duplicate task id: {tid}")
        seen.add(tid)
    tasks = index_tasks(q)

    for t in q["tasks"]:
        tid = t["id"]

        # 2. depends_on targets resolve
        for d in t.get("depends_on") or []:
            if d not in tasks:
                problems.append(f"{tid}: depends_on unknown task '{d}'")

        # 3. channel_of targets resolve (vendor independence is checked separately)
        a = t.get("channel_of")
        if a and a not in tasks:
            problems.append(f"{tid}: channel_of unknown task '{a}'")

        # 4. output_contract, when set, has a schema file
        oc = t.get("output_contract")
        if oc and not (CONTRACTS / f"{oc}.yaml").exists():
            problems.append(f"{tid}: output_contract '{oc}' has no ops/contracts/{oc}.yaml")

        # 5. worker is known
        w = t.get("worker")
        if w not in known_workers:
            problems.append(f"{tid}: unknown worker '{w}' (not a vendor family or {sorted(NON_VENDOR_WORKERS)})")

        # 6. owner_account is a real seat or a legal float value
        owner = t.get("owner_account")
        if owner not in seats and owner not in FLOAT_OWNERS:
            problems.append(f"{tid}: owner_account '{owner}' is not a seat in accounts.yaml")

        # 7. a human-driven L2 task must name an owner seat
        if w in ("code_pro", "project_pro") and owner is None:
            problems.append(f"{tid}: worker '{w}' needs an owner_account seat")

    # 8. every contract file parses and is non-empty
    for cf in sorted(CONTRACTS.glob("*.yaml")):
        try:
            doc = yaml.safe_load(cf.read_text())
            if not doc:
                problems.append(f"contract {cf.name} is empty")
        except yaml.YAMLError as e:
            problems.append(f"contract {cf.name} is not valid YAML: {e}")

    # 9. cross-vendor independence on every dual-channel pair (arch §3)
    problems += check_cross_vendor(q)

    if problems:
        print(f"selfcheck FAILED — {len(problems)} problem(s):")
        for p in problems:
            print("   ✖", p)
        return 1
    print(f"selfcheck PASSED — {len(ids)} tasks, "
          f"{len(list(CONTRACTS.glob('*.yaml')))} contracts, DAG + vendor independence clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

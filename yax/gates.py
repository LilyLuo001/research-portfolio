#!/usr/bin/env python3
"""Mechanically verify YAX's pre-registration gates.

RESEARCH_PLAN_v1.md states gates in §5 (power honesty), §8 (novelty), §9 (the
seal protocol) and §12 (kill conditions). A gate that only an agent's judgement
enforces is not a gate. This script checks the ones that can be checked from
artifacts and git history, and fails closed on everything it cannot see.

  python yax/gates.py --power-aggregate <path> [--freeze-tag v1.0-preregistered]

Every gate returns PASS, FAIL or BLOCKED:

  PASS     the condition was checked and holds
  FAIL     the condition was checked and does NOT hold
  BLOCKED  the condition could not be checked (missing artifact, no git, ...)

BLOCKED is never treated as PASS. The exit status is non-zero if any gate is
FAIL or BLOCKED, so a caller cannot mistake "not checked" for "fine".

Stdlib only: this runs on the SCC under an old interpreter as well as locally.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PRESPEC = "yax/COVERAGE_RULE_PRESPEC_v1.md"
FREEZE = "yax/DESIGN_FREEZE_v1.md"
PLAN = "yax/RESEARCH_PLAN_v2.md"
SUPPORT = "yax/measurement/computerization_support_receipt.json"
DEFAULT_TAG = "v1.0-preregistered"

# §5.2: a design whose power never falls is describing its own smoothness.
GRADIENT_CEILING = 0.95   # power at the smallest tested effect must be below this
POWER_TARGET = 0.80       # the MDE definition
NOMINAL_SIZE = 0.05
SIZE_TOLERANCE = 0.01     # beyond this, bootstrap inference is mandatory


class Result:
    __slots__ = ("gate", "status", "detail")

    def __init__(self, gate, status, detail):
        self.gate, self.status, self.detail = gate, status, detail

    def __repr__(self):
        return f"{self.status:<8} {self.gate:<28} {self.detail}"


def _git(*args):
    try:
        r = subprocess.run(["git", "-C", str(ROOT), *args],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _rel_decline(log_effect):
    """log(1-d) -> d. The plan speaks in relative declines, the grid in logs."""
    return 1.0 - math.exp(log_effect)


# ---------------------------------------------------------------- the gates

def gate_gradient(agg):
    """§5.2. Power must fall through 80% inside the tested grid.

    Two distinct failures, and they mean opposite things:
      * power at the smallest effect is at ceiling -> the ENGINE is suspect
      * power never reaches 80% anywhere -> the DESIGN is underpowered
    """
    if agg is None:
        return Result("gradient", "BLOCKED", "no power aggregate supplied")
    rows = agg.get("results")
    if not rows:
        return Result("gradient", "BLOCKED", "aggregate has no 'results' array")

    pts = []
    for r in rows:
        le, pw = r.get("true_log_effect"), r.get("rejection_probability_zero")
        if le is None or pw is None or le == 0:
            continue
        pts.append((abs(_rel_decline(le)), pw))
    if len(pts) < 2:
        return Result("gradient", "BLOCKED",
                      f"only {len(pts)} non-null effect points; need >= 2")
    pts.sort()

    smallest_d, smallest_p = pts[0]
    largest_d, largest_p = pts[-1]

    if smallest_p >= GRADIENT_CEILING:
        return Result(
            "gradient", "FAIL",
            f"power is {smallest_p:.3f} at the SMALLEST tested effect "
            f"({smallest_d:.2%}), at or above the {GRADIENT_CEILING:.2f} "
            f"ceiling. Per plan §5.2 this is an engine bug to diagnose, not a "
            f"strong design: extend the grid downward and re-run. Do NOT freeze.")

    if largest_p < POWER_TARGET:
        return Result("gradient", "FAIL",
                      f"power never reaches {POWER_TARGET:.0%} — max is "
                      f"{largest_p:.3f} at a {largest_d:.2%} decline. The "
                      f"design is underpowered on this support.")

    # linear interpolation between the bracketing points
    mde = None
    for (d0, p0), (d1, p1) in zip(pts, pts[1:]):
        if p0 < POWER_TARGET <= p1:
            mde = d0 + (POWER_TARGET - p0) * (d1 - d0) / (p1 - p0) if p1 != p0 else d1
            break
    if mde is None:
        return Result("gradient", "BLOCKED",
                      "grid brackets 80% but no adjacent crossing pair found; "
                      "inspect the grid by hand")
    return Result("gradient", "PASS",
                  f"MDE80 ~= {mde:.2%} relative decline "
                  f"(power {smallest_p:.3f} at {smallest_d:.2%} rising to "
                  f"{largest_p:.3f} at {largest_d:.2%})")


def gate_calibration(agg):
    """§5.1. Oversized inference makes bootstrap mandatory, not optional."""
    if agg is None:
        return Result("calibration", "BLOCKED", "no power aggregate supplied")
    null_rows = [r for r in agg.get("results", []) if r.get("true_log_effect") == 0]
    if not null_rows:
        return Result("calibration", "BLOCKED", "no null (effect = 0) row")
    size = null_rows[0].get("rejection_probability_zero")
    cov = null_rows[0].get("coverage_95")
    if size is None:
        return Result("calibration", "BLOCKED", "null row has no rejection rate")
    off = abs(size - NOMINAL_SIZE)
    boot = any(k for k in agg if "bootstrap" in k.lower())
    detail = (f"null size {size:.3f} vs nominal {NOMINAL_SIZE:.2f}"
              + (f", coverage {cov:.3f}" if cov is not None else ""))
    if off <= SIZE_TOLERANCE:
        return Result("calibration", "PASS", detail + " — within tolerance")
    if boot:
        return Result("calibration", "PASS",
                      detail + f" — off by {off:.3f}, and bootstrap fields are "
                      f"present as §5.1 requires")
    return Result("calibration", "FAIL",
                  detail + f" — off by {off:.3f} and the aggregate carries no "
                  f"bootstrap field. §5.1 makes wild-cluster bootstrap the "
                  f"PRIMARY inference before the MDE enters the manuscript.")


def gate_coverage_rule(agg):
    """§9.1 + COVERAGE_RULE_PRESPEC_v1.md. The rule is declared, and a failed
    strict gate must not have silently unlocked the freeze."""
    p = ROOT / PRESPEC
    if not p.is_file():
        return Result("coverage_rule", "FAIL", f"{PRESPEC} does not exist")
    text = p.read_text(encoding="utf-8")
    needed = ["Rule A", "Rule B", "Rule C", "PRIMARY"]
    missing = [n for n in needed if n not in text]
    if missing:
        return Result("coverage_rule", "FAIL",
                      f"{PRESPEC} does not name {missing}")
    if agg is not None and agg.get("design_freeze_permitted") is True:
        frac = agg.get("covered_route_mass_fraction")
        if frac is not None and frac < 0.90:
            return Result("coverage_rule", "FAIL",
                          f"aggregate claims design_freeze_permitted with "
                          f"coverage {frac:.4f} < 0.90. A failed gate must not "
                          f"unlock the freeze.")
    return Result("coverage_rule", "PASS",
                  "three rules declared, primary named in advance")


def gate_prespec_precedes_tag(tag):
    """§9. The whole claim is the ORDERING. Check it in git, not in prose."""
    tag_commit = _git("rev-list", "-n", "1", tag)
    if tag_commit is None:
        return Result("prespec_before_tag", "BLOCKED",
                      f"tag {tag} does not exist yet — freeze has not happened")
    first = _git("log", "--reverse", "--format=%H", "--", PRESPEC)
    if not first:
        return Result("prespec_before_tag", "FAIL",
                      f"{PRESPEC} has no commit history")
    prespec_commit = first.splitlines()[0]
    # `merge-base --is-ancestor` answers through exit status, not stdout, so
    # _git (which returns stdout) cannot express it.
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
                            prespec_commit, tag_commit],
                           capture_output=True, timeout=30)
        ok = (r.returncode == 0)
    except Exception:
        return Result("prespec_before_tag", "BLOCKED", "git merge-base failed")
    if ok:
        return Result("prespec_before_tag", "PASS",
                      f"{PRESPEC} ({prespec_commit[:9]}) is an ancestor of {tag}")
    return Result("prespec_before_tag", "FAIL",
                  f"{PRESPEC} was committed AFTER {tag}. The pre-specification "
                  f"is void by its own terms and the coverage rule must be "
                  f"reported as a post-hoc choice.")


def gate_freeze_doc(tag):
    """§9.5. The freeze document must exist and pin the panel it froze."""
    p = ROOT / FREEZE
    if not p.is_file():
        return Result("freeze_doc", "BLOCKED",
                      f"{FREEZE} not written yet — pre-freeze work outstanding")
    text = p.read_text(encoding="utf-8")
    if not any(len(w) == 64 and all(c in "0123456789abcdef" for c in w.lower())
               for w in text.split()):
        return Result("freeze_doc", "FAIL",
                      f"{FREEZE} carries no 64-hex panel sha256. A freeze that "
                      f"does not pin the data it froze is not a freeze.")
    return Result("freeze_doc", "PASS", f"{FREEZE} present and pins a sha256")


def gate_seal(tag):
    """§9.7 + §12.3. No post-period outcome may be committed before the tag."""
    tracked = _git("ls-files", "yax/analysis/outcomes", "dax/analysis/outcomes")
    committed = [l for l in (tracked or "").splitlines() if l.strip()]
    tag_exists = _git("rev-list", "-n", "1", tag) is not None
    if committed and not tag_exists:
        return Result("seal", "FAIL",
                      f"{len(committed)} outcome file(s) committed with no {tag} "
                      f"tag: {committed[:3]}. This is kill condition §12.3 — the "
                      f"chapter's central claim is lost and the paper must be "
                      f"labelled post-hoc.")
    if not tag_exists:
        return Result("seal", "PASS", "no tag yet, and no outcomes committed")
    return Result("seal", "PASS", f"{tag} exists; {len(committed)} outcome files")


def gate_novelty(tag):
    """§9. Prior-work claims must be resolved with locators, not merely stated.

    An earlier version of this gate passed as soon as the plan stopped saying
    "VERIFY BEFORE THE FREEZE". That is a false pass: rewriting the heading
    resolves nothing. It now looks for the markers an UNFINISHED gate leaves
    behind, so editing the warning away cannot satisfy it.
    """
    p = ROOT / PLAN
    if not p.is_file():
        return Result("novelty", "BLOCKED", f"{PLAN} missing")
    text = p.read_text(encoding="utf-8")
    unresolved = [m for m in ("VERIFY BEFORE THE FREEZE", "locators outstanding",
                              "not yet searched", "not yet verified",
                              "claims to confirm")
                  if m.lower() in text.lower()]
    if unresolved:
        return Result("novelty", "BLOCKED",
                      f"plan still carries unresolved prior-work markers: "
                      f"{unresolved}. Every claim needs a URL, author, date and "
                      f"version, and the decisive question -- has anyone run a "
                      f"pre-registered, power-stated public-data test? -- needs "
                      f"an actual registry search with the sources listed.")
    return Result("novelty", "PASS", "no unresolved prior-work markers in the plan")


def gate_computerization(tag):
    """§8a. The computerization confound must be addressed before the freeze.

    A control added after outcomes are seen is specification search, so this
    gate blocks the freeze rather than flagging a to-do. It passes only when the
    support check has been re-run against a real computerization measure --
    teleworkability is a stand-in and the receipt says so itself.
    """
    p = ROOT / SUPPORT
    if not p.is_file():
        return Result("computerization", "BLOCKED",
                      f"{SUPPORT} missing — run "
                      f"yax/measurement/computerization_support.py")
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return Result("computerization", "BLOCKED", f"unreadable receipt: {exc}")
    if rec.get("proxy_warning"):
        return Result("computerization", "BLOCKED",
                      "support check still runs on the teleworkability PROXY. "
                      "Obtain Webb (2020), Frey-Osborne (2017) and a constructed "
                      "RTI, crosswalk them, and re-run — see "
                      "briefs/Y1b_computerization.md. The proxy already reports "
                      "AIOE's clean cell at 1.61% of employment, so this is not "
                      "a formality.")
    verdicts = {n: m.get("verdict") for n, m in rec.get("measures", {}).items()}
    return Result("computerization", "PASS",
                  f"support check run against real measures: {verdicts}")


# ---------------------------------------------------------------- runner

def run(power_aggregate=None, tag=DEFAULT_TAG):
    agg = None
    if power_aggregate:
        p = pathlib.Path(power_aggregate)
        if p.is_file():
            try:
                agg = json.loads(p.read_text(encoding="utf-8"))
            except Exception as exc:
                print(f"WARNING: could not parse {p}: {exc}", file=sys.stderr)
    return [
        gate_gradient(agg),
        gate_calibration(agg),
        gate_coverage_rule(agg),
        gate_novelty(tag),
        gate_computerization(tag),
        gate_prespec_precedes_tag(tag),
        gate_freeze_doc(tag),
        gate_seal(tag),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--power-aggregate", help="power_available_support_aggregate_*.json")
    ap.add_argument("--freeze-tag", default=DEFAULT_TAG)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    results = run(args.power_aggregate, args.freeze_tag)

    if args.json:
        print(json.dumps([{"gate": r.gate, "status": r.status, "detail": r.detail}
                          for r in results], indent=2))
    else:
        print("YAX pre-registration gates\n" + "=" * 74)
        for r in results:
            print(r)
            print()
        n_fail = sum(1 for r in results if r.status == "FAIL")
        n_block = sum(1 for r in results if r.status == "BLOCKED")
        print("=" * 74)
        if n_fail:
            print(f"{n_fail} FAILED. Do not proceed to the freeze.")
        elif n_block:
            print(f"{n_block} BLOCKED — not checked, which is not the same as "
                  f"passing. Resolve before the freeze.")
        else:
            print("All gates pass. The seal protocol may proceed.")

    return 1 if any(r.status in ("FAIL", "BLOCKED") for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())

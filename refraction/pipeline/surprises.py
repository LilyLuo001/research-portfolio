#!/usr/bin/env python3
"""REFR-R1b — the half of the surprise build that needs no external schema.

R1b has two stages, and only one of them is blocked:

  PARSE      USMPD file -> S_raw. Needs the real file's column names, which
             nobody in this repo has seen. Deliberately NOT implemented here:
             `parse_usmpd()` raises NeedInfo listing exactly what is required.
             Guessing those columns is precisely what iron rule 1 forbids, and
             the manual's R1b prompt says so explicitly ("只允许使用我贴出的列名;
             需要但没有的列输出 NEED_INFO, 禁止猜列名"). The paste-list is
             refraction/R1b_input_requirements.md.

  TRANSFORM  S_raw -> S_std, the scheduled-window policy, and the three
             acceptance assertions. Defined entirely by ops/contracts/
             {macro_calendar,surprises}.yaml plus frozen_config.yaml, so it needs
             no knowledge of USMPD's layout at all. That is this module.

Written before R1a returned, so that when the registry and the file heads arrive,
what is left is an adapter — not a pipeline.

Every tunable is read from frozen_config.yaml (refraction/CLAUDE.md: no magic
numbers in code). Nothing here touches a post-period outcome, so the
prereg guard does not gate it; it is upstream of Gate-0.

CLI:  python refraction/pipeline/surprises.py check <surprises.csv> <calendar.csv>
"""
import argparse
import csv
import math
import pathlib
import sys
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
CONFIG = HERE.parent / "frozen_config.yaml"

SURPRISE_COLUMNS = ["type", "date_ET", "time_ET", "S_raw", "S_std", "source",
                    "is_scheduled"]
CALENDAR_COLUMNS = ["type", "date_ET", "time_ET", "is_scheduled", "source"]


class NeedInfo(Exception):
    """Raised instead of guessing. Carries what must be supplied, verbatim."""


def load_config(path=CONFIG):
    import yaml
    return yaml.safe_load(pathlib.Path(path).read_text())


# --------------------------------------------------------------------------- #
# the blocked stage                                                            #
# --------------------------------------------------------------------------- #
def parse_usmpd(*_args, **_kwargs):
    raise NeedInfo(
        "NEED_INFO: the USMPD parse stage cannot be written from memory. Supply, "
        "from the file itself (see refraction/R1b_input_requirements.md): "
        "(1) the exact file name and format; (2) the full column list; (3) the "
        "first 20 rows; (4) which column carries the FOMC surprise this project "
        "registers as S_raw, quoting the official definition; (5) how the file "
        "marks unscheduled meetings; (6) whether statement and press-conference "
        "windows are separate columns or separate rows. Until then R1b's parse "
        "stage stays unimplemented by design — REFR-R1a-verify is its blocker."
    )


# --------------------------------------------------------------------------- #
# transform                                                                    #
# --------------------------------------------------------------------------- #
def _is_missing(v):
    return v is None or v == "" or (isinstance(v, float) and math.isnan(v))


def _sample_std(values):
    """Population-consistent sample std (n-1), the convention behind
    'S_std = S_raw / 样本内标准差'. Returns None when it is undefined."""
    xs = [float(v) for v in values if not _is_missing(v)]
    if len(xs) < 2:
        return None
    mean = sum(xs) / len(xs)
    var = sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var) if var > 0 else None


def standardize(rows, config):
    """Attach S_std per announcement type. Missing S_raw stays missing.

    A CPI/NFP row with no consensus has no surprise — the contract says S_std
    NULL is legal there and the count belongs in the manifest. Filling it with a
    zero would silently assert 'the release matched expectations', which is a
    fabricated fact, not a neutral default.
    """
    policy = config["surprise"]["standardize"]
    if policy != "sample_std":
        raise NeedInfo(f"NEED_INFO: unknown surprise.standardize policy {policy!r}; "
                       "frozen_config is the only legal source for this choice.")
    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r.get("S_raw"))
    sds = {t: _sample_std(v) for t, v in by_type.items()}

    out, n_null = [], Counter()
    for r in rows:
        r = dict(r)
        sd, raw = sds.get(r["type"]), r.get("S_raw")
        if _is_missing(raw) or sd in (None, 0):
            r["S_std"] = None
            n_null[r["type"]] += 1
        else:
            r["S_std"] = float(raw) / sd
        out.append(r)
    return out, {"sd_by_type": sds, "null_S_std_by_type": dict(n_null)}


def apply_scheduled_policy(rows, config):
    """Drop unscheduled announcements when frozen_config says to. The policy is
    read, never chosen here; the dropped rows are returned so the count is
    reportable rather than invisible."""
    if not config["surprise"].get("exclude_unscheduled", True):
        return list(rows), []
    kept = [r for r in rows if _truthy(r.get("is_scheduled"))]
    dropped = [r for r in rows if not _truthy(r.get("is_scheduled"))]
    return kept, dropped


def _truthy(v):
    return str(v).strip().lower() in ("1", "true", "yes", "t")


# --------------------------------------------------------------------------- #
# the three acceptance assertions (manual §R1b)                                #
# --------------------------------------------------------------------------- #
def a1_no_duplicate_keys(rows):
    seen = Counter((r["type"], r["date_ET"]) for r in rows)
    dups = sorted(k for k, n in seen.items() if n > 1)
    return {"name": "A1_no_duplicate_type_date", "pass": not dups,
            "detail": f"{len(dups)} duplicate (type, date_ET) keys",
            "offending": [list(d) for d in dups[:20]]}


def a2_reconciles_with_calendar(rows, calendar):
    """Per type and per year, the surprise series must match the R1a calendar.

    This is the assertion that catches a parse which silently lost a year, and it
    is why the calendar is an independent input rather than something derived
    from the same file.
    """
    def census(rs):
        c = Counter()
        for r in rs:
            c[(r["type"], str(r["date_ET"])[:4])] += 1
        return c
    got, want = census(rows), census(calendar)
    diffs = [{"type": k[0], "year": k[1], "surprises": got.get(k, 0),
              "calendar": want.get(k, 0)}
             for k in sorted(set(got) | set(want)) if got.get(k, 0) != want.get(k, 0)]
    return {"name": "A2_calendar_reconciliation", "pass": not diffs,
            "detail": f"{len(diffs)} (type, year) cells disagree with the calendar",
            "offending": diffs[:20]}


def a3_s_std_finite_or_null(rows):
    """S_std may be NULL (no consensus) but never inf or NaN — those are arithmetic
    failures wearing a missing value's clothes."""
    bad = [{"type": r["type"], "date_ET": r["date_ET"], "S_std": str(r.get("S_std"))}
           for r in rows
           if r.get("S_std") is not None
           and (not isinstance(r["S_std"], (int, float))
                or math.isnan(r["S_std"]) or math.isinf(r["S_std"]))]
    nulls = sum(1 for r in rows if r.get("S_std") is None)
    return {"name": "A3_S_std_finite_or_null", "pass": not bad,
            "detail": f"{len(bad)} non-finite S_std; {nulls} legal NULLs",
            "offending": bad[:20], "n_null": nulls}


def a4_release_times_match_config(rows, config):
    """Announcement clock times must equal the registered release times.

    Not in the manual's three, but free here and it catches a timezone slip — the
    defect that would silently misalign every announcement-window return in R2.
    """
    want = config["panel"]["release_times_ET"]
    bad = [{"type": r["type"], "date_ET": r["date_ET"], "time_ET": r.get("time_ET"),
            "expected": want.get(r["type"])}
           for r in rows
           if r["type"] in want and str(r.get("time_ET")) != str(want[r["type"]])]
    return {"name": "A4_release_time_matches_config", "pass": not bad,
            "detail": f"{len(bad)} rows whose time_ET is not the registered release time",
            "offending": bad[:20]}


def a5_within_registered_sample_window(rows, config):
    lo = str(config["sample"]["announcements_start"])
    hi = str(config["sample"]["announcements_end"])
    bad = [{"type": r["type"], "date_ET": str(r["date_ET"])}
           for r in rows if not (lo <= str(r["date_ET"]) <= hi)]
    return {"name": "A5_within_sample_window", "pass": not bad,
            "detail": f"{len(bad)} rows outside {lo}..{hi}", "offending": bad[:20]}


HARD = ["A1_no_duplicate_type_date", "A3_S_std_finite_or_null",
        "A4_release_time_matches_config", "A5_within_sample_window"]


def run_all(rows, calendar, config):
    results = {r["name"]: r for r in (
        a1_no_duplicate_keys(rows),
        a2_reconciles_with_calendar(rows, calendar),
        a3_s_std_finite_or_null(rows),
        a4_release_times_match_config(rows, config),
        a5_within_registered_sample_window(rows, config),
    )}
    results["overall_pass"] = all(results[k]["pass"] for k in HARD)
    results["reconciliation_pass"] = results["A2_calendar_reconciliation"]["pass"]
    return results


def build(raw_rows, calendar, config):
    """raw_rows (parsed elsewhere) -> (rows, report, diagnostics). Never writes."""
    kept, dropped = apply_scheduled_policy(raw_rows, config)
    rows, diag = standardize(kept, config)
    diag["dropped_unscheduled"] = len(dropped)
    return rows, run_all(rows, calendar, config), diag


def _read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if "S_raw" in r:
            r["S_raw"] = None if r["S_raw"] in ("", "NA", "NULL") else float(r["S_raw"])
        if r.get("S_std") in ("", "NA", "NULL"):
            r["S_std"] = None
        elif "S_std" in r:
            r["S_std"] = float(r["S_std"])
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description="REFR-R1b transform + assertions")
    ap.add_argument("cmd", choices=["check"])
    ap.add_argument("surprises")
    ap.add_argument("calendar")
    a = ap.parse_args(argv)
    cfg = load_config()
    rep = run_all(_read_csv(a.surprises), _read_csv(a.calendar), cfg)
    for k, v in rep.items():
        if isinstance(v, dict):
            print(f"[{'PASS' if v['pass'] else 'FAIL'}] {k}: {v['detail']}")
    print("OVERALL:", "PASS" if rep["overall_pass"] else "FAIL")
    return 0 if rep["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

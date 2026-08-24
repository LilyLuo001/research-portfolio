#!/usr/bin/env python3
"""Build onet_task_weights.parquet from the pinned O*NET 26.1 text database.

Implements W2_DECISION_task_weight_2026-08-24.md. That decision matters more
than the code, so its terms are restated where they bind:

**[W2-D1] The definition is not re-derived.** The weight is the one already in
`crosswalk/build_legacy_onet_fallback.py` and already embedded in Mapping A's
coverage and the DWA-transport bound:

    frequency_score = sum(category_index * percent) / sum(percent)
    weight          = importance * frequency_score
    share           = weight / sum(weights within the occupation)

A second definition written now would silently diverge from results already
computed through these weights. `--reconcile-against` exists so a seat can
prove this builder reproduces the pinned `onet_timeshares.csv` rather than
asserting it.

**[W2-D2] This is not a time share.** O*NET 26.1 publishes no measured share of
work time by task: the one "% Time" scale (TI) occurs in zero data tables, and
its nine survey items carry CX/CXP and measure body position. The quantity here
is a share of importance-times-frequency **rating mass**. The column is
`task_weight_share`, never `task_time_share`, and no release-path prose may
describe it as time.

**[W2-D3] A known defect, recorded not fixed.** `frequency_score` treats FT's
seven category indices as cardinal. They are ordinal bands -- "Yearly or less"
through "Hourly or more" -- and such bands are typically spaced closer to
logarithmically than linearly, so equal spacing is an assumption and probably a
wrong one. Correcting it would change every weight and break the reconciliation
in W2-D1, and the correct spacing needs published band definitions this repo
does not hold. The receipt carries the defect and its fix path.

**[W2-D4] Two variants, frozen before anyone looks.** Importance-only
(`IM / sum IM`, the field standard) and equal-weight (`1 / n_tasks`) are built
alongside the primary and are never replacements. If a headline moves
materially across the three, the aggregation function is doing work the data
cannot support -- and that is a finding to report, not a number to choose from.

**[W2-D5] The vintage caveat travels.** O*NET 26.1 is cumulative and Task
Ratings rows are dated 2004 through 2021. "2021 vintage" names the release, not
each row's survey year. The receipt records the observed date distribution so
the caveat can be stated from data rather than from memory.

This builder never downloads. It takes a local archive path and refuses unless
the archive's SHA-256 matches the pin recorded by the input inventory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import sys
import zipfile
from collections import Counter, defaultdict

# The archive the 2026-08-24 input inventory read and verified against its pin.
PINNED_ARCHIVE_SHA256 = (
    "543d65fab85e7d8f0361783e89ac68c7cbd34b4018182394214a60354ab8017a")
RELEASE = "O*NET 26.1 (text database)"

TASK_RATINGS = "Task Ratings.txt"
TASK_STATEMENTS = "Task Statements.txt"

# FT publishes one row per category per (occupation, task): seven bands whose
# Data Values are percentages of incumbents and sum to 100. Anything other
# than a complete set of seven is a layout we have not verified and must not
# silently renormalise over.
FT_CATEGORIES = (1, 2, 3, 4, 5, 6, 7)
FT_CATEGORY_LABELS = {
    1: "Yearly or less", 2: "More than yearly", 3: "More than monthly",
    4: "More than weekly", 5: "Daily", 6: "Several times daily",
    7: "Hourly or more",
}
# The inventory measured FT sums across all 17,879 pairs at 99.98--100.02.
# A wider tolerance here would admit a genuinely malformed distribution; a
# tighter one would fail on the published rounding.
FT_SUM_TOLERANCE = 0.5

OUTPUT_FIELDS = [
    "onet_soc", "task_id", "task_weight_share",
    "importance_only_share", "equal_weight_share",
    "importance", "frequency_score", "relevance",
    "n_tasks_in_occupation", "rating_date", "source_vintage",
]


class BuildError(RuntimeError):
    """Raised when the archive does not support building the weights."""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _read_table(archive, suffix):
    """Yield rows of the single member whose name ends with `suffix`.

    Exactly one member must match. O*NET ships 38 members and several share
    name fragments, so a substring match that hits two files would read
    whichever the zip listed first -- the class of fault that put a constant
    column into the DWA coverage bound.
    """
    matches = [n for n in archive.namelist() if n.endswith(suffix)]
    if len(matches) != 1:
        raise BuildError(
            f"expected exactly one archive member ending in {suffix!r}, "
            f"found {len(matches)}: {sorted(matches)}")
    with archive.open(matches[0]) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text, delimiter="\t")
        required = {"O*NET-SOC Code", "Task ID"}
        if not required <= set(reader.fieldnames or []):
            raise BuildError(
                f"{suffix} is missing {sorted(required - set(reader.fieldnames or []))}; "
                f"found {reader.fieldnames}")
        for row in reader:
            yield row


def read_ratings(archive):
    """Collect IM, RT and the seven FT bands per (occupation, task).

    Returns (ratings, stats). A pair recommended for suppression is dropped
    whole rather than partially: suppression is published per rating row, and
    keeping the unsuppressed half of a pair would build a weight out of a
    record O*NET says not to publish.
    """
    ratings = defaultdict(
        lambda: {"frequency": {}, "importance": None, "relevance": None,
                 "suppressed": False, "date": None})
    seen = set()
    stats = Counter()
    dates = Counter()

    for row in _read_table(archive, TASK_RATINGS):
        key = (row["O*NET-SOC Code"].strip(), row["Task ID"].strip())
        scale = row["Scale ID"].strip()
        category = row.get("Category", "").strip()
        dedupe = (key, scale, category)
        if dedupe in seen:
            raise BuildError(
                f"duplicate rating row for {key} scale {scale} "
                f"category {category!r}; the archive grain is not what the "
                f"inventory recorded and every weight would double-count")
        seen.add(dedupe)
        stats[f"rating_rows_{scale}"] += 1

        rec = ratings[key]
        if row.get("Recommend Suppress", "").strip().upper() == "Y":
            rec["suppressed"] = True
        date = row.get("Date", "").strip()
        if date:
            rec["date"] = date
            year = date.split("/")[-1]
            if year:
                dates[year] += 1

        value = row.get("Data Value", "").strip()
        if value == "":
            raise BuildError(f"empty Data Value for {key} scale {scale}")
        if scale == "FT":
            rec["frequency"][int(category)] = float(value)
        elif scale == "IM":
            rec["importance"] = float(value)
        elif scale == "RT":
            rec["relevance"] = float(value)
        else:
            stats["rating_rows_unknown_scale"] += 1

    stats["rated_pairs"] = len(ratings)
    return ratings, stats, dates


def usable(key, rec, stats, ft_sums):
    """Decide whether a rated pair can carry a weight. Never guesses a value."""
    if rec["suppressed"]:
        stats["dropped_recommend_suppress"] += 1
        return False
    if rec["importance"] is None:
        stats["dropped_no_importance"] += 1
        return False
    bands = rec["frequency"]
    if set(bands) != set(FT_CATEGORIES):
        # Renormalising over a partial distribution would invent a frequency
        # profile. The seven bands are the published shape; anything else is
        # a layout change that must be looked at, not averaged over.
        stats["dropped_incomplete_frequency_bands"] += 1
        return False
    total = sum(bands.values())
    ft_sums.append(total)
    if abs(total - 100.0) > FT_SUM_TOLERANCE:
        raise BuildError(
            f"FT bands for {key} sum to {total}, outside 100 +/- "
            f"{FT_SUM_TOLERANCE}. The inventory measured every pair within "
            f"0.05 of 100, so this archive does not match it.")
    return True


def compute(ratings, statements, stats, ft_sums):
    """Compute the primary weight and both frozen variants, per occupation."""
    by_occupation = defaultdict(list)
    for key, rec in ratings.items():
        if not usable(key, rec, stats, ft_sums):
            continue
        occupation, task_id = key
        bands = rec["frequency"]
        band_mass = sum(bands.values())
        # [W2-D3] the cardinal-index treatment, isolated on one line so the
        # defect has one place to be fixed if the band spacing is ever obtained.
        frequency_score = sum(k * v for k, v in bands.items()) / band_mass
        by_occupation[occupation].append({
            "task_id": task_id,
            "importance": rec["importance"],
            "relevance": rec["relevance"],
            "frequency_score": frequency_score,
            "weight": rec["importance"] * frequency_score,
            "rating_date": rec["date"],
        })

    rows = []
    for occupation, items in sorted(by_occupation.items()):
        weight_total = sum(i["weight"] for i in items)
        importance_total = sum(i["importance"] for i in items)
        if weight_total <= 0 or importance_total <= 0:
            stats["dropped_occupation_zero_denominator"] += 1
            continue
        n = len(items)
        for item in sorted(items, key=lambda i: i["task_id"]):
            rows.append({
                "onet_soc": occupation,
                "task_id": item["task_id"],
                "task_weight_share": item["weight"] / weight_total,
                "importance_only_share": item["importance"] / importance_total,
                "equal_weight_share": 1.0 / n,
                "importance": item["importance"],
                "frequency_score": item["frequency_score"],
                "relevance": item["relevance"],
                "n_tasks_in_occupation": n,
                "rating_date": item["rating_date"],
                "source_vintage": RELEASE,
            })
    stats["occupations_with_weights"] = len(
        {r["onet_soc"] for r in rows})
    stats["tasks_with_weights"] = len(rows)
    stats["statements_without_ratings"] = len(
        {(s["O*NET-SOC Code"].strip(), s["Task ID"].strip())
         for s in statements}
        - set(ratings))
    return rows


def check_shares_sum_to_one(rows, tolerance=1e-9):
    """Every share column must sum to 1 within each occupation.

    This is the arithmetic identity the whole wage-bill weighting rests on. If
    it fails, an occupation's tasks either over- or under-claim its wage mass
    and every exposure number built on it is wrong by that factor.
    """
    for column in ("task_weight_share", "importance_only_share",
                   "equal_weight_share"):
        totals = defaultdict(float)
        for row in rows:
            totals[row["onet_soc"]] += row[column]
        worst = max(((abs(t - 1.0), occ) for occ, t in totals.items()),
                    default=(0.0, None))
        if worst[0] > tolerance:
            raise BuildError(
                f"{column} sums to {1.0 + worst[0]:.12f} for occupation "
                f"{worst[1]}, outside 1 +/- {tolerance}")
    return True


def reconcile(rows, path, tolerance=1e-6):
    """Prove this builder reproduces the pinned predecessor, per W2-D1.

    The predecessor CSV carries the same definition under the old name. Shares
    that differ mean the definition moved, which is the one outcome W2-D1
    exists to prevent -- and it must be a refusal, not a warning, because the
    divergence would be invisible in every downstream number.
    """
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        share_column = next(
            (c for c in ("task_time_share", "task_weight_share",
                         "legacy_task_time_share")
             if c in (reader.fieldnames or [])), None)
        if share_column is None:
            raise BuildError(
                f"{path} carries no recognised share column; found "
                f"{reader.fieldnames}")
        expected = {(r["onet_soc"].strip() if "onet_soc" in r
                     else r["O*NET-SOC Code"].strip(),
                     r["task_id"].strip()): float(r[share_column])
                    for r in reader}

    built = {(r["onet_soc"], r["task_id"]): r["task_weight_share"] for r in rows}
    only_built = sorted(set(built) - set(expected))
    only_expected = sorted(set(expected) - set(built))
    diffs = [(k, built[k], expected[k]) for k in set(built) & set(expected)
             if abs(built[k] - expected[k]) > tolerance]
    result = {
        "reconciled_against": str(path),
        "share_column_read": share_column,
        "rows_in_reference": len(expected),
        "rows_built": len(built),
        "keys_only_in_built": len(only_built),
        "keys_only_in_reference": len(only_expected),
        "shares_differing_beyond_tolerance": len(diffs),
        "tolerance": tolerance,
    }
    if only_built or only_expected or diffs:
        worst = max((abs(b - e) for _, b, e in diffs), default=0.0)
        raise BuildError(
            f"reconciliation FAILED against {path}: "
            f"{len(only_built)} keys only here, {len(only_expected)} only "
            f"there, {len(diffs)} shares differing (worst {worst:.3e}). "
            f"W2-D1 requires this builder to reproduce the pinned definition; "
            f"a divergence here would be invisible in every downstream number.")
    result["status"] = "RECONCILED"
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=pathlib.Path, required=True,
                    help="local path to db_26_1_text.zip; never downloaded")
    ap.add_argument("--expect-sha", default=PINNED_ARCHIVE_SHA256,
                    help="required archive SHA-256; refuses on mismatch")
    ap.add_argument("--output", type=pathlib.Path,
                    default=pathlib.Path("dax/data_built/onet_task_weights.parquet"))
    ap.add_argument("--receipt", type=pathlib.Path, default=None)
    ap.add_argument("--reconcile-against", type=pathlib.Path, default=None,
                    help="pinned onet_timeshares.csv; W2-D1 reconciliation")
    args = ap.parse_args(argv)

    try:
        import pandas as pd  # noqa: F401
    except ImportError:
        print("pandas is required to write the parquet", file=sys.stderr)
        return 2

    if not args.archive.is_file():
        print(f"archive not found: {args.archive}", file=sys.stderr)
        return 2

    actual = sha256(args.archive)
    if actual != args.expect_sha:
        print(f"REFUSING: archive SHA-256 {actual} does not match the pin "
              f"{args.expect_sha}. This builder never downloads; supply the "
              f"archive the input inventory verified.", file=sys.stderr)
        return 2

    stats = Counter()
    ft_sums = []
    try:
        with zipfile.ZipFile(args.archive) as archive:
            bad = archive.testzip()
            if bad is not None:
                raise BuildError(f"corrupt archive member: {bad}")
            ratings, rstats, dates = read_ratings(archive)
            statements = list(_read_table(archive, TASK_STATEMENTS))
        stats.update(rstats)
        rows = compute(ratings, statements, stats, ft_sums)
        if not rows:
            raise BuildError("no task carried a usable weight")
        check_shares_sum_to_one(rows)
        reconciliation = (reconcile(rows, args.reconcile_against)
                          if args.reconcile_against else None)
    except BuildError as exc:
        print(f"NEED_HUMAN: {exc}", file=sys.stderr)
        return 2

    import pandas as pd
    frame = pd.DataFrame(rows)[OUTPUT_FIELDS]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.output, index=False)

    receipt = {
        "receipt_version": "dax-w2-onet-task-weights-v1",
        "decision": "dax/memo/W2_DECISION_task_weight_2026-08-24.md",
        "not_a_time_share": (
            "[W2-D2] This is a share of importance-times-frequency RATING "
            "MASS. O*NET 26.1 publishes no measured share of work time by "
            "task. No release-path prose, table or column may describe "
            "task_weight_share as time."),
        "definition": {
            "primary": "share = (importance * frequency_score) normalised within occupation",
            "frequency_score": "sum(category_index * percent) / sum(percent) over FT bands 1..7",
            "variants_frozen_before_inspection": {
                "importance_only_share": "IM / sum(IM) within occupation",
                "equal_weight_share": "1 / n_tasks within occupation",
            },
            "source_of_definition": (
                "[W2-D1] adopted unchanged from "
                "dax/w2/crosswalk/build_legacy_onet_fallback.py; not re-derived"),
        },
        "known_defect": {
            "id": "W2-D3",
            "what": ("frequency_score treats FT's seven category indices as "
                     "cardinal values. They are ordinal frequency bands."),
            "bands": FT_CATEGORY_LABELS,
            "why_not_fixed_here": (
                "correcting the spacing changes every weight and breaks the "
                "W2-D1 reconciliation with Mapping A's coverage and the DWA "
                "bound, which were computed through these weights"),
            "fix_path": (
                "obtain the published FT band definitions; if spacing is not "
                "near-linear, re-derive the weight and re-run Mapping A "
                "coverage and the DWA bound in the same change so all three "
                "move together"),
        },
        "vintage_caveat": {
            "id": "W2-D5",
            "release": RELEASE,
            "what": ("O*NET 26.1 is cumulative. Task Ratings rows carry dates "
                     "spanning many years; '2021 vintage' names the release, "
                     "not each row's survey year. Any claim that the index "
                     "rests on 2021 task structure must say this."),
            "rating_row_year_counts": dict(sorted(dates.items())),
        },
        "source_archive": {
            "path": str(args.archive),
            "sha256": actual,
            "verified_against_pin": True,
            "release": RELEASE,
            "members_read": [TASK_RATINGS, TASK_STATEMENTS],
        },
        "counts": dict(sorted(stats.items())),
        "ft_band_sums": {
            "min": min(ft_sums) if ft_sums else None,
            "max": max(ft_sums) if ft_sums else None,
            "tolerance": FT_SUM_TOLERANCE,
        },
        "shares_sum_to_one_within_occupation": True,
        "reconciliation": reconciliation,
        "output": {
            "path": str(args.output),
            "rows": len(rows),
            "columns": OUTPUT_FIELDS,
            "share_column": "task_weight_share",
        },
    }
    receipt_path = args.receipt or args.output.with_suffix(".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {args.output} ({len(rows)} rows)")
    print(f"wrote {receipt_path}")
    print(f"occupations: {stats['occupations_with_weights']}  "
          f"rated pairs: {stats['rated_pairs']}  "
          f"suppressed: {stats['dropped_recommend_suppress']}")
    if reconciliation:
        print(f"reconciliation: {reconciliation['status']} against "
              f"{reconciliation['rows_in_reference']} reference rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

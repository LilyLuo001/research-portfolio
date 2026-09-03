"""Build provisional O*NET 25.0 task-share fallbacks on the 2019 taxonomy.

O*NET 26.1 contains task statements for some newly classified occupations but
no usable importance/frequency ratings. This builder uses the official O*NET
25.0 archive and official 2010-to-2019 taxonomy crosswalk. It never overwrites
current usable profiles. Every carried profile is labelled provisional; when
several legacy occupations feed one 2019 code, equal source weights are only a
diagnostic center and downstream code must carry source-profile bounds.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import pathlib
import zipfile
from collections import defaultdict


FIELDS = [
    "onet_soc2019", "onet_soc2010", "task_id", "task_statement",
    "legacy_task_time_share", "legacy_source_weight",
    "fallback_task_time_share", "fallback_status", "bounds_required",
    "source_vintage",
]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _rows(archive: zipfile.ZipFile, suffix: str):
    member = next(name for name in archive.namelist() if name.endswith(suffix))
    with archive.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        yield from csv.DictReader(text, delimiter="\t")


def legacy_profiles(archive_path: pathlib.Path) -> dict[str, list[dict[str, object]]]:
    with zipfile.ZipFile(archive_path) as archive:
        archive.testzip()
        tasks = {(row["O*NET-SOC Code"], row["Task ID"]): row
                 for row in _rows(archive, "Task Statements.txt")}
        ratings: dict[tuple[str, str], dict[str, object]] = defaultdict(
            lambda: {"frequency": {}, "importance": None, "suppressed": False}
        )
        for row in _rows(archive, "Task Ratings.txt"):
            key = (row["O*NET-SOC Code"], row["Task ID"])
            if row["Recommend Suppress"] == "Y":
                ratings[key]["suppressed"] = True
            if row["Scale ID"] == "FT":
                ratings[key]["frequency"][int(row["Category"])] = float(row["Data Value"])
            elif row["Scale ID"] == "IM":
                ratings[key]["importance"] = float(row["Data Value"])

    raw_weights: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for (occupation, task_id), task in tasks.items():
        rating = ratings.get((occupation, task_id))
        if not rating or rating["suppressed"] or rating["importance"] is None:
            continue
        frequency = rating["frequency"]
        frequency_sum = sum(frequency.values())
        if not frequency_sum:
            continue
        frequency_score = sum(k * v for k, v in frequency.items()) / frequency_sum
        raw_weights[occupation].append(
            (task_id, task["Task"], float(rating["importance"]) * frequency_score)
        )

    profiles: dict[str, list[dict[str, object]]] = {}
    for occupation, items in raw_weights.items():
        denominator = sum(weight for _, _, weight in items)
        if denominator <= 0:
            continue
        profiles[occupation] = [
            {"task_id": task_id, "task_statement": statement,
             "legacy_task_time_share": weight / denominator}
            for task_id, statement, weight in items
        ]
    return profiles


def taxonomy_sources(
    crosswalk_path: pathlib.Path, profiles: dict[str, list[dict[str, object]]]
) -> dict[str, list[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    with crosswalk_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            old = row["O*NET-SOC 2010 Code"].strip()
            new = row["O*NET-SOC 2019 Code"].strip()
            if old in profiles:
                result[new].add(old)
    return {new: sorted(old) for new, old in result.items()}


def current_usable_codes(path: pathlib.Path) -> set[str]:
    result = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["primary_usable"].strip().lower() == "true":
                result.add(row["onet_soc"].strip())
    return result


def build(archive_path: pathlib.Path, crosswalk_path: pathlib.Path,
          current_path: pathlib.Path, output_path: pathlib.Path,
          receipt_path: pathlib.Path) -> dict[str, object]:
    profiles = legacy_profiles(archive_path)
    sources = taxonomy_sources(crosswalk_path, profiles)
    current = current_usable_codes(current_path)
    fallback = {new: old for new, old in sources.items() if new not in current}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sums: dict[str, float] = defaultdict(float)
    row_count = 0
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for new_code, old_codes in sorted(fallback.items()):
            source_weight = 1.0 / len(old_codes)
            status = ("legacy_single_source" if len(old_codes) == 1
                      else "legacy_equal_source_mix")
            for old_code in old_codes:
                for task in profiles[old_code]:
                    share = source_weight * float(task["legacy_task_time_share"])
                    writer.writerow({
                        "onet_soc2019": new_code,
                        "onet_soc2010": old_code,
                        "task_id": task["task_id"],
                        "task_statement": task["task_statement"],
                        "legacy_task_time_share": f"{task['legacy_task_time_share']:.12f}",
                        "legacy_source_weight": f"{source_weight:.12f}",
                        "fallback_task_time_share": f"{share:.12f}",
                        "fallback_status": status,
                        "bounds_required": "true",
                        "source_vintage": "O*NET 25.0 (2020-08)",
                    })
                    sums[new_code] += share
                    row_count += 1
    output_path.chmod(0o600)
    bad_sums = {code: value for code, value in sums.items() if abs(value - 1) > 1e-9}
    if bad_sums:
        raise ValueError(f"legacy fallback shares do not sum to one: {bad_sums}")
    receipt = {
        "status": "ONET_25_0_TO_2019_PROVISIONAL_FALLBACK_PRIVATE",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sources": {
            "onet_25_0_archive": {
                "agency": "U.S. Department of Labor, O*NET Resource Center",
                "vintage": "O*NET 25.0 (August 2020)",
                "url": "https://www.onetcenter.org/dl_files/database/db_25_0_text.zip",
                "sha256": sha256(archive_path),
            },
            "onet_2010_to_2019_crosswalk": {
                "agency": "U.S. Department of Labor, O*NET Resource Center",
                "vintage": "O*NET-SOC 2010 to O*NET-SOC 2019",
                "url": ("https://www.onetcenter.org/taxonomy/2019/walk/"
                        "2010_to_2019_Crosswalk.csv?fmt=csv"),
                "sha256": sha256(crosswalk_path),
            },
        },
        "inputs": {
            archive_path.name: sha256(archive_path),
            crosswalk_path.name: sha256(crosswalk_path),
            current_path.name: sha256(current_path),
        },
        "output_name": output_path.name,
        "output_sha256": sha256(output_path),
        "n_rows": row_count,
        "n_fallback_onet_soc2019_codes": len(fallback),
        "n_equal_source_mix_codes": sum(len(old) > 1 for old in fallback.values()),
        "bad_share_sums": len(bad_sums),
        "use_rule": "provisional bounds only; never overwrite a current usable O*NET 26.1 profile",
        "raw_files_committed": False,
        "detailed_fallback_committed": False,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=pathlib.Path, required=True)
    parser.add_argument("--taxonomy-crosswalk", type=pathlib.Path, required=True)
    parser.add_argument("--current-timeshares", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.archive, args.taxonomy_crosswalk,
                           args.current_timeshares, args.output, args.receipt), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

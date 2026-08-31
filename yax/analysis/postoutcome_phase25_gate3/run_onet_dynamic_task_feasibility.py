#!/usr/bin/env python3
"""Audit official archived O*NET task vintages without labor outcomes.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.
This program reads O*NET database archives only. It does not read CPS data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import zipfile
from collections import Counter

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
RELEASES = [
    ("22.0", "2017-08"), ("22.1", "2017-10"), ("22.2", "2018-02"),
    ("22.3", "2018-05"), ("23.0", "2018-08"), ("23.1", "2018-11"),
    ("23.2", "2019-02"), ("23.3", "2019-05"), ("24.0", "2019-08"),
    ("24.1", "2019-11"), ("24.2", "2020-02"), ("24.3", "2020-05"),
    ("25.0", "2020-08"), ("25.1", "2020-11"), ("25.2", "2021-02"),
    ("25.3", "2021-05"), ("26.0", "2021-08"), ("26.1", "2021-11"),
    ("26.2", "2022-02"), ("26.3", "2022-05"), ("27.0", "2022-08"),
    ("27.1", "2022-11"), ("27.2", "2023-02"), ("27.3", "2023-05"),
    ("28.0", "2023-08"), ("28.1", "2023-11"), ("28.2", "2024-02"),
    ("28.3", "2024-05"), ("29.0", "2024-08"), ("29.1", "2024-11"),
    ("29.2", "2025-02"), ("29.3", "2025-05"), ("30.0", "2025-08"),
    ("30.1", "2025-12"), ("30.2", "2026-02"), ("30.3", "2026-05"),
    ("31.0", "2026-08"),
]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_hash(rows: list[tuple]) -> str:
    payload = json.dumps(sorted(rows), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def modal(values: pd.Series) -> str:
    clean = [str(value) for value in values.dropna() if str(value).strip()]
    if not clean:
        return ""
    counts = Counter(clean)
    return sorted(counts, key=lambda value: (-counts[value], value))[0]


def find_member(archive: zipfile.ZipFile, suffix: str) -> str:
    names = [name for name in archive.namelist() if pathlib.PurePosixPath(name).name == suffix]
    if len(names) != 1:
        raise RuntimeError(f"expected one {suffix!r}, found {names}")
    return names[0]


def read_release(path: pathlib.Path, version: str, release_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    with zipfile.ZipFile(path) as archive:
        with archive.open(find_member(archive, "Task Statements.txt")) as handle:
            tasks = pd.read_csv(handle, sep="\t", dtype=str, keep_default_na=False)
        with archive.open(find_member(archive, "Task Ratings.txt")) as handle:
            ratings = pd.read_csv(handle, sep="\t", dtype=str, keep_default_na=False)
    tasks.columns = [column.strip() for column in tasks.columns]
    ratings.columns = [column.strip() for column in ratings.columns]
    required_tasks = {"O*NET-SOC Code", "Task ID", "Task", "Task Type", "Date", "Domain Source"}
    required_ratings = {"O*NET-SOC Code", "Task ID", "Scale ID", "Data Value", "Date", "Domain Source"}
    if not required_tasks.issubset(tasks.columns) or not required_ratings.issubset(ratings.columns):
        raise RuntimeError(f"unexpected O*NET schema in {path.name}")
    tasks = tasks[list(required_tasks)].rename(columns={
        "O*NET-SOC Code": "occ", "Task ID": "task_id", "Task": "task_text",
        "Task Type": "task_type", "Date": "task_date", "Domain Source": "task_source",
    })
    ratings = ratings[list(required_ratings)].rename(columns={
        "O*NET-SOC Code": "occ", "Task ID": "task_id", "Scale ID": "scale_id",
        "Data Value": "data_value", "Date": "rating_date", "Domain Source": "rating_source",
    })
    ratings = ratings.loc[ratings.scale_id.isin(["IM", "RT"])].copy()
    ratings["data_value"] = pd.to_numeric(ratings.data_value, errors="coerce")
    tasks["release_version"], tasks["release_date"] = version, release_date
    ratings["release_version"], ratings["release_date"] = version, release_date
    return tasks, ratings


def snapshot_table(tasks: pd.DataFrame, ratings: pd.DataFrame) -> pd.DataFrame:
    task_rows = []
    for occ, group in tasks.groupby("occ", sort=True):
        content = [
            (str(row.task_id), str(row.task_text), str(row.task_type))
            for row in group.itertuples(index=False)
        ]
        task_rows.append({
            "occ": occ,
            "task_content_fingerprint": stable_hash(content),
            "task_count": len(group),
            "task_date": modal(group.task_date),
            "task_dates": "|".join(sorted(set(group.task_date) - {""})),
            "task_sources": "|".join(sorted(set(group.task_source) - {""})),
        })
    rating_rows = []
    for occ, group in ratings.groupby("occ", sort=True):
        content = [
            (str(row.task_id), str(row.scale_id), None if pd.isna(row.data_value) else float(row.data_value))
            for row in group.itertuples(index=False)
        ]
        rating_rows.append({
            "occ": occ,
            "rating_fingerprint": stable_hash(content),
            "rating_rows": len(group),
            "rating_date": modal(group.rating_date),
            "rating_dates": "|".join(sorted(set(group.rating_date) - {""})),
            "rating_sources": "|".join(sorted(set(group.rating_source) - {""})),
        })
    return pd.DataFrame(task_rows).merge(pd.DataFrame(rating_rows), on="occ", how="outer")


def transition_metrics(left_tasks: pd.DataFrame, right_tasks: pd.DataFrame,
                       left_ratings: pd.DataFrame, right_ratings: pd.DataFrame,
                       left_version: str, right_version: str,
                       left_date: str, right_date: str) -> dict:
    lt = left_tasks.set_index(["occ", "task_id"])
    rt = right_tasks.set_index(["occ", "task_id"])
    lk, rk = set(lt.index), set(rt.index)
    common = lk & rk
    common_index = pd.MultiIndex.from_tuples(sorted(common), names=["occ", "task_id"])
    exact = int((
        lt.reindex(common_index).task_text.to_numpy()
        == rt.reindex(common_index).task_text.to_numpy()
    ).sum())
    revised = len(common) - exact

    left_text = {(row.occ, normalize_text(row.task_text)): str(row.task_id)
                 for row in left_tasks.itertuples(index=False)}
    right_text = {(row.occ, normalize_text(row.task_text)): str(row.task_id)
                  for row in right_tasks.itertuples(index=False)}
    same_text_keys = set(left_text) & set(right_text)
    renumbered = sum(left_text[key] != right_text[key] for key in same_text_keys)

    removed_codes = set(left_tasks.occ) - set(right_tasks.occ)
    added_codes = set(right_tasks.occ) - set(left_tasks.occ)
    old_lineage = set(zip(left_tasks.loc[left_tasks.occ.isin(removed_codes), "task_id"],
                          left_tasks.loc[left_tasks.occ.isin(removed_codes), "task_text"]))
    new_lineage = set(zip(right_tasks.loc[right_tasks.occ.isin(added_codes), "task_id"],
                          right_tasks.loc[right_tasks.occ.isin(added_codes), "task_text"]))

    lr = left_ratings.set_index(["occ", "task_id", "scale_id"]).data_value
    rr = right_ratings.set_index(["occ", "task_id", "scale_id"]).data_value
    rating_common = lr.index.intersection(rr.index)
    rating_delta = (rr.loc[rating_common].to_numpy(float) - lr.loc[rating_common].to_numpy(float))
    rating_delta = rating_delta[np.isfinite(rating_delta)]
    return {
        "analysis_status": LABEL, "row_type": "adjacent_release_summary",
        "left_release": left_version, "right_release": right_version,
        "left_release_date": left_date, "right_release_date": right_date,
        "left_occupations": left_tasks.occ.nunique(), "right_occupations": right_tasks.occ.nunique(),
        "common_exact_occupation_codes": len(set(left_tasks.occ) & set(right_tasks.occ)),
        "occupation_codes_deleted": len(removed_codes), "occupation_codes_added": len(added_codes),
        "left_occ_task_ids": len(lk), "right_occ_task_ids": len(rk),
        "stable_occ_task_ids": len(common), "exact_stable_occ_task_texts": exact,
        "task_id_wording_revisions": revised, "apparent_task_id_renumbering_same_occ_text": renumbered,
        "task_additions": len(rk - lk), "task_deletions": len(lk - rk),
        "lineage_task_matches_across_deleted_added_occ_codes": len(old_lineage & new_lineage),
        "comparable_im_rt_ratings": int(len(rating_delta)),
        "mean_absolute_im_rt_change": float(np.mean(np.abs(rating_delta))) if len(rating_delta) else "",
    }


def build_outputs(archive_dir: pathlib.Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    releases: list[dict] = []
    source_hashes = {}
    for version, release_date in RELEASES:
        path = archive_dir / f"db_{version.replace('.', '_')}_text.zip"
        if not path.exists():
            raise FileNotFoundError(path)
        tasks, ratings = read_release(path, version, release_date)
        releases.append({"version": version, "date": release_date, "tasks": tasks,
                         "ratings": ratings, "snapshots": snapshot_table(tasks, ratings)})
        source_hashes[path.name] = sha256(path)

    transition_rows = []
    for left, right in zip(releases[:-1], releases[1:]):
        transition_rows.append(transition_metrics(
            left["tasks"], right["tasks"], left["ratings"], right["ratings"],
            left["version"], right["version"], left["date"], right["date"],
        ))

    history = []
    for release in releases:
        snapshot = release["snapshots"].copy()
        snapshot["release_version"] = release["version"]
        snapshot["release_date"] = release["date"]
        history.append(snapshot)
    history = pd.concat(history, ignore_index=True)
    history["release_order"] = history.release_version.map(
        {version: index for index, (version, _) in enumerate(RELEASES)}
    )
    history = history.sort_values(["occ", "release_order"])
    history["combined_fingerprint"] = history.task_content_fingerprint.fillna("") + ":" + history.rating_fingerprint.fillna("")
    history["previous_fingerprint"] = history.groupby("occ").combined_fingerprint.shift()
    history["genuine_snapshot"] = history.previous_fingerprint.isna() | history.combined_fingerprint.ne(history.previous_fingerprint)
    history["content_changed"] = (
        history.task_content_fingerprint.ne(history.groupby("occ").task_content_fingerprint.shift())
        & history.groupby("occ").task_content_fingerprint.shift().notna()
    )
    history["ratings_changed"] = (
        history.rating_fingerprint.ne(history.groupby("occ").rating_fingerprint.shift())
        & history.groupby("occ").rating_fingerprint.shift().notna()
    )
    timing = history.loc[history.genuine_snapshot].copy()
    timing["metadata_update_date"] = timing.rating_date.where(timing.rating_date.ne(""), timing.task_date)
    timing["metadata_update_month"] = pd.to_datetime(timing.metadata_update_date, format="%m/%Y", errors="coerce")
    timing["months_since_previous_genuine_snapshot"] = (
        timing.groupby("occ").metadata_update_month.diff().dt.days / 30.4375
    )
    timing_rows = timing[[
        "occ", "release_version", "release_date", "task_count", "rating_rows",
        "task_date", "rating_date", "metadata_update_date", "task_dates", "rating_dates",
        "task_sources", "rating_sources", "content_changed", "ratings_changed",
        "months_since_previous_genuine_snapshot", "task_content_fingerprint", "rating_fingerprint",
    ]].copy()
    timing_rows.insert(0, "analysis_status", LABEL)

    coverage_rows = []
    for occ, group in history.groupby("occ", sort=True):
        genuine = group.loc[group.genuine_snapshot]
        dates = pd.to_datetime(
            genuine.rating_date.where(genuine.rating_date.ne(""), genuine.task_date),
            format="%m/%Y", errors="coerce",
        )
        pre = dates.dt.year.lt(2022)
        post = dates.dt.year.ge(2022)
        coverage_rows.append({
            "analysis_status": LABEL, "occ": occ,
            "first_archive_release": group.release_version.iloc[0],
            "last_archive_release": group.release_version.iloc[-1],
            "archive_releases_observed": len(group),
            "genuine_task_domain_snapshots": len(genuine),
            "content_changes_after_first": int(genuine.content_changed.sum()),
            "rating_changes_after_first": int(genuine.ratings_changed.sum()),
            "distinct_metadata_update_dates": int(dates.dropna().nunique()),
            "pre_2022_genuine_snapshots": int(pre.sum()),
            "post_2022_genuine_snapshots": int(post.sum()),
            "has_pre_and_post_2022": bool(pre.any() and post.any()),
            "has_multiple_pre_and_post_2022": bool(pre.sum() >= 2 and post.any()),
            "task_sources_observed": "|".join(sorted({x for cell in group.task_sources for x in str(cell).split("|") if x})),
            "rating_sources_observed": "|".join(sorted({x for cell in group.rating_sources for x in str(cell).split("|") if x})),
        })

    # Deterministic illustrative subset: most repeatedly observed exact codes,
    # ties resolved by code. This selection uses no labor outcome.
    coverage = pd.DataFrame(coverage_rows).sort_values(
        ["genuine_task_domain_snapshots", "occ"], ascending=[False, True]
    )
    pilot_codes = set(coverage.head(12).occ)
    pilot_rows = []
    for occ in sorted(pilot_codes):
        frames = []
        for release in releases:
            frame = release["tasks"].loc[release["tasks"].occ.eq(occ)].copy()
            if not frame.empty:
                frames.append((release, frame))
        for (left_rel, left), (right_rel, right) in zip(frames[:-1], frames[1:]):
            if stable_hash([(r.task_id, r.task_text, r.task_type) for r in left.itertuples()]) == stable_hash(
                [(r.task_id, r.task_text, r.task_type) for r in right.itertuples()]
            ):
                continue
            metric = transition_metrics(
                left, right,
                left_rel["ratings"].loc[left_rel["ratings"].occ.eq(occ)],
                right_rel["ratings"].loc[right_rel["ratings"].occ.eq(occ)],
                left_rel["version"], right_rel["version"], left_rel["date"], right_rel["date"],
            )
            metric["row_type"] = "illustrative_pilot_occupation_transition"
            metric["pilot_occ"] = occ
            pilot_rows.append(metric)
    stability = pd.DataFrame(transition_rows + pilot_rows)
    metadata = {
        "analysis_status": LABEL,
        "archive_versions": [version for version, _ in RELEASES],
        "archive_release_dates": dict(RELEASES),
        "archive_sha256": source_hashes,
        "archives": len(releases),
        "selection_rule_for_illustrative_subset": "12 exact O*NET-SOC codes with most genuine snapshots; ties by code",
        "labor_outcome_files_read": [],
        "labor_outcome_regressions": [],
    }
    return coverage, stability, timing_rows, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    coverage, stability, timing, metadata = build_outputs(args.archive_dir)
    paths = {
        "coverage": args.output_dir / "YAX_ONET_TASK_VINTAGE_COVERAGE.csv",
        "stability": args.output_dir / "YAX_ONET_TASK_ID_STABILITY.csv",
        "timing": args.output_dir / "YAX_ONET_UPDATE_TIMING.csv",
    }
    coverage.to_csv(paths["coverage"], index=False, quoting=csv.QUOTE_MINIMAL)
    stability.to_csv(paths["stability"], index=False, quoting=csv.QUOTE_MINIMAL)
    timing.to_csv(paths["timing"], index=False, quoting=csv.QUOTE_MINIMAL)
    receipt = args.output_dir / "YAX_ONET_DYNAMIC_TASK_EXECUTION_RECEIPT.json"
    metadata["outputs"] = {path.name: sha256(path) for path in paths.values()}
    receipt.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    summary = {
        "occupations": len(coverage),
        "ge_2_genuine": int(coverage.genuine_task_domain_snapshots.ge(2).sum()),
        "ge_3_genuine": int(coverage.genuine_task_domain_snapshots.ge(3).sum()),
        "pre_and_post_2022": int(coverage.has_pre_and_post_2022.sum()),
        "multiple_pre_and_post_2022": int(coverage.has_multiple_pre_and_post_2022.sum()),
        "median_months_between_updates": float(timing.months_since_previous_genuine_snapshot.median()),
        "output_hashes": metadata["outputs"],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

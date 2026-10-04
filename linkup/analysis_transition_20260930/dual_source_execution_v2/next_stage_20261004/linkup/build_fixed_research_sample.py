#!/usr/bin/env python3
"""Build the fixed 4,000 A + 4,000 B + 2,000 C LinkUp research sample.

A and B are nested in the accepted old 40,300-record probability sample. C is
drawn from the eligible null-arm joined frame in the same 69 old support cells.
That joined frame is upstream-filtered to explicit GenAI/software use/develop;
C is a residual technology-candidate diagnostic, not occupation-wide background.
Private keys are written only below an explicitly private output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SEED = "20261004"
VERSION = "linkup_next_stage_fixed_sample_v1"
AI_FIELDS = (
    "tech_generative_ai_detected",
    "tech_predictive_ai_detected",
    "tech_unspecified_ai_detected",
)
CELL = ("OCCUPATION_MAJOR", "CENSUS_REGION", "created_year")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def allocate_positive(counts: dict[tuple, int], total: int) -> dict[tuple, int]:
    """Capped Hamilton allocation with one draw in every positive cell."""
    positive = {k: int(v) for k, v in counts.items() if int(v) > 0}
    if total < len(positive) or total > sum(positive.values()):
        raise ValueError("requested total cannot give every positive cell one draw")
    allocation = {k: 1 for k in positive}
    remaining = total - len(positive)
    capacities = {k: positive[k] - 1 for k in positive}
    while remaining:
        capacity_total = sum(capacities.values())
        if capacity_total <= 0:
            raise RuntimeError("allocation exhausted capacity")
        quotas = {k: remaining * capacities[k] / capacity_total for k in positive}
        base = {k: min(capacities[k], int(quotas[k])) for k in positive}
        used = sum(base.values())
        for k, n in base.items():
            allocation[k] += n
            capacities[k] -= n
        remaining -= used
        if remaining:
            order = sorted(
                (k for k in positive if capacities[k] > 0),
                key=lambda k: (-(quotas[k] - int(quotas[k])), k),
            )
            for k in order[:remaining]:
                allocation[k] += 1
                capacities[k] -= 1
            remaining -= min(remaining, len(order))
    return allocation


def cell_key(row: dict) -> tuple:
    return tuple(row[x] for x in CELL)


def stable_order(salt: str, key: str) -> str:
    return hashlib.md5((SEED + "|" + salt + "|" + key).encode()).hexdigest()


def sample_nested(formal_path: Path) -> tuple[list[dict], list[dict]]:
    rows = pq.read_table(formal_path).to_pylist()
    if len(rows) != 40300:
        raise RuntimeError(f"expected frozen 40,300-row sample, found {len(rows)}")
    out, allocations = [], []
    for arm in ("A", "B"):
        arm_rows = [r for r in rows if r["arm"] == arm]
        counts: dict[tuple, int] = {}
        for row in arm_rows:
            counts[cell_key(row)] = counts.get(cell_key(row), 0) + 1
        if len(counts) != 69:
            raise RuntimeError(f"arm {arm} does not cover all 69 support cells")
        alloc = allocate_positive(counts, 4000)
        grouped: dict[tuple, list[dict]] = {k: [] for k in counts}
        for row in arm_rows:
            grouped[cell_key(row)].append(row)
        for key, values in grouped.items():
            selected_n, nested_N = alloc[key], counts[key]
            chosen = sorted(values, key=lambda r: (stable_order("next-" + arm, r["JOB_HASH"]), r["JOB_HASH"]))[:selected_n]
            for rank, row in enumerate(chosen, 1):
                original_pi = float(row["inclusion_probability"])
                conditional_pi = selected_n / nested_N
                out.append({
                    **row, "arm": arm, "sample_rank_in_cell_arm": rank,
                    "nested_frame_cell_arm_N": nested_N, "next_selected_cell_arm_n": selected_n,
                    "original_inclusion_probability": original_pi,
                    "conditional_inclusion_probability": conditional_pi,
                    "total_inclusion_probability": original_pi * conditional_pi,
                    "nested_design_weight": 1.0 / (original_pi * conditional_pi),
                    "pooled_cell_standardization_weight": float(row["W_h"]),
                })
            allocations.append({
                **dict(zip(CELL, key)), "arm": arm, "frame_cell_arm_N": nested_N,
                "selected_cell_arm_n": selected_n,
                "original_inclusion_probability": float(values[0]["inclusion_probability"]),
                "conditional_inclusion_probability": selected_n / nested_N,
                "total_inclusion_probability": float(values[0]["inclusion_probability"]) * selected_n / nested_N,
                "pooled_cell_standardization_weight": float(values[0]["W_h"]),
            })
    return out, allocations


def sample_c(joined_dir: Path, cells: list[dict], threads: int, memory: str) -> tuple[list[dict], list[dict]]:
    import duckdb
    if not memory[:-2].isdigit() or memory[-2:] not in {"GB", "MB"}:
        raise ValueError("memory limit must be an integer followed by GB or MB")
    files = sorted(joined_dir.glob("*.parquet"))
    if len(files) != 16:
        raise RuntimeError(f"expected 16 joined frame partitions, found {len(files)}")
    con = duckdb.connect()
    con.execute(f"PRAGMA threads={int(threads)}")
    con.execute(f"PRAGMA memory_limit='{memory}'")
    con.read_parquet([str(x) for x in files], union_by_name=True).create_view("joined_input")
    cell_table = pa.Table.from_pylist([
        {**{k: row[k] for k in CELL}, "W_h": row["pooled_cell_standardization_weight"]}
        for row in cells if row["arm"] == "A"
    ])
    con.register("support_cells", cell_table)
    no_ai = " AND ".join(f"j.{x}=false" for x in AI_FIELDS)
    con.execute(f"""
      CREATE TABLE c_frame AS
      SELECT j.JOB_HASH,j.SOURCE_FILE,j.SOURCE_ROW,j.RECORD_SOURCE_ROW,
             j.OCCUPATION_MAJOR,j.CENSUS_REGION,
             year(CAST(j.CREATED AS DATE))::INTEGER AS created_year,s.W_h
      FROM joined_input j JOIN support_cells s
        ON j.OCCUPATION_MAJOR=s.OCCUPATION_MAJOR AND j.CENSUS_REGION=s.CENSUS_REGION
       AND year(CAST(j.CREATED AS DATE))=s.created_year
      WHERE j.usable=true
        AND CAST(j.CREATED AS DATE) BETWEEN DATE '2018-01-01' AND DATE '2026-06-30'
        AND (CASE
          WHEN j.tech_generative_ai_use_explicit=true THEN 'A'
          WHEN j.tech_traditional_software_use_explicit=true AND {no_ai} THEN 'B'
          ELSE NULL END) IS NULL
    """)
    counts_rows = con.execute("SELECT OCCUPATION_MAJOR,CENSUS_REGION,created_year,count(*) N FROM c_frame GROUP BY 1,2,3").fetchall()
    counts = {(a, b, c): n for a, b, c, n in counts_rows}
    alloc = allocate_positive(counts, 2000)
    allocation_table = pa.Table.from_pylist([
        {**dict(zip(CELL, k)), "frame_cell_arm_N": counts[k], "selected_cell_arm_n": alloc[k]}
        for k in sorted(alloc)
    ])
    con.register("c_alloc", allocation_table)
    query = f"""
      SELECT c.*, 'C' arm, row_number() OVER (
               PARTITION BY c.OCCUPATION_MAJOR,c.CENSUS_REGION,c.created_year
               ORDER BY md5('{SEED}|next-C|'||c.JOB_HASH),c.JOB_HASH) sample_rank_in_cell_arm,
             a.frame_cell_arm_N AS nested_frame_cell_arm_N,
             a.selected_cell_arm_n AS next_selected_cell_arm_n,
             1.0::DOUBLE AS original_inclusion_probability,
             a.selected_cell_arm_n::DOUBLE/a.frame_cell_arm_N AS conditional_inclusion_probability,
             a.selected_cell_arm_n::DOUBLE/a.frame_cell_arm_N AS total_inclusion_probability,
             a.frame_cell_arm_N::DOUBLE/a.selected_cell_arm_n AS nested_design_weight,
             c.W_h AS pooled_cell_standardization_weight
      FROM c_frame c JOIN c_alloc a USING (OCCUPATION_MAJOR,CENSUS_REGION,created_year)
      QUALIFY sample_rank_in_cell_arm<=a.selected_cell_arm_n
    """
    selected = con.execute(query).fetch_arrow_table().to_pylist()
    con.close()
    allocations = [
        {**dict(zip(CELL, k)), "arm": "C", "frame_cell_arm_N": counts[k],
        "selected_cell_arm_n": alloc[k], "original_inclusion_probability": 1.0,
        "conditional_inclusion_probability": alloc[k] / counts[k],
        "total_inclusion_probability": alloc[k] / counts[k],
        "pooled_cell_standardization_weight": next(r["pooled_cell_standardization_weight"] for r in cells if r["arm"] == "A" and cell_key(r) == k)}
        for k in sorted(alloc)
    ]
    return selected, allocations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-formal", type=Path, required=True)
    parser.add_argument("--joined-dir", type=Path)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--memory-limit", default="8GB")
    args = parser.parse_args()
    args.private_output.mkdir(parents=True, exist_ok=True)
    os.chmod(args.private_output, 0o700)
    args.public_output.mkdir(parents=True, exist_ok=True)

    selected, allocations = sample_nested(args.frozen_formal)
    status = "ab_complete_c_pending_no_joined_frame"
    if args.joined_dir:
        c_selected, c_allocations = sample_c(args.joined_dir, allocations, args.threads, args.memory_limit)
        selected.extend(c_selected)
        allocations.extend(c_allocations)
        status = "complete"
    counts = {arm: sum(row["arm"] == arm for row in selected) for arm in ("A", "B", "C")}
    if counts["A"] != 4000 or counts["B"] != 4000 or (args.joined_dir and counts["C"] != 2000):
        raise RuntimeError(f"sample count invariant failed: {counts}")

    key_path = args.private_output / "FIXED_RESEARCH_SAMPLE_KEYS_PRIVATE.parquet"
    pq.write_table(pa.Table.from_pylist(selected), key_path, compression="zstd")
    os.chmod(key_path, 0o600)
    allocation_path = args.public_output / "cell_allocation.csv"
    import csv
    fields = list(allocations[0])
    with allocation_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(allocations)
    receipt = {
        "status": status, "version": VERSION, "seed": int(SEED), "counts": counts,
        "frame": "usable ads in the original 69 OCCUPATION_MAJOR x CENSUS_REGION x CREATED-year support cells, 2018-01-01 through 2026-06-30",
        "arms": {
            "A": "old C1 explicit generative-AI use arm, nested in accepted 40,300 sample",
            "B": "old C1 explicit traditional-software use with no detected AI, nested in accepted 40,300 sample",
            "C": "neither A nor B within the upstream explicit GenAI/software use/develop candidate frame; restricted diagnostic, not occupation-wide background or untreated",
        },
        "allocation": "capped proportional Hamilton allocation with minimum one selected record in every positive supported cell; fixed MD5 order",
        "probabilities": "total_inclusion_probability = original_inclusion_probability * conditional_inclusion_probability; nested_design_weight is its inverse",
        "standardization": "pooled_cell_standardization_weight is the original pooled A+B frame W_h and is stored separately from design weights",
        "raw_vs_weighted": "raw sample counts must not be presented as weighted estimates",
        "private_key_output": {"path": str(key_path), "sha256": sha256(key_path), "bytes": key_path.stat().st_size},
        "public_allocation_sha256": sha256(allocation_path),
        "frozen_formal_sha256": sha256(args.frozen_formal),
        "model_extraction": "not_run",
        "privacy": "row-level keys and any later ad text remain private and excluded from Git",
    }
    atomic_json(args.public_output / "SAMPLE_EXECUTION_RECEIPT.json", receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()

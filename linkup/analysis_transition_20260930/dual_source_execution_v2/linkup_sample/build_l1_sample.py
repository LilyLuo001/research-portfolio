#!/usr/bin/env python3
"""Freeze the LinkUp L1 key samples from existing narrow products.

This script never reads original description text and never changes an old output.
All row-level outputs contain private keys and must remain outside Git.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import duckdb

VERSION = "linkup_l1_sample_v1"
SEED = "20261004"
AI_FIELDS = (
    "tech_generative_ai_detected",
    "tech_predictive_ai_detected",
    "tech_unspecified_ai_detected",
)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def sql_string(value):
    return "'" + str(value).replace("'", "''") + "'"


def load_private_keys(path):
    if not path:
        return set()
    obj = json.loads(Path(path).read_text())
    rows = obj.get("private_keys", obj.get("selected", [])) if isinstance(obj, dict) else obj
    result = set()
    for row in rows:
        if isinstance(row, str):
            try:
                parsed = json.loads(row)
                result.add(str(parsed[0]))
            except (ValueError, TypeError, IndexError):
                result.add(row)
        elif isinstance(row, dict):
            key = row.get("JOB_HASH", row.get("job_hash"))
            if key is None and "private_key" in row:
                try:
                    key = json.loads(row["private_key"])[0]
                except (ValueError, TypeError, IndexError):
                    key = None
            if key is not None:
                result.add(str(key))
        elif isinstance(row, (list, tuple)) and row:
            result.add(str(row[0]))
    return result


def q(con, query, params=None):
    return con.execute(query, params or []).fetchone()[0]


def export(con, query, path):
    path = Path(path)
    con.execute(f"COPY ({query}) TO {sql_string(path)} (FORMAT PARQUET, COMPRESSION ZSTD)")
    os.chmod(path, 0o600)


def git_ancestor(path):
    path = Path(path).resolve()
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--joined-dir", type=Path, required=True)
    p.add_argument("--narrow-dir", type=Path, required=True)
    p.add_argument("--known-used", type=Path, action="append", default=[])
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--memory-limit", default="24GB")
    p.add_argument("--temp-dir", type=Path)
    p.add_argument("--core-only", action="store_true", help="stop after formal/dev/evaluation/config outputs; do not rescan broad diagnostic frame")
    a = p.parse_args()

    joined = sorted(a.joined_dir.glob("*.parquet"))
    narrow = sorted(x for x in a.narrow_dir.glob("*.parquet") if not x.name.endswith(".durations.parquet"))
    if len(joined) != 16:
        raise RuntimeError(f"expected 16 joined partitions, found {len(joined)}")
    if len(narrow) != 2464:
        raise RuntimeError(f"expected 2464 narrow partitions, found {len(narrow)}")
    repo = git_ancestor(a.output_dir)
    if repo is not None:
        raise RuntimeError(f"private row-level output cannot be inside Git worktree: {repo}")
    a.output_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(a.output_dir, 0o700)
    temp_dir = a.temp_dir or (a.output_dir / "duckdb_tmp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Keep the mutable DuckDB work database in the job-specific temporary area.
    # A canceled Slurm step can leave a distributed-filesystem lock on an output DB.
    con = duckdb.connect(str(temp_dir / "l1_sample.duckdb"))
    con.execute(f"PRAGMA threads={int(a.threads)}")
    con.execute(f"PRAGMA memory_limit={sql_string(a.memory_limit)}")
    con.execute(f"PRAGMA temp_directory={sql_string(temp_dir)}")
    con.read_parquet([str(x) for x in joined], union_by_name=True).create_view("joined_input")

    known = set()
    for path in a.known_used:
        known.update(load_private_keys(path))
    con.execute("CREATE TABLE known_used (JOB_HASH VARCHAR PRIMARY KEY)")
    if known:
        con.executemany("INSERT INTO known_used VALUES (?)", [(x,) for x in sorted(known)])

    no_ai = " AND ".join(f"{x} = false" for x in AI_FIELDS)
    con.execute(f"""
      CREATE TABLE eligible AS
      SELECT *, CASE
        WHEN tech_generative_ai_use_explicit = true THEN 'A'
        WHEN tech_traditional_software_use_explicit = true AND {no_ai} THEN 'B'
        ELSE NULL END AS old_c1_arm,
        CAST(CREATED AS DATE) AS created_date,
        year(CAST(CREATED AS DATE))::INTEGER AS created_year
      FROM joined_input
      WHERE usable = true
        AND CAST(CREATED AS DATE) BETWEEN DATE '2018-01-01' AND DATE '2026-06-30'
        AND coalesce(trim(CAST(OCCUPATION_MAJOR AS VARCHAR)), '') <> ''
        AND coalesce(trim(CAST(CENSUS_REGION AS VARCHAR)), '') <> ''
    """)
    con.execute("""
      CREATE TABLE cell_counts_all AS
      SELECT OCCUPATION_MAJOR, CENSUS_REGION, created_year,
        count(*) FILTER (WHERE old_c1_arm='A')::BIGINT AS frame_count_a,
        count(*) FILTER (WHERE old_c1_arm='B')::BIGINT AS frame_count_b
      FROM eligible GROUP BY 1,2,3
    """)
    con.execute("""
      CREATE TABLE support_cells AS
      SELECT *, least(frame_count_b, 3*frame_count_a)::BIGINT AS sample_count_b,
        1.0::DOUBLE AS inclusion_probability_a,
        least(frame_count_b,3*frame_count_a)::DOUBLE/frame_count_b AS inclusion_probability_b,
        (frame_count_a+frame_count_b)::DOUBLE/sum(frame_count_a+frame_count_b) OVER () AS W_h
      FROM cell_counts_all WHERE frame_count_a >= 20 AND frame_count_b >= 20
    """)
    if q(con, "SELECT count(*) FROM support_cells") != 69:
        raise RuntimeError("old C1 support does not reproduce 69 cells")
    if q(con, "SELECT sum(frame_count_a) FROM support_cells") != 10075:
        raise RuntimeError("old C1 support does not reproduce A=10,075")
    if q(con, "SELECT sum(frame_count_b) FROM support_cells") != 1064428:
        raise RuntimeError("old C1 support does not reproduce B=1,064,428")

    con.execute(f"""
      CREATE TABLE formal_ranked AS
      SELECT e.*, s.frame_count_a, s.frame_count_b, s.sample_count_b,
        s.inclusion_probability_a, s.inclusion_probability_b, s.W_h,
        row_number() OVER (
          PARTITION BY e.OCCUPATION_MAJOR,e.CENSUS_REGION,e.created_year,e.old_c1_arm
          ORDER BY md5({sql_string(SEED)} || '|formal|' || e.JOB_HASH), e.JOB_HASH
        ) AS stable_rank_in_cell_arm
      FROM eligible e JOIN support_cells s USING (OCCUPATION_MAJOR,CENSUS_REGION,created_year)
      WHERE e.old_c1_arm IN ('A','B')
    """)
    con.execute("""
      CREATE TABLE formal_sample AS
      SELECT JOB_HASH,SOURCE_FILE,SOURCE_ROW,RECORD_SOURCE_ROW,
        OCCUPATION_MAJOR,CENSUS_REGION,created_year,old_c1_arm AS arm,
        frame_count_a,frame_count_b,
        CASE WHEN old_c1_arm='A' THEN frame_count_a ELSE sample_count_b END AS selected_cell_arm_n,
        CASE WHEN old_c1_arm='A' THEN inclusion_probability_a ELSE inclusion_probability_b END AS inclusion_probability,
        CASE WHEN old_c1_arm='A' THEN 1.0 ELSE 1.0/inclusion_probability_b END AS design_weight,
        W_h,stable_rank_in_cell_arm
      FROM formal_ranked
      WHERE old_c1_arm='A' OR stable_rank_in_cell_arm <= sample_count_b
    """)

    # Operational near frame: existing T5 candidate-joined rows in the old 69 cells,
    # but outside both old C1 arms. The full 204.8m occupation join is intentionally not rebuilt.
    con.execute("""
      CREATE TABLE near_frame AS
      SELECT e.JOB_HASH,e.SOURCE_FILE,e.SOURCE_ROW,e.RECORD_SOURCE_ROW,
        e.OCCUPATION_MAJOR,e.CENSUS_REGION,e.created_year
      FROM eligible e JOIN support_cells s USING (OCCUPATION_MAJOR,CENSUS_REGION,created_year)
      ANTI JOIN known_used k USING (JOB_HASH)
      WHERE e.old_c1_arm IS NULL
    """)
    near_n = q(con, "SELECT count(*) FROM near_frame")
    if near_n < 300:
        raise RuntimeError(f"near frame has only {near_n} rows")
    con.execute(f"""
      CREATE TABLE diagnostic_near AS
      SELECT *, 'near_existing_t5_candidates_outside_c1' AS diagnostic_stratum,
        300::BIGINT AS selected_stratum_n, {near_n}::BIGINT AS frame_stratum_N,
        300.0/{near_n} AS inclusion_probability,
        row_number() OVER (ORDER BY md5({sql_string(SEED)} || '|near|' || JOB_HASH),JOB_HASH) AS stable_rank
      FROM near_frame QUALIFY stable_rank <= 300
    """)

    # Development/evaluation keys are provisional until original text is materialized and
    # SHA-256-grouped. Known historical review keys are excluded now; text duplicates cannot be.
    con.execute("""
      CREATE TABLE subset_frame AS
      SELECT f.* FROM formal_sample f ANTI JOIN known_used k USING (JOB_HASH)
    """)
    for arm in ("A", "B"):
        available = q(con, "SELECT count(*) FROM subset_frame WHERE arm=?", [arm])
        if available < 200:
            raise RuntimeError(f"arm {arm} has fewer than 200 subset candidates")
    con.execute(f"""
      CREATE TABLE development_keys AS
      SELECT *, 'development_200' AS subset,
        row_number() OVER (PARTITION BY arm ORDER BY md5({sql_string(SEED)} || '|dev|' || JOB_HASH),JOB_HASH) AS subset_arm_rank,
        100.0/count(*) OVER (PARTITION BY arm) AS subset_inclusion_probability
      FROM subset_frame QUALIFY subset_arm_rank <= 100
    """)
    con.execute(f"""
      CREATE TABLE evaluation_keys AS
      SELECT *, 'locked_evaluation_200' AS subset,
        row_number() OVER (PARTITION BY arm ORDER BY md5({sql_string(SEED)} || '|eval|' || JOB_HASH),JOB_HASH) AS subset_arm_rank,
        100.0/count(*) OVER (PARTITION BY arm) AS subset_inclusion_probability
      FROM subset_frame ANTI JOIN development_keys USING (JOB_HASH)
      QUALIFY subset_arm_rank <= 100
    """)
    con.execute(f"""
      CREATE TABLE config_compare_keys AS
      SELECT *, 'configuration_compare_80' AS subset,
        row_number() OVER (PARTITION BY arm ORDER BY md5({sql_string(SEED)} || '|config|' || JOB_HASH),JOB_HASH) AS config_arm_rank,
        0.4::DOUBLE AS conditional_probability_within_development
      FROM development_keys QUALIFY config_arm_rank <= 40
    """)

    # Write the formal and development artifacts before the broad 204.8m-row scan.
    core_outputs = {
        "L1_CELL_COUNTS_PRIVATE.parquet": "SELECT * FROM support_cells ORDER BY OCCUPATION_MAJOR,CENSUS_REGION,created_year",
        "L1_FORMAL_SAMPLE_KEYS_PRIVATE.parquet": "SELECT * FROM formal_sample ORDER BY arm,OCCUPATION_MAJOR,CENSUS_REGION,created_year,stable_rank_in_cell_arm",
        "L1_DEVELOPMENT_200_KEYS_PROVISIONAL.parquet": "SELECT * FROM development_keys ORDER BY arm,subset_arm_rank",
        "L1_EVALUATION_200_KEYS_PROVISIONAL.parquet": "SELECT * FROM evaluation_keys ORDER BY arm,subset_arm_rank",
        "L1_CONFIG_COMPARE_80_KEYS_PROVISIONAL.parquet": "SELECT * FROM config_compare_keys ORDER BY arm,config_arm_rank",
    }
    for name, query in core_outputs.items():
        export(con, query, a.output_dir / name)
    core_counts = {
        "support_cells": q(con, "SELECT count(*) FROM support_cells"),
        "formal_A": q(con, "SELECT count(*) FROM formal_sample WHERE arm='A'"),
        "formal_B": q(con, "SELECT count(*) FROM formal_sample WHERE arm='B'"),
        "formal_total": q(con, "SELECT count(*) FROM formal_sample"),
        "known_review_JOB_HASH_excluded_from_subsets": len(known),
        "development": q(con, "SELECT count(*) FROM development_keys"),
        "evaluation": q(con, "SELECT count(*) FROM evaluation_keys"),
        "config_compare": q(con, "SELECT count(*) FROM config_compare_keys"),
        "development_evaluation_overlap": q(con, "SELECT count(*) FROM development_keys JOIN evaluation_keys USING(JOB_HASH)"),
        "expected_formal_B_sum_sample_count_b": q(con, "SELECT sum(sample_count_b) FROM support_cells"),
    }
    if core_counts["development"] != 200 or core_counts["evaluation"] != 200 or core_counts["config_compare"] != 80:
        raise RuntimeError("development/evaluation/config counts failed")
    if core_counts["development_evaluation_overlap"]:
        raise RuntimeError("development/evaluation overlap invariant failed")
    if core_counts["formal_B"] != core_counts["expected_formal_B_sum_sample_count_b"]:
        raise RuntimeError("formal B count differs from sum(sample_count_b)")
    cell_mismatches = q(con, """
      SELECT count(*) FROM (
        SELECT s.OCCUPATION_MAJOR,s.CENSUS_REGION,s.created_year,
          s.frame_count_a,s.sample_count_b,
          count(*) FILTER (WHERE f.arm='A') AS selected_a,
          count(*) FILTER (WHERE f.arm='B') AS selected_b
        FROM support_cells s LEFT JOIN formal_sample f
          USING (OCCUPATION_MAJOR,CENSUS_REGION,created_year)
        GROUP BY 1,2,3,4,5
      ) x WHERE selected_a<>frame_count_a OR selected_b<>sample_count_b
    """)
    if cell_mismatches:
        raise RuntimeError(f"formal sample has {cell_mismatches} cell-arm count mismatches")
    max_b_weight_error = q(con, """
      SELECT max(abs(weighted_b-frame_count_b)) FROM (
        SELECT s.OCCUPATION_MAJOR,s.CENSUS_REGION,s.created_year,s.frame_count_b,
          sum(f.design_weight) FILTER (WHERE f.arm='B') AS weighted_b
        FROM support_cells s LEFT JOIN formal_sample f
          USING (OCCUPATION_MAJOR,CENSUS_REGION,created_year)
        GROUP BY 1,2,3,4
      ) x
    """)
    if max_b_weight_error is None or max_b_weight_error > 1e-7:
        raise RuntimeError(f"B inverse-probability weights do not recover frame cells: {max_b_weight_error}")
    core_counts["cell_arm_count_mismatches"] = cell_mismatches
    core_counts["max_B_weighted_cell_reconstruction_error"] = max_b_weight_error
    if abs(q(con, "SELECT sum(W_h) FROM support_cells") - 1.0) > 1e-12:
        raise RuntimeError("W_h does not sum to one")
    core_receipt = {
        "status": "core_keys_complete_subsets_provisional_pending_text_dedup_broad_pending",
        "version": VERSION, "seed": SEED, "counts": core_counts,
        "heldout_400_status": "unavailable_not_claimed_excluded",
        "text_deduplication_status": "not_completed_original_text_not_materialized",
        "outputs": {name: {"sha256": sha256(a.output_dir / name), "bytes": (a.output_dir / name).stat().st_size}
                    for name in core_outputs},
    }
    atomic_json(a.output_dir / "L1_CORE_RECEIPT_PRIVATE.json", core_receipt)
    os.chmod(a.output_dir / "L1_CORE_RECEIPT_PRIVATE.json", 0o600)
    if a.core_only:
        con.close()
        return

    # Broad frame last: all usable semantic-narrow keys outside the entire T5 joined table.
    # ORDER BY ... LIMIT is a bounded Top-N plan, not a 204.8m-row window materialization.
    con.read_parquet([str(x) for x in narrow], union_by_name=True).create_view("narrow_input")
    con.execute("CREATE TABLE joined_keys AS SELECT DISTINCT JOB_HASH FROM joined_input")
    con.execute("""
      CREATE VIEW broad_frame AS
      SELECT n.JOB_HASH,n.SOURCE_FILE,n.SOURCE_ROW,n.RECORD_SOURCE_ROW
      FROM narrow_input n
      ANTI JOIN joined_keys j USING (JOB_HASH)
      ANTI JOIN known_used k USING (JOB_HASH)
      WHERE n.usable = true
    """)
    broad_n = q(con, "SELECT count(*) FROM broad_frame")
    if broad_n < 300:
        raise RuntimeError(f"broad frame has only {broad_n} rows")
    con.execute(f"""
      CREATE TABLE diagnostic_broad AS
      SELECT *, 'broad_usable_outside_entire_t5_join' AS diagnostic_stratum,
        300::BIGINT AS selected_stratum_n, {broad_n}::BIGINT AS frame_stratum_N,
        300.0/{broad_n} AS inclusion_probability,
        row_number() OVER (ORDER BY md5({sql_string(SEED)} || '|broad|' || JOB_HASH),JOB_HASH) AS stable_rank
      FROM (
        SELECT * FROM broad_frame
        ORDER BY md5({sql_string(SEED)} || '|broad|' || JOB_HASH),JOB_HASH
        LIMIT 300
      ) selected_broad
    """)
    con.execute("CREATE TABLE diagnostic_sample AS SELECT * FROM diagnostic_near UNION ALL BY NAME SELECT * FROM diagnostic_broad")

    diagnostic_outputs = {
        "L1_DIAGNOSTIC_600_KEYS_PRIVATE.parquet": "SELECT * FROM diagnostic_sample ORDER BY diagnostic_stratum,stable_rank",
    }
    for name, query in diagnostic_outputs.items():
        export(con, query, a.output_dir / name)

    counts = {
        "support_cells": q(con, "SELECT count(*) FROM support_cells"),
        "formal_A": q(con, "SELECT count(*) FROM formal_sample WHERE arm='A'"),
        "formal_B": q(con, "SELECT count(*) FROM formal_sample WHERE arm='B'"),
        "formal_total": q(con, "SELECT count(*) FROM formal_sample"),
        "near_frame_N": near_n,
        "near_selected": q(con, "SELECT count(*) FROM diagnostic_near"),
        "broad_frame_N": broad_n,
        "broad_selected": q(con, "SELECT count(*) FROM diagnostic_broad"),
        "known_review_JOB_HASH_excluded_from_diagnostics_and_subsets": len(known),
        "development": q(con, "SELECT count(*) FROM development_keys"),
        "evaluation": q(con, "SELECT count(*) FROM evaluation_keys"),
        "config_compare": q(con, "SELECT count(*) FROM config_compare_keys"),
        "development_evaluation_overlap": q(con, "SELECT count(*) FROM development_keys JOIN evaluation_keys USING(JOB_HASH)"),
        "near_broad_overlap": q(con, "SELECT count(*) FROM diagnostic_near JOIN diagnostic_broad USING(JOB_HASH)"),
    }
    if counts["near_selected"] != 300 or counts["broad_selected"] != 300:
        raise RuntimeError("diagnostic sample counts failed")
    if counts["development"] != 200 or counts["evaluation"] != 200 or counts["config_compare"] != 80:
        raise RuntimeError("development/evaluation/config counts failed")
    if counts["development_evaluation_overlap"] or counts["near_broad_overlap"]:
        raise RuntimeError("sample overlap invariant failed")
    if abs(q(con, "SELECT sum(W_h) FROM support_cells") - 1.0) > 1e-12:
        raise RuntimeError("W_h does not sum to one")

    receipt = {
        "status": "keys_complete_subsets_provisional_pending_text_dedup",
        "version": VERSION,
        "seed": SEED,
        "counts": counts,
        "sampling": {
            "formal": "old C1 69 support cells; all A; B bottom stable MD5 ranks by cell with sample_count_b=min(frame_count_b,3*frame_count_a)",
            "old_weight": "W_h=(frame_count_a+frame_count_b)/sum_h(frame_count_a+frame_count_b) over the 69 old support cells",
            "near": "SRS-by-frozen-hash from existing T5 joined candidates in the 69 cells but outside both C1 arms",
            "broad": "SRS-by-frozen-hash from usable semantic narrow, excluding every key in existing T5 joined input",
            "diagnostic_overlap": "frames are disjoint because broad excludes the entire T5 joined input",
            "subsets": "100 per old arm for development and evaluation; evaluation excludes development; config comparison is 40 per arm within development",
        },
        "known_review_exclusion": {
            "sources": [str(x) for x in a.known_used],
            "distinct_JOB_HASH": len(known),
            "heldout_400_status": "unavailable_not_claimed_excluded",
        },
        "text_deduplication": {
            "status": "not_completed_original_text_not_materialized_in_L1",
            "required_next_step": "materialize selected original texts, normalize only the frozen summary-exclusion rule, group by cryptographic full-text digest, then finalize the 200/200/80 lists before evaluation reveal",
            "claim_limit": "provisional subset key lists do not establish independence from repeated description text",
        },
        "near_frame_limit": "candidate-near only: uses the existing 6,010,975-row T5 technology-candidate join and therefore diagnoses C1 arm/role screening inside that table; it is not the contract's broader all-text same-cell frame and cannot measure technology-term misses outside T5",
        "missing_broader_cell_coverage": "full usable-text occupation-region-CREATED-year columns are unavailable without rebuilding the full Records/O*NET join; intentionally not rebuilt for this 600-row diagnostic",
        "input_inventory": {"joined_files": len(joined), "narrow_main_files": len(narrow)},
        "outputs": {},
    }
    for name in {**core_outputs, **diagnostic_outputs}:
        path = a.output_dir / name
        receipt["outputs"][name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    atomic_json(a.output_dir / "L1_SAMPLE_RECEIPT_PRIVATE.json", receipt)
    os.chmod(a.output_dir / "L1_SAMPLE_RECEIPT_PRIVATE.json", 0o600)
    con.close()


if __name__ == "__main__":
    main()

"""Create outcome-blind local delivery tables from seed and aggregate receipts only."""
import csv
import hashlib
import json
import argparse
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts-dir", default="receipts", type=Path)
    parser.add_argument("--out-dir", default="delivery", type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parents[1]
    seed_path = here / "out_v3" / "seed_stock_wave.csv"
    roster = json.loads((here / "out_v3" / "ROSTER_RECEIPT.json").read_text())
    receipts = here / args.receipts_dir
    bridge = json.loads((receipts / "pit_bridge_receipt.json").read_text())
    aggregate = json.loads((receipts / "earnings_metadata_aggregate.json").read_text())
    projected = json.loads((receipts / "ibes_projection_receipt.json").read_text())
    out = here / args.out_dir
    out.mkdir(exist_ok=False)

    seed_rows = list(csv.DictReader(seed_path.open(newline="")))
    gaps = []
    for row in seed_rows:
        gaps.append({
            "source_version": row["source_version"],
            "source_row_locator": row["source_row_locator"],
            "permno": row["permno"], "old_wave_id": row["wave_id"],
            "old_effective_date": row["effective_date"],
            "package_or_fund_reference": row["source_accessions"] or "UNKNOWN",
            "announcement_evidence": "MISSING_NOT_IN_E007_SEED",
            "pre_announcement_holdings": "MISSING_NOT_VERIFIED_BY_E007_SEED",
            "denominator_or_corporate_action": "MISSING_NOT_VERIFIED_BY_E007_SEED",
            "effective_identifier_mapping": "DATE_VALID_PIT_BRIDGE_EXISTS_FOR_SOME_SEED_ROWS_ONLY; SEE_SCC_RECEIPT",
            "new_clock_status": "UNKNOWN_NOT_ASSESSED",
        })
    write_csv(out / "NEW_CLOCK_MEMBERSHIP_GAPS.csv", list(gaps[0]), gaps)

    rows = [
        ("E007 reconstructed exposure", "retrieval seed", "all E007 rows", "source rows", roster["input_rows"], "MEASURED", "E007 CSV"),
        ("E007 reconstructed exposure", "retrieval seed", "all E007 rows", "primary_ready seed stock-wave rows", roster["seed_stock_wave_rows"], "MEASURED", "E007 CSV"),
        ("E007 reconstructed exposure", "retrieval seed", "primary_ready seed rows", "unique PERMNO securities", roster["seed_security_rows"], "MEASURED", "E007 CSV"),
        ("E007 seed roster", "PIT identifier bridge", "seed stock-wave rows", "date-valid usable mapped seed rows", bridge["mapped_seed_rows"], "MEASURED", "SCC PIT receipt"),
        ("E007 seed roster", "PIT identifier bridge", "seed stock-wave rows", "missing mapping seed rows", bridge["missing_seed_rows"], "MEASURED", "SCC PIT receipt"),
        ("E007 seed roster", "PIT identifier bridge", "seed stock-wave rows", "ambiguous mapping seed rows", bridge["ambiguous_seed_rows"], "MEASURED", "SCC PIT receipt"),
        ("E007 seed roster", "IBES metadata projection", "date-valid candidate CUSIPs", "candidate CUSIPs", bridge["candidate_cusips"], "MEASURED", "SCC PIT receipt"),
        ("E007 seed roster", "IBES metadata projection", "candidate CUSIPs", "CUSIPs with source records", aggregate["candidate_cusips_with_source_records"], "MEASURED", "SCC aggregate receipt"),
        ("E007 seed roster", "IBES metadata projection", "filtered source records", "source records", aggregate["source_record_count"], "MEASURED", "SCC aggregate receipt"),
        ("E007 seed roster", "IBES metadata projection", "filtered source records", "parseable announcement dates", aggregate["announcement_date_parseable_records"], "MEASURED", "SCC aggregate receipt"),
        ("E007 seed roster", "IBES metadata projection", "filtered source records", "parseable announcement times", aggregate["announcement_time_parseable_records"], "MEASURED", "SCC aggregate receipt"),
        ("E007 seed roster", "economic event construction", "filtered source records", "unique economic events", "", "NOT_ASSESSED", "revision/event rule unavailable"),
        ("E007 seed roster", "session support", "filtered source records", "RTH/non-RTH", "", "NOT_ASSESSED", "timezone/calendar rule unavailable"),
    ]
    for partition, count in aggregate["annual_partition_record_counts"].items():
        rows.append(("E007 seed roster", "IBES metadata projection", partition, "source records", count, "MEASURED", "SCC aggregate receipt"))
    write_csv(out / "EARNINGS_METADATA_CENSUS.csv", ["population", "stage", "denominator", "metric", "value", "status", "source"],
              [dict(zip(["population", "stage", "denominator", "metric", "value", "status", "source"], row)) for row in rows])
    receipt = {
        "status": "METADATA_PROJECTED_ECONOMIC_EVENT_RULE_PENDING",
        "purpose": "EARNINGS_METADATA_RETRIEVAL_SEED_ONLY",
        "analysis_eligible": "NOT_ASSESSED",
        "new_clock_completeness": "UNKNOWN",
        "source_hashes": {"E007": roster["E007_sha256"], "E011": roster["E011_sha256"]},
        "local_input_hashes": {p.name: sha256(p) for p in [seed_path, here / "out_v3" / "ROSTER_RECEIPT.json", receipts / "pit_bridge_receipt.json", receipts / "earnings_metadata_aggregate.json", receipts / "ibes_projection_receipt.json"]},
        "local_output_hashes": {p.name: sha256(p) for p in out.iterdir()},
        "scc_raw_metadata_location": "/projectnb/econdept/qluo/P1_Refraction_WRDS/p1_roster_earnings_20260913/ibes_metadata_projection_v2/ibes_announcement_metadata.csv",
        "raw_metadata_copied_to_local": False,
        "outcome_fields_read_or_exported": False,
        "projection_columns": projected["columns"],
    }
    (out / "EXECUTION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Self-check the aggregate March-replacement audit outputs."""
from __future__ import annotations

import argparse
import csv
import json
import pathlib


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=pathlib.Path, required=True)
    args = parser.parse_args()
    receipt = json.loads((args.results / "MARCH_REPLACEMENT_AUDIT_RECEIPT.json").read_text())
    fields = json.loads((args.results / "SURVEY_FIELD_AUDIT.json").read_text())
    with (args.results / "MARCH_SAMPLE_OVERLAP_AND_STOCK.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    checks = []

    def check(condition: bool, message: str) -> None:
        checks.append({"check": message, "pass": bool(condition)})
        if not condition:
            raise RuntimeError(message)

    check(receipt["status"] == "PASS_FUNCTIONAL_REPLACEMENT", "replacement receipt passes")
    check(len(rows) == 5, "five repaired March months")
    check(all(row["functional_replacement_pass"] == "True" for row in rows), "each month passes")
    check(all(int(row["wide_positive_weight_records"]) == 0 for row in rows), "wide ASEC has zero positive final weights")
    check(all(float(row["wide_active_routed_stock"]) == 0 for row in rows), "wide ASEC contributes zero routed stock")
    check(all(float(row["repair_active_routed_stock"]) > 0 for row in rows), "Basic repair contributes positive routed stock")
    check(all(abs(float(row["append_minus_replacement_routed_stock"])) < 1e-8 for row in rows), "append equals replacement after the weight filter")
    check(all(int(row["active_overlap_CPSIDP"]) == 0 for row in rows), "no active person overlap")
    check(fields["candidate_public_stratum_PSU_or_replicate_fields"] == [], "no design fields found")
    check(fields["design_based_inference_available"] is False, "design-based inference not claimed")
    forbidden = {"SERIAL", "CPSID", "CPSIDP", "CPSIDV"}
    header = set(rows[0])
    check(not (header & forbidden), "no raw identifier column serialized")
    (args.results / "SELF_CHECK_MARCH_REPLACEMENT.json").write_text(
        json.dumps({"status": "PASS", "checks": checks}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()


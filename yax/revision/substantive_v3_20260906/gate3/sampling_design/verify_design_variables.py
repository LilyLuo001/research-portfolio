#!/usr/bin/env python3
"""Publish a sanitized header-only audit of authorized CPS design variables."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path


EXPECTED = {
    "wide": "3fe42477e6f2ce401e85123f0e278e758595c1c4071a8743f243a92752db38c9",
    "march_repair": "a4ae2ef06d66a0d47359ccceffff9a15843ac501a9f25f9a05aa8fdca9c4f911",
}
REQUIRED = {"YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP",
            "CPSIDV", "MISH", "WTFINL", "HWTFINL"}
PUBLIC_DESIGN_NAMES = {"PSU", "STRATA", "STRATUM"}
SOURCE_URLS = {
    "CPSID": "https://cps.ipums.org/cps-action/variables/CPSID",
    "CPSIDP": "https://cps.ipums.org/cps-action/variables/CPSIDP",
    "CPSIDV": "https://cps.ipums.org/cps-action/variables/CPSIDV",
    "SERIAL": "https://cps.ipums.org/cps-action/variables/SERIAL",
    "MISH": "https://cps.ipums.org/cps-action/variables/MISH",
    "WTFINL": "https://cps.ipums.org/cps-action/variables/WTFINL",
    "replicate_weights": "https://cps.ipums.org/cps/repwt.shtml",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def gzip_header(path: Path) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        row = next(csv.reader(stream))
    if not row or len(row) != len(set(row)):
        raise RuntimeError("extract header is empty or duplicated")
    return row


def audit_headers(headers: dict[str, list[str]], hashes: dict[str, str]) -> dict:
    if set(headers) != set(EXPECTED) or set(hashes) != set(EXPECTED):
        raise RuntimeError("logical input inventory differs")
    if hashes != EXPECTED:
        raise RuntimeError("authorized extract hash differs")
    for label, columns in headers.items():
        missing = REQUIRED - set(columns)
        if missing:
            raise RuntimeError(f"{label} lacks required header variables: {sorted(missing)}")
    all_columns = set.intersection(*(set(value) for value in headers.values()))
    replicate = sorted(name for name in set.union(*(set(value) for value in headers.values()))
                       if name.startswith("REPWT"))
    public_design = sorted(PUBLIC_DESIGN_NAMES & set.union(
        *(set(value) for value in headers.values())))
    if replicate or public_design:
        raise RuntimeError("unexpected public design variable found; interpretation must be revisited")
    return {
        "schema_version": "yax-gate3-cps-design-variable-audit-v1",
        "status": "PASS_AUTHORIZED_EXTRACT_HEADER_AUDIT",
        "inputs": {
            label: {"sha256": hashes[label], "columns": headers[label]}
            for label in sorted(headers)
        },
        "common_required_variables": sorted(REQUIRED & all_columns),
        "public_PSU_or_stratum_variables": public_design,
        "replicate_weight_variables": replicate,
        "interpretation": {
            "CPSID": "longitudinal household linking unit; common multiplier may preserve observed co-resident and repeated-month dependence",
            "CPSIDP_CPSIDV": "person linking identifiers; CPSIDV is demographic-validated and CPSIDP requires linkage checks",
            "SERIAL": "unique only within YEAR and MONTH; not a longitudinal household unit",
            "MISH": "rotation position in the 4-8-4 pattern; eight values are not eight independent PSUs",
            "WTFINL": "final person weight for Basic Monthly analysis",
            "ASEC_replicates": "not present and not transferable to Basic Monthly inference",
            "design_based_inference": False,
        },
        "official_source_urls": SOURCE_URLS,
        "privacy": "header names and whole-file hashes only; no row, identifier value, stock, or private path serialized",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wide", type=Path, required=True)
    parser.add_argument("--march-repair", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {"wide": args.wide, "march_repair": args.march_repair}
    result = audit_headers(
        {label: gzip_header(path) for label, path in paths.items()},
        {label: sha256_file(path) for label, path in paths.items()},
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": result["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

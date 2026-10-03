#!/usr/bin/env python3
"""Build the bounded CPS historical occupation/RTI composition benchmark.

The program reads an IPUMS CPS CSV or CSV.GZ and the frozen CPS OCC2010
computerization lookup. It fails closed if the verified schema is absent.
It does not use earnings fields and does not estimate a causal model.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


REQUIRED_CPS = {"YEAR", "ASECFLAG", "ASECWT", "EMPSTAT", "OCC2010"}
REQUIRED_MAP = {"cps_occ2010", "rti_autor_dorn"}
EMPLOYED_CODES = {"10", "12"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


def code(value: str) -> str:
    text = value.strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(4)


def weighted_cutpoints(values, probs=(0.25, 0.5, 0.75)):
    ordered = sorted(values)
    total = sum(weight for _, weight in ordered)
    if total <= 0:
        raise ValueError("no positive mapped early-window weight")
    result, cumulative, index = [], 0.0, 0
    for probability in probs:
        target = probability * total
        while index < len(ordered) and cumulative < target:
            cumulative += ordered[index][1]
            value = ordered[index][0]
            index += 1
        result.append(value)
    return result


def group(value: float, cuts) -> str:
    if value <= cuts[0]:
        return "q1_low_rti"
    if value <= cuts[1]:
        return "q2"
    if value <= cuts[2]:
        return "q3"
    return "q4_high_rti"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cps", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--mapping-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--early-years", default="2004,2005,2006")
    parser.add_argument("--late-years", default="2023,2024,2025")
    args = parser.parse_args()
    early = tuple(int(x) for x in args.early_years.split(","))
    late = tuple(int(x) for x in args.late_years.split(","))
    if set(early) & set(late):
        raise ValueError("early and late windows must not overlap")

    rti = {}
    with args.mapping.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_MAP - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"mapping missing required fields: {sorted(missing)}")
        for row in reader:
            raw = row["rti_autor_dorn"].strip()
            if raw:
                occ = code(row["cps_occ2010"])
                value = float(raw)
                if not math.isfinite(value):
                    raise ValueError(f"nonfinite RTI for OCC2010 {occ}")
                if occ in rti:
                    relation = "conflicting" if rti[occ] != value else "duplicate"
                    raise ValueError(f"{relation} mapping key for OCC2010 {occ}")
                rti[occ] = value

    occ_weight = defaultdict(float)
    occ_count = defaultdict(int)
    total_weight = defaultdict(float)
    total_count = defaultdict(int)
    asec_rows = defaultdict(int)
    observed_years = set()
    asecflag_weight_crosscheck = {
        "positive_ASECWT_rows": 0,
        "positive_ASECWT_and_ASECFLAG_1_rows": 0,
        "ASECFLAG_1_rows": 0,
    }
    with open_text(args.cps) as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = REQUIRED_CPS - fields
        if missing:
            raise ValueError(f"CPS input missing required fields: {sorted(missing)}")
        for row in reader:
            year = int(row["YEAR"])
            observed_years.add(year)
            raw_weight = row["ASECWT"].strip()
            raw_flag = row["ASECFLAG"].strip()
            if raw_flag in {"1", "1.0"}:
                asecflag_weight_crosscheck["ASECFLAG_1_rows"] += 1
            if not raw_weight:
                continue
            asec_rows[year] += 1
            parsed_weight = float(raw_weight)
            if not math.isfinite(parsed_weight):
                raise ValueError(f"nonfinite ASECWT in year {year}")
            if parsed_weight > 0:
                asecflag_weight_crosscheck["positive_ASECWT_rows"] += 1
                if raw_flag in {"1", "1.0"}:
                    asecflag_weight_crosscheck["positive_ASECWT_and_ASECFLAG_1_rows"] += 1
            if row["EMPSTAT"].strip() not in EMPLOYED_CODES:
                continue
            weight = parsed_weight
            if weight <= 0:
                continue
            occ = code(row["OCC2010"])
            total_weight[year] += weight
            total_count[year] += 1
            occ_weight[(year, occ)] += weight
            occ_count[(year, occ)] += 1

    if not (
        asecflag_weight_crosscheck["positive_ASECWT_rows"]
        == asecflag_weight_crosscheck["positive_ASECWT_and_ASECFLAG_1_rows"]
        == asecflag_weight_crosscheck["ASECFLAG_1_rows"]
    ):
        raise ValueError("positive ASECWT does not exactly identify ASECFLAG==1 rows")

    requested = set(early) | set(late)
    absent = sorted(requested - observed_years)
    if absent:
        raise ValueError(f"requested years absent from CPS input: {absent}")
    zero_denominator = sorted(year for year in requested if total_weight[year] <= 0)
    if zero_denominator:
        raise ValueError(f"requested years lack positive employed ASEC denominator: {zero_denominator}")

    early_values = []
    for (year, occ), weight in occ_weight.items():
        if year in early and occ in rti:
            early_values.append((rti[occ], weight))
    cuts = weighted_cutpoints(early_values)

    def summarize(years):
        out = {"person_rows": 0, "mapped_person_rows": 0,
               "weight": 0.0, "mapped_weight": 0.0,
               "rti_weighted_sum": 0.0,
               "q1_low_rti": 0.0, "q2": 0.0, "q3": 0.0,
               "q4_high_rti": 0.0}
        for year in years:
            out["person_rows"] += total_count[year]
            out["weight"] += total_weight[year]
            for (candidate_year, occ), weight in occ_weight.items():
                if candidate_year != year or occ not in rti:
                    continue
                score = rti[occ]
                out["mapped_person_rows"] += occ_count[(candidate_year, occ)]
                out["mapped_weight"] += weight
                out["rti_weighted_sum"] += weight * score
                out[group(score, cuts)] += weight
        return out

    rows = []
    for label, years in (("early_window", early), ("late_window", late)):
        result = summarize(years)
        denom, mapped = result["weight"], result["mapped_weight"]
        rows.append({
            "period": label,
            "years": ",".join(map(str, years)),
            "unweighted_employed_rows": result["person_rows"],
            "rti_mapped_person_rows": result["mapped_person_rows"],
            "rti_unmapped_person_rows": result["person_rows"] - result["mapped_person_rows"],
            "pooled_asec_weighted_person_years": denom,
            "annual_average_asec_weighted_employed_persons": denom / len(years),
            "rti_mapped_weight": mapped,
            "rti_unmapped_weight": denom - mapped,
            "rti_mapped_weight_share": mapped / denom if denom else None,
            "rti_weighted_mean_among_mapped": result["rti_weighted_sum"] / mapped if mapped else None,
            "q1_low_rti_share_all_employed": result["q1_low_rti"] / denom if denom else None,
            "q2_share_all_employed": result["q2"] / denom if denom else None,
            "q3_share_all_employed": result["q3"] / denom if denom else None,
            "q4_high_rti_share_all_employed": result["q4_high_rti"] / denom if denom else None,
            "unmapped_share_all_employed": 1 - mapped / denom if denom else None,
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "CPS_BENCHMARK.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    receipt = {
        "status": "complete_descriptive_benchmark",
        "input": {
            "cps_path": str(args.cps),
            "cps_sha256": sha256(args.cps),
            "mapping_path": str(args.mapping),
            "mapping_sha256": sha256(args.mapping),
            "mapping_receipt_path": str(args.mapping_receipt),
            "mapping_receipt_sha256": sha256(args.mapping_receipt),
        },
        "verified_schema": sorted(REQUIRED_CPS),
        "sample": {
            "annual_sample": "ASECWT nonmissing and positive",
            "employment": "EMPSTAT in {10,12}",
            "denominator": "ASEC-weighted employed persons, including occupations without a usable RTI score",
            "occupation": "harmonized IPUMS OCC2010",
            "early_years": list(early),
            "late_years": list(late),
            "asec_selection_crosscheck": asecflag_weight_crosscheck,
        },
        "mapping": {
            "measure": "rti_autor_dorn",
            "formula": "ln(task_routine)-ln(task_manual)-ln(task_abstract)",
            "source": "Autor-Dorn occ1990dd_task_alm",
            "crosswalk": "direct CPS OCC2010 to occ1990dd bridge",
            "scored_occ2010_codes_loaded": len(rti),
            "quartile_cutpoints_fixed_from_early_window_weighted_distribution": cuts,
            "quartile_tie_rule": "score equal to a cutpoint enters the lower quartile",
        },
        "observed_year_range": [min(observed_years), max(observed_years)],
        "asec_rows_by_year": {str(y): asec_rows[y] for y in sorted(asec_rows)},
        "outputs": {"csv": str(csv_path)},
        "limits": [
            "Descriptive occupation/task composition only; no causal effect.",
            "Static historical RTI scores describe occupations, not realized worker tasks.",
            "No workplace computer-use supplement field is present in this CPS schema.",
            "No earnings field is read or analyzed.",
        ],
    }
    receipt_path = args.output_dir / "CPS_BENCHMARK_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

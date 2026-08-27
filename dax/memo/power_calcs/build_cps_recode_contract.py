"""Build the extract-9 recode contract from IPUMS DDI and basic codebook only."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import xml.etree.ElementTree as ET


VARIABLES = ("AGE", "EMPSTAT", "OCC", "OCC2010", "CLASSWKR", "WTFINL", "WKSTAT")
ASEC_GAP_YEARS = tuple(range(2017, 2022))


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def compact_text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def variable(root: ET.Element, name: str) -> ET.Element:
    matches = [
        element
        for element in root.iter()
        if local_name(element) == "var" and element.attrib.get("name") == name
    ]
    if len(matches) != 1:
        raise ValueError(f"DDI must contain exactly one {name} variable; found {len(matches)}")
    return matches[0]


def categories(element: ET.Element) -> dict[int, str]:
    result: dict[int, str] = {}
    for category in element:
        if local_name(category) != "catgry":
            continue
        value = label = None
        for child in category:
            if local_name(child) == "catValu":
                value = compact_text(child)
            elif local_name(child) == "labl":
                label = compact_text(child)
        if value is None or label is None:
            raise ValueError("DDI category lacks value or label")
        result[int(value)] = label
    return result


def metadata(element: ET.Element) -> dict[str, object]:
    description = ""
    for child in element:
        if local_name(child) == "txt":
            description = compact_text(child)
            break
    return {
        "decimal_places": int(element.attrib.get("dcml", "0")),
        "interval": element.attrib.get("intrvl"),
        "description": description,
        "categories": {str(key): value for key, value in categories(element).items()},
    }


def build(ddi: pathlib.Path, codebook: pathlib.Path) -> dict[str, object]:
    root = ET.parse(ddi).getroot()
    source = codebook.read_text(encoding="utf-8")
    as_ec_years = sorted({
        int(value)
        for value in re.findall(r"IPUMS-CPS, ASEC (20\d{2})", source)
        if int(value) in ASEC_GAP_YEARS
    })
    if as_ec_years != list(ASEC_GAP_YEARS):
        raise ValueError(f"expected ASEC 2017-2021 labels; found {as_ec_years}")

    values = {name: metadata(variable(root, name)) for name in VARIABLES}
    empstat = {int(key): value for key, value in values["EMPSTAT"]["categories"].items()}
    classwkr = {int(key): value for key, value in values["CLASSWKR"]["categories"].items()}
    wkstat = {int(key): value for key, value in values["WKSTAT"]["categories"].items()}
    occ2010 = {int(key): value for key, value in values["OCC2010"]["categories"].items()}

    expected_employed = {10: "At work", 12: "Has job, not at work last week"}
    for code, label in expected_employed.items():
        if empstat.get(code) != label:
            raise ValueError(f"EMPSTAT {code} label changed: {empstat.get(code)!r}")
    if occ2010.get(9999) != "NIU":
        raise ValueError("OCC2010 must enumerate 9999 as NIU")
    if classwkr.get(99) != "Missing/Unknown" or classwkr.get(0) != "NIU":
        raise ValueError("CLASSWKR missing categories changed")
    if wkstat.get(99) != "NIU, blank, or not in labor force":
        raise ValueError("WKSTAT 99 label changed")

    valid_occ = sorted(code for code, label in occ2010.items() if label != "NIU")
    return {
        "record_version": "cps-extract9-recode-contract-v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sources": {
            "ddi": {"path": str(ddi), "sha256": sha256(ddi)},
            "basic_codebook": {"path": str(codebook), "sha256": sha256(codebook)},
            "microdata_read": False,
        },
        "age": {
            "extract_min": 16,
            "extract_max": 75,
            "primary_min": 22,
            "primary_max": 65,
            "young_codes": [22, 23, 24, 25],
            "comparison_min": 26,
            "comparison_max": 65,
            "missing_codes": [],
        },
        "employment": {
            "source_variable": "EMPSTAT",
            "employed_codes": [10, 12],
            "niu_codes": [0],
            "armed_forces_codes": [1],
            "unemployed_codes": [20, 21, 22],
            "not_in_labor_force_codes": [30, 31, 32, 33, 34, 35, 36],
            "categories": values["EMPSTAT"]["categories"],
        },
        "occupation": {
            "primary_variable": "OCC",
            "primary_lookup_key": ["lookup_role", "occ_code"],
            "target_occupation_by_year": {
                "2017-2019": "probabilistic expansion of raw Census-2010 OCC to Census-2018 using official conversion rates",
                "2020-plus": "raw OCC directly observed on Census-2018"
            },
            "exposure_lookup_role": "raw_occ_main_2020_plus",
            "occ_code_normalization": "integer OCC formatted as exactly four zero-padded digits",
            "raw_missing_codes": None,
            "raw_missing_note": "OCC is continuous and the extract-9 DDI enumerates no missing categories or invalid range.",
            "primary_coverage_rule": "retain only full dv_rating_beta routes; require at least 90 percent of positive-WTFINL employed age-22-65 weight after the official bridge",
            "occ2010_role": "sensitivity only; never the primary grouping or exposure join",
            "valid_occ2010_codes": valid_occ,
            "missing_occ2010_codes": [9999],
            "occ2010_valid_rule": "code must be enumerated by extract-9 DDI and its label must not be NIU",
            "harmonization_caveat": "OCC2010 uses modal/forced assignment across vintages and is not admissible for the primary design.",
        },
        "class_of_worker": {
            "source_variable": "CLASSWKR",
            "primary_sample_restriction": "none",
            "niu_codes": [0],
            "missing_unknown_codes": [99],
            "self_employed_codes": [10, 13, 14],
            "general_wage_salary_codes": [20],
            "private_wage_salary_codes": [21, 22, 23],
            "government_wage_salary_codes": [24, 25, 27, 28],
            "armed_forces_codes": [26],
            "unpaid_family_codes": [29],
            "sensitivity_rule": "private-wage/salary sensitivity uses 21,22,23; if general code 20 is observed among employed rows, fail closed and report it rather than guessing private/public.",
            "categories": values["CLASSWKR"]["categories"],
        },
        "work_status": {
            "source_variable": "WKSTAT",
            "full_time_schedule_codes": [10, 11, 12, 13, 14, 15],
            "part_time_codes": [20, 21, 22, 40, 41, 42],
            "unemployed_codes": [50, 60],
            "niu_missing_codes": [99],
            "categories": values["WKSTAT"]["categories"],
        },
        "weight": {
            "source_variable": "WTFINL",
            "valid_rule": "finite and strictly positive",
            "missing_codes": None,
            "missing_note": "The DDI declares a continuous numeric variable and enumerates no missing category or invalid range.",
            "ddi_decimal_places": values["WTFINL"]["decimal_places"],
            "csv_scaling_rule": "parse the delivered CSV numeric value directly; do not apply an additional implied-decimal rescaling",
            "earnings_prohibition": "EARNWT, not WTFINL, is required for EARNWEEK/HOURWAGE/PAIDHOUR/UNION analyses.",
        },
        "structural_gaps": {
            "omit_months": [f"{year}-03" for year in ASEC_GAP_YEARS],
            "reason": "extract-9 basic codebook labels these as ASEC samples and marks WTFINL unavailable; never substitute ASECWT",
            "corrective_request": "dax/memo/power_calcs/ipums_ai_telework_march_patch_v1.json",
        },
        "metadata": values,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ddi", type=pathlib.Path, required=True)
    parser.add_argument("--codebook", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = build(args.ddi, args.codebook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS_METADATA_ONLY",
        "valid_occ2010_codes": len(result["occupation"]["valid_occ2010_codes"]),
        "structural_gaps": result["structural_gaps"]["omit_months"],
        "microdata_read": result["sources"]["microdata_read"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

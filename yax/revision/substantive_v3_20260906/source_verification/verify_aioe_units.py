#!/usr/bin/env python3
"""Verify the vendored AIOE source scale without spreadsheet dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[4]
WORKBOOK = ROOT / "yax" / "measurement" / "AIOE_DataAppendix.xlsx"
MAPPING_RESULT = ROOT / "yax" / "analysis" / "audit" / "MAPPING_DECOMPOSITION_AUDIT.csv"
MAPPING_RUNNER = ROOT / "yax" / "analysis" / "run_frozen_v11.py"

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def workbook_column(path: Path, sheet_name: str, column: str) -> list[float]:
    ns = {"m": MAIN_NS, "r": REL_NS}
    with zipfile.ZipFile(path) as archive:
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        shared = [
            "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
            for item in shared_root.findall("m:si", ns)
        ]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship_map = {
            item.attrib["Id"]: item.attrib["Target"] for item in relationships
        }
        sheet = next(
            item
            for item in workbook.find("m:sheets", ns)
            if item.attrib["name"] == sheet_name
        )
        target = relationship_map[sheet.attrib[f"{{{REL_NS}}}id"]]
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        sheet_root = ET.fromstring(archive.read(target))

        values: list[float] = []
        for row in sheet_root.findall(".//m:sheetData/m:row", ns):
            cells: dict[str, str] = {}
            for cell in row.findall("m:c", ns):
                cell_column = "".join(character for character in cell.attrib["r"] if character.isalpha())
                value_node = cell.find("m:v", ns)
                if value_node is None:
                    continue
                value = value_node.text or ""
                if cell.attrib.get("t") == "s":
                    value = shared[int(value)]
                cells[cell_column] = value
            if cells.get("A") in (None, "SOC Code") or not cells.get(column):
                continue
            values.append(float(cells[column]))
    return values


def quantile_linear(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])


def verify() -> dict[str, object]:
    values = workbook_column(WORKBOOK, "Appendix A", "C")
    p25 = quantile_linear(values, 0.25)
    median = quantile_linear(values, 0.50)
    p75 = quantile_linear(values, 0.75)
    result = {
        "workbook_repo_path": str(WORKBOOK.relative_to(ROOT)),
        "workbook_sha256": sha256(WORKBOOK),
        "sheet": "Appendix A",
        "field": "AIOE",
        "source_occupation_count": len(values),
        "unweighted_mean": statistics.fmean(values),
        "unweighted_sample_sd": statistics.stdev(values),
        "minimum": min(values),
        "p25": p25,
        "median": median,
        "p75": p75,
        "source_iqr_raw_units": p75 - p25,
        "maximum": max(values),
        "mapping_result_repo_path": str(MAPPING_RESULT.relative_to(ROOT)),
        "mapping_result_sha256": sha256(MAPPING_RESULT),
        "mapping_runner_repo_path": str(MAPPING_RUNNER.relative_to(ROOT)),
        "mapping_runner_sha256": sha256(MAPPING_RUNNER),
        "historical_mapping_audit_unit": (
            "one full-window employment-stock-weighted standard deviation of repaired "
            "equal-administrative AIOE on the expanded 495-occupation AIOE-plus-Webb support"
        ),
        "raw_unit_interpretation": (
            "one unit of the standardized source-occupation AIOE index; not a probability, "
            "percentage, or employment-weighted standard deviation"
        ),
    }

    if len(values) != 774:
        raise AssertionError(f"expected 774 source occupations, found {len(values)}")
    if abs(float(result["unweighted_mean"])) > 1e-6:
        raise AssertionError("source AIOE mean is not approximately zero")
    if abs(float(result["unweighted_sample_sd"]) - 1.0) > 1e-6:
        raise AssertionError("source AIOE sample SD is not approximately one")

    runner = MAPPING_RUNNER.read_text(encoding="utf-8")
    required_runner_tokens = (
        "fixed_reference = weighted_scale(v_ref, w_ref)",
        "scale=\"per_sd\", ai_reference=fixed_reference",
        "(1, original, exact, \"original exposure, original support\")",
        "(2, original, repaired, \"repaired exposure, original support\")",
        "(3, expanded, repaired, \"repaired exposure, expanded support\")",
    )
    missing = [token for token in required_runner_tokens if token not in runner]
    if missing:
        raise AssertionError(f"historical mapping scale/decomposition contract changed: {missing}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = verify()
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

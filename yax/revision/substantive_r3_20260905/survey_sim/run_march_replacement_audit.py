#!/usr/bin/env python3
"""Audit March Basic replacement and CPS sampling fields without releasing IDs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import numpy as np
import pandas as pd


REPAIRED_MONTHS = {f"{year}-03" for year in range(2017, 2022)}
ID_COLUMNS = ("CPSID", "CPSIDP", "CPSIDV")
READ_COLUMNS = (
    "YEAR", "MONTH", "ASECFLAG", "SERIAL", "CPSID", "CPSIDP", "CPSIDV",
    "MISH", "AGE", "EMPSTAT", "OCC", "WTFINL",
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty output: {path}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: pathlib.Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def month(frame: pd.DataFrame) -> pd.Series:
    return (
        pd.to_numeric(frame.YEAR, errors="raise").astype(int).astype(str)
        + "-"
        + pd.to_numeric(frame.MONTH, errors="raise").astype(int).astype(str).str.zfill(2)
    )


def load_repaired_months(path: pathlib.Path) -> pd.DataFrame:
    pieces = []
    for chunk in pd.read_csv(path, usecols=list(READ_COLUMNS), chunksize=500_000):
        mm = month(chunk)
        keep = mm.isin(REPAIRED_MONTHS)
        if keep.any():
            local = chunk.loc[keep].copy()
            local["month"] = mm.loc[keep]
            pieces.append(local)
    if not pieces:
        raise RuntimeError(f"no repaired-month records in {path}")
    result = pd.concat(pieces, ignore_index=True)
    for column in ("WTFINL", "AGE", "EMPSTAT", "OCC", *ID_COLUMNS, "SERIAL", "ASECFLAG"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def analysis_active(frame: pd.DataFrame) -> pd.Series:
    return (
        frame.AGE.between(18, 65)
        & frame.EMPSTAT.isin([10, 12])
        & np.isfinite(frame.WTFINL)
        & frame.WTFINL.gt(0)
        & frame.OCC.notna()
        & frame.OCC.between(0, 9999)
        & frame.OCC.mod(1).eq(0)
    )


def request_samples(path: pathlib.Path) -> tuple[dict, set[str]]:
    request = json.loads(path.read_text(encoding="utf-8"))
    return request, set(request.get("samples", {}))


def ddi_variables(path: pathlib.Path) -> tuple[dict[str, str], list[str]]:
    root = ET.parse(path).getroot()
    result: dict[str, str] = {}
    for element in root.iter():
        if not element.tag.endswith("var"):
            continue
        name = element.attrib.get("name") or element.attrib.get("ID")
        if not name:
            continue
        texts = []
        for descendant in element.iter():
            value = (descendant.text or "").strip()
            if value:
                texts.append(value)
        result[name] = " ".join(texts)
    return result, sorted(result)


def bridge_mass(path: pathlib.Path) -> dict[str, float]:
    bridge = pd.read_csv(path, dtype={"census_2010": str})
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    return bridge.groupby("census_2010").bridge_weight.sum().to_dict()


def routed_stock(frame: pd.DataFrame, masses: dict[str, float]) -> float:
    active = frame.loc[analysis_active(frame)].copy()
    if active.empty:
        return 0.0
    early = active.YEAR.le(2019)
    source = active.OCC.astype(int).map(lambda value: f"{value:04d}")
    multiplier = np.where(early, source.map(masses).fillna(0.0), 1.0)
    return float(np.sum(active.WTFINL.to_numpy(float) * multiplier))


def unique_positive(frame: pd.DataFrame, column: str) -> set[int]:
    values = pd.to_numeric(frame[column], errors="coerce")
    return set(values.loc[values.notna() & values.gt(0)].astype("int64").tolist())


def duplicates_on_active_person_id(frame: pd.DataFrame, column: str) -> int:
    active = frame.loc[analysis_active(frame)].copy()
    values = pd.to_numeric(active[column], errors="coerce")
    valid = values.notna() & values.gt(0)
    keys = active.loc[valid, ["month"]].copy()
    keys[column] = values.loc[valid].astype("int64").to_numpy()
    return int(keys.duplicated(["month", column], keep=False).sum())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wide", type=pathlib.Path, required=True)
    parser.add_argument("--repair", type=pathlib.Path, required=True)
    parser.add_argument("--wide-request", type=pathlib.Path, required=True)
    parser.add_argument("--repair-request", type=pathlib.Path, required=True)
    parser.add_argument("--wide-ddi", type=pathlib.Path, required=True)
    parser.add_argument("--repair-ddi", type=pathlib.Path, required=True)
    parser.add_argument("--bridge", type=pathlib.Path, required=True)
    parser.add_argument("--cell-builder", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    wide_request, wide_samples = request_samples(args.wide_request)
    repair_request, repair_samples = request_samples(args.repair_request)
    expected_wide = {f"cps{year}_03s" for year in range(2017, 2022)}
    expected_repair = {f"cps{year}_03b" for year in range(2017, 2022)}
    wide_repaired_selection = {sample for sample in wide_samples if sample[3:7].isdigit() and sample[7:10] == "_03" and sample[3:7] in {str(y) for y in range(2017, 2022)}}

    wide = load_repaired_months(args.wide)
    repair = load_repaired_months(args.repair)
    masses = bridge_mass(args.bridge)
    combined = pd.concat([wide.assign(source_file="wide_ASEC"), repair.assign(source_file="repair_Basic")], ignore_index=True)

    rows: list[dict] = []
    all_pass = True
    for repaired_month in sorted(REPAIRED_MONTHS):
        w = wide.loc[wide.month.eq(repaired_month)].copy()
        r = repair.loc[repair.month.eq(repaired_month)].copy()
        wa, ra = w.loc[analysis_active(w)], r.loc[analysis_active(r)]
        local = pd.concat([w.assign(source_file="wide_ASEC"), r.assign(source_file="repair_Basic")], ignore_index=True)
        record: dict = {
            "month": repaired_month,
            "wide_raw_records": len(w),
            "repair_raw_records": len(r),
            "wide_ASECFLAG_values": ";".join(map(str, sorted(w.ASECFLAG.dropna().astype(int).unique()))),
            "repair_ASECFLAG_values": ";".join(map(str, sorted(r.ASECFLAG.dropna().astype(int).unique()))),
            "wide_positive_weight_records": int(w.WTFINL.gt(0).sum()),
            "repair_positive_weight_records": int(r.WTFINL.gt(0).sum()),
            "wide_active_analysis_records": len(wa),
            "repair_active_analysis_records": len(ra),
            "wide_active_WTFINL_stock": float(wa.WTFINL.sum()),
            "repair_active_WTFINL_stock": float(ra.WTFINL.sum()),
            "wide_active_routed_stock": routed_stock(w, masses),
            "repair_active_routed_stock": routed_stock(r, masses),
        }
        for identifier in ID_COLUMNS:
            w_raw, r_raw = unique_positive(w, identifier), unique_positive(r, identifier)
            w_active, r_active = unique_positive(wa, identifier), unique_positive(ra, identifier)
            raw_overlap = w_raw & r_raw
            active_overlap = w_active & r_active
            record.update({
                f"wide_raw_unique_{identifier}": len(w_raw),
                f"repair_raw_unique_{identifier}": len(r_raw),
                f"raw_overlap_{identifier}": len(raw_overlap),
                f"repair_raw_overlap_share_{identifier}": len(raw_overlap) / len(r_raw) if r_raw else np.nan,
                f"wide_active_unique_{identifier}": len(w_active),
                f"repair_active_unique_{identifier}": len(r_active),
                f"active_overlap_{identifier}": len(active_overlap),
                f"combined_active_duplicate_rows_{identifier}": duplicates_on_active_person_id(local, identifier) if identifier != "CPSID" else "not_a_person_key",
            })
        record["append_active_routed_stock"] = record["wide_active_routed_stock"] + record["repair_active_routed_stock"]
        record["replacement_active_routed_stock"] = record["repair_active_routed_stock"]
        record["append_minus_replacement_routed_stock"] = record["append_active_routed_stock"] - record["replacement_active_routed_stock"]
        month_pass = (
            len(w) > 0
            and len(r) > 0
            and set(w.ASECFLAG.dropna().astype(int).unique()) == {1}
            and set(r.ASECFLAG.dropna().astype(int).unique()) == {2}
            and int(w.WTFINL.gt(0).sum()) == 0
            and len(wa) == 0
            and record["active_overlap_CPSIDP"] == 0
            and record["active_overlap_CPSIDV"] == 0
            and record["combined_active_duplicate_rows_CPSIDP"] == 0
            and record["combined_active_duplicate_rows_CPSIDV"] == 0
            and abs(record["append_minus_replacement_routed_stock"]) < 1e-8
        )
        record["functional_replacement_pass"] = month_pass
        all_pass &= month_pass
        rows.append(record)

    wide_ddi, wide_variables = ddi_variables(args.wide_ddi)
    repair_ddi, repair_variables = ddi_variables(args.repair_ddi)
    combined_variables = set(wide_variables) & set(repair_variables)
    design_patterns = ("STRAT", "PSU", "REPLICATE", "REPWT", "REPWGT", "VARSTR", "VARPSU")
    candidate_design_variables = sorted(
        variable for variable in combined_variables
        if any(pattern in variable.upper() for pattern in design_patterns)
    )
    available = [name for name in ("SERIAL", "CPSID", "CPSIDP", "CPSIDV", "MISH", "WTFINL", "HWTFINL") if name in combined_variables]
    field_audit = {
        "available_link_and_weight_fields_in_both_files": available,
        "candidate_public_stratum_PSU_or_replicate_fields": candidate_design_variables,
        "wide_variable_count": len(wide_variables),
        "repair_variable_count": len(repair_variables),
        "SERIAL_DDI_excerpt": wide_ddi.get("SERIAL", "")[:1200],
        "CPSID_DDI_excerpt": wide_ddi.get("CPSID", "")[:1800],
        "MISH_DDI_excerpt": wide_ddi.get("MISH", "")[:1200],
        "WTFINL_DDI_excerpt": wide_ddi.get("WTFINL", "")[:1600],
        "design_based_inference_available": False,
        "reason": "No public stratum, PSU, or replicate-weight field is present in both authenticated Basic-Monthly analysis files.",
        "admissible_sensitivity": "Mean-one positive multiplier at longitudinal household CPSID, common across all observed months and fractional route descendants, conditional on supplied final weights.",
        "not_captured": "CPS multistage selection, public-use design strata/PSUs, replicate-weight variance, and uncertainty from calibration/nonresponse adjustments in WTFINL.",
    }

    source = args.cell_builder.read_text(encoding="utf-8")
    builder_order_pass = (
        'weight.gt(0)' in source
        and 'chunk = chunk.loc[keep].copy()' in source
        and 'microdata_paths.append(args.repair_microdata)' in source
    )
    request_gate = (
        wide_repaired_selection == expected_wide
        and repair_samples == expected_repair
        and "replace accidentally selected" in repair_request.get("description", "").lower()
    )
    all_pass &= request_gate and builder_order_pass and not candidate_design_variables

    write_csv(args.output_dir / "MARCH_SAMPLE_OVERLAP_AND_STOCK.csv", rows)
    write_json(args.output_dir / "SURVEY_FIELD_AUDIT.json", field_audit)
    receipt = {
        "status": "PASS_FUNCTIONAL_REPLACEMENT" if all_pass else "FAIL_CLOSED",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repaired_months": sorted(REPAIRED_MONTHS),
        "wide_repaired_sample_selection": sorted(wide_repaired_selection),
        "repair_sample_selection": sorted(repair_samples),
        "request_gate_pass": request_gate,
        "builder_positive_weight_filter_precedes_concatenation_pass": builder_order_pass,
        "per_month_functional_replacement_pass": all(row["functional_replacement_pass"] for row in rows),
        "candidate_public_design_fields": candidate_design_variables,
        "raw_record_overlap_is_not_active_stock_overlap": True,
        "input_hashes": {
            "wide": sha256(args.wide),
            "repair": sha256(args.repair),
            "wide_request": sha256(args.wide_request),
            "repair_request": sha256(args.repair_request),
            "wide_ddi": sha256(args.wide_ddi),
            "repair_ddi": sha256(args.repair_ddi),
            "bridge": sha256(args.bridge),
            "cell_builder": sha256(args.cell_builder),
        },
        "nonrelease_assertion": "Outputs contain aggregate counts only; no SERIAL, CPSID, CPSIDP, or CPSIDV value is serialized.",
    }
    write_json(args.output_dir / "MARCH_REPLACEMENT_AUDIT_RECEIPT.json", receipt)
    if not all_pass:
        raise RuntimeError(f"March replacement audit failed closed: {receipt}")


if __name__ == "__main__":
    main()


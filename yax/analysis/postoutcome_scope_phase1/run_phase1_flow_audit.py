#!/usr/bin/env python3
"""Audit CPS longitudinal-flow feasibility without treatment-effect regressions.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
from datetime import datetime, timezone

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
ROOT = pathlib.Path(__file__).resolve().parents[3]
INVENTORY_VARIABLES = (
    "YEAR", "MONTH", "SERIAL", "CPSID", "PERNUM", "CPSIDP", "CPSIDV",
    "MISH", "AGE", "EMPSTAT", "OCC", "OCC2010", "IND1990", "CLASSWKR",
    "WTFINL", "EARNWT", "EDUC", "SEX", "RACE", "HISPAN", "ASECFLAG",
)
LOAD_COLUMNS = INVENTORY_VARIABLES
MEANINGS = {
    "YEAR": "Calendar year of interview",
    "MONTH": "Calendar month of interview",
    "SERIAL": "Household serial unique only within year-month sample",
    "CPSID": "IPUMS longitudinal household identifier for the 4-8-4 rotation",
    "PERNUM": "Person number within household/sample",
    "CPSIDP": "IPUMS person longitudinal identifier based on roster line",
    "CPSIDV": "IPUMS validated person longitudinal identifier; preferred link key",
    "MISH": "Month in sample, 1 through 8",
    "AGE": "Age at last birthday at interview",
    "EMPSTAT": "Employment status; 10/12 employed, 20s unemployed, 30s NILF",
    "OCC": "Sample-specific Census occupation code; current occupation only when employed",
    "OCC2010": "IPUMS harmonized Census-2010 occupation code",
    "IND1990": "IPUMS harmonized 1990 industry code",
    "CLASSWKR": "Class of worker; not an employer identity",
    "WTFINL": "Final basic monthly cross-sectional person weight",
    "EARNWT": "Outgoing-rotation earnings weight; not a longitudinal link weight",
    "EDUC": "Educational attainment",
    "SEX": "Reported sex; used only for link-selection diagnostics",
    "RACE": "Reported race; used only for ID validation/selection diagnostics",
    "HISPAN": "Hispanic-origin coding",
    "ASECFLAG": "Marks ASEC supplement records; positive-WTFINL basic records are audited",
}
RELEVANCE = {
    "YEAR": "transition timing", "MONTH": "transition timing", "SERIAL": "household checks",
    "CPSID": "household links", "PERNUM": "within-sample person key",
    "CPSIDP": "alternative person links", "CPSIDV": "preferred person links",
    "MISH": "rotation eligibility", "AGE": "origin-age rule", "EMPSTAT": "E/N states",
    "OCC": "primary occupation transition", "OCC2010": "coding-noise sensitivity",
    "IND1990": "inventory/selection", "CLASSWKR": "worker-class diagnostic",
    "WTFINL": "origin/destination count sensitivity", "EARNWT": "weight audit",
    "EDUC": "attrition selection", "SEX": "attrition selection",
    "RACE": "attrition selection", "HISPAN": "attrition selection",
    "ASECFLAG": "basic-versus-supplement record separation",
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def age_bin(values: pd.Series) -> pd.Series:
    return pd.cut(
        values,
        [17, 21, 25, 30, 40, 50, 65, np.inf],
        labels=["18-21", "22-25", "26-30", "31-40", "41-50", "51-65", "66+"],
    ).astype("string")


def load_extract(path: pathlib.Path) -> tuple[pd.DataFrame, list[dict], dict]:
    header = pd.read_csv(path, nrows=0).columns.tolist()
    absent = [name for name in INVENTORY_VARIABLES if name not in header]
    if absent:
        raise RuntimeError(f"expected inventory variables absent from actual header: {absent}")
    missing = {name: 0 for name in INVENTORY_VARIABLES}
    total_rows = 0
    pieces = []
    for chunk in pd.read_csv(path, usecols=list(LOAD_COLUMNS), chunksize=500_000):
        total_rows += len(chunk)
        for name in INVENTORY_VARIABLES:
            missing[name] += int(chunk[name].isna().sum())
        # ASEC supplement records have no basic WTFINL. Retain actual basic records only.
        basic = chunk.loc[chunk.ASECFLAG.ne(1) & pd.to_numeric(chunk.WTFINL, errors="coerce").gt(0)].copy()
        pieces.append(basic.drop(columns=["ASECFLAG"]))
    frame = pd.concat(pieces, ignore_index=True)
    del pieces
    integer_types = {
        "YEAR": "int16", "MONTH": "int8", "SERIAL": "int32", "PERNUM": "int8",
        "MISH": "int8", "AGE": "int16", "EMPSTAT": "int8", "OCC": "int16",
        "OCC2010": "int16", "IND1990": "int16", "CLASSWKR": "int16",
        "EDUC": "int16", "SEX": "int8", "RACE": "int16", "HISPAN": "int16",
    }
    for column, dtype in integer_types.items():
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype(dtype)
    for column in ("CPSID", "CPSIDP", "CPSIDV"):
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("int64")
    frame["WTFINL"] = pd.to_numeric(frame.WTFINL, errors="raise").astype("float64")
    frame["EARNWT"] = pd.to_numeric(frame.EARNWT, errors="coerce").astype("float64")
    frame["month_ord"] = (frame.YEAR.astype("int32") * 12 + frame.MONTH.astype("int32")).astype("int32")
    frame["month"] = frame.YEAR.astype(str) + "-" + frame.MONTH.astype(str).str.zfill(2)
    frame["employed"] = frame.EMPSTAT.isin([10, 12])
    frame["nonemployed"] = frame.EMPSTAT.between(20, 36)
    frame["age_bin"] = age_bin(frame.AGE)
    inventory = [
        {
            "analysis_status": LABEL,
            "Variable": name,
            "Available?": "yes",
            "Meaning": MEANINGS[name],
            "Missing rate": missing[name] / total_rows,
            "Relevant for": RELEVANCE[name],
        }
        for name in INVENTORY_VARIABLES
    ]
    inventory.extend(
        [
            {
                "analysis_status": LABEL,
                "Variable": "official longitudinal linking weight",
                "Available?": "no",
                "Meaning": "No such variable appears in the actual extract header",
                "Missing rate": 1.0,
                "Relevant for": "longitudinal attrition adjustment",
            },
            {
                "analysis_status": LABEL,
                "Variable": "same-employer identifier",
                "Available?": "no",
                "Meaning": "No employer identity or same-employer field appears in the extract",
                "Missing rate": 1.0,
                "Relevant for": "occupation-switch coding-noise audit",
            },
        ]
    )
    receipt = {
        "full_extract_rows": total_rows,
        "positive_WTFINL_basic_rows": len(frame),
        "actual_header": header,
        "duplicate_CPSIDV_within_month": int(frame.duplicated(["YEAR", "MONTH", "CPSIDV"]).sum()),
        "CPSIDV_zero_count": int(frame.CPSIDV.eq(0).sum()),
    }
    return frame, inventory, receipt


def mapping_inputs(args: argparse.Namespace) -> tuple[dict, dict, dict]:
    bridge = pd.read_csv(args.bridge, dtype={"census_2010": str, "census_2018": str})
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    dominant = (
        bridge.sort_values(
            ["census_2010", "bridge_weight", "census_2018"],
            ascending=[True, False, True],
            kind="mergesort",
        )
        .drop_duplicates("census_2010")
        .set_index("census_2010")["census_2018"]
        .to_dict()
    )
    membership = pd.read_csv(args.membership, dtype={"occ_code": str})
    membership["occ_code"] = membership.occ_code.str.zfill(4)
    quintile = membership.set_index("occ_code").preperiod_quintile.astype(int).to_dict()
    comp = pd.read_csv(args.computerization, dtype={"census2018": str})
    comp["census2018"] = comp.census2018.str.zfill(4)
    major = comp.set_index("census2018").soc_major_group.astype(str).to_dict()
    return dominant, quintile, major


def add_occupation_fields(frame: pd.DataFrame, dominant: dict, quintile: dict, major: dict) -> None:
    source = frame.OCC.astype(int).map(lambda value: f"{value:04d}")
    early = frame.YEAR.le(2019)
    mapped = source.copy()
    mapped.loc[early] = source.loc[early].map(dominant)
    mapped = mapped.where(frame.employed)
    frame["occ2018_modal"] = mapped.astype("string")
    frame["beta_quintile"] = frame.occ2018_modal.map(quintile).astype("float32")
    frame["soc_major_group"] = frame.occ2018_modal.map(major).astype("string")


def build_pairs(frame: pd.DataFrame, gap: int, allowed_mish: set[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    observed_months = set(frame.month_ord.unique())
    origin = frame.loc[
        frame.AGE.between(18, 65)
        & frame.EMPSTAT.between(10, 36)
        & frame.MISH.isin(allowed_mish)
    ].copy()
    origin["target_ord"] = origin.month_ord + gap
    origin = origin.loc[origin.target_ord.isin(observed_months)].copy()
    keep_dest = [
        "CPSIDV", "month_ord", "MISH", "AGE", "EMPSTAT", "OCC", "OCC2010",
        "WTFINL", "occ2018_modal", "beta_quintile", "soc_major_group",
    ]
    destination = frame[keep_dest].rename(columns={name: f"{name}_d" for name in keep_dest if name != "CPSIDV"})
    pairs = origin.merge(
        destination,
        left_on=["CPSIDV", "target_ord"],
        right_on=["CPSIDV", "month_ord_d"],
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    pairs["matched_id"] = pairs._merge.eq("both")
    pairs["matched"] = pairs.matched_id & pairs.MISH_d.eq(pairs.MISH + 1)
    return origin, pairs.drop(columns="_merge")


def match_summary_rows(pairs: pd.DataFrame, structure: str) -> list[dict]:
    rows: list[dict] = []

    def add(dimension: str, level: str, mask: pd.Series, notes: str = "") -> None:
        selected = pairs.loc[mask]
        eligible = len(selected)
        matched = int(selected.matched.sum())
        rows.append(
            {
                "analysis_status": LABEL,
                "link_structure": structure,
                "dimension": dimension,
                "level": level,
                "eligible_raw": eligible,
                "matched_raw": matched,
                "match_rate": matched / eligible if eligible else "",
                "eligible_weighted_origin": float(selected.WTFINL.sum()),
                "matched_weighted_origin": float(selected.loc[selected.matched, "WTFINL"].sum()),
                "valid_CPSIDV_rate": float(selected.CPSIDV.ne(0).mean()) if eligible else "",
                "notes": notes,
            }
        )

    all_mask = pd.Series(True, index=pairs.index)
    add("overall", "all eligible origins", all_mask)
    for year in sorted(pairs.YEAR.unique()):
        add("calendar_year", str(year), pairs.YEAR.eq(year))
    add("period", "pre-2023", pairs.month.lt("2023-01"))
    add("period", "post-2023", pairs.month.ge("2023-01"))
    add("age", "22-25", pairs.AGE.between(22, 25))
    add("age", "26-65", pairs.AGE.between(26, 65))
    for mish in sorted(pairs.MISH.unique()):
        add("MISH_transition", f"{mish}->{mish + 1}", pairs.MISH.eq(mish))
    add("origin_employment", "employed", pairs.employed)
    add("origin_employment", "nonemployed", pairs.nonemployed)
    for q in range(1, 6):
        add(
            "origin_beta_quintile",
            f"Q{q}",
            pairs.employed & pairs.beta_quintile.eq(q),
            "Defined only for employed origins with modal Census-2018 mapping on primary support",
        )
    return rows


def flow_masks(pairs: pd.DataFrame) -> dict[str, pd.Series]:
    matched = pairs.matched
    emp_o = pairs.employed
    non_o = pairs.nonemployed
    emp_d = pairs.EMPSTAT_d.isin([10, 12])
    non_d = pairs.EMPSTAT_d.between(20, 36)
    valid_o = pairs.occ2018_modal.notna()
    valid_d = pairs.occ2018_modal_d.notna()
    changed = valid_o & valid_d & pairs.occ2018_modal.ne(pairs.occ2018_modal_d)
    return {
        "employment_exit": matched & emp_o & non_d,
        "occupational_switch_out": matched & emp_o & emp_d & changed,
        "entry_from_nonemployment": matched & non_o & emp_d,
        "switch_into_occupation": matched & emp_o & emp_d & changed,
    }


def flow_feasibility_rows(pairs: pd.DataFrame) -> list[dict]:
    masks = flow_masks(pairs)
    rows: list[dict] = []
    risk = {
        "employment_exit": pairs.matched & pairs.employed,
        "occupational_switch_out": pairs.matched & pairs.employed & pairs.EMPSTAT_d.isin([10, 12]),
        "entry_from_nonemployment": pairs.matched & pairs.nonemployed,
        "switch_into_occupation": pairs.matched & pairs.employed & pairs.EMPSTAT_d.isin([10, 12]),
    }

    def add(margin: str, dimension: str, level: str, subgroup: pd.Series, exposure_basis: str) -> None:
        event_mask = masks[margin] & subgroup
        risk_mask = risk[margin] & subgroup
        weight_col = "WTFINL_d" if margin == "entry_from_nonemployment" else "WTFINL"
        occ_col = "occ2018_modal_d" if margin in ("entry_from_nonemployment", "switch_into_occupation") else "occ2018_modal"
        q_col = "beta_quintile_d" if margin in ("entry_from_nonemployment", "switch_into_occupation") else "beta_quintile"
        covered_events = event_mask & pairs[q_col].notna()
        coverage = int(pairs.loc[covered_events, occ_col].nunique())
        rows.append(
            {
                "analysis_status": LABEL,
                "margin": margin,
                "subgroup_dimension": dimension,
                "subgroup_level": level,
                "linked_risk_set_raw": int(risk_mask.sum()),
                "flow_events_raw": int(event_mask.sum()),
                "linked_risk_set_weighted": float(pairs.loc[risk_mask, weight_col].sum()),
                "flow_events_weighted": float(pairs.loc[event_mask, weight_col].sum()),
                "occupation_coverage_count": coverage,
                "occupation_coverage_share_of_468": coverage / 468,
                "exposure_basis": exposure_basis,
            }
        )

    universal = pd.Series(True, index=pairs.index)
    for margin in masks:
        basis = "destination" if margin in ("entry_from_nonemployment", "switch_into_occupation") else "origin"
        add(margin, "overall", "all matched adjacent transitions", universal, basis)
        add(margin, "age_at_origin", "22-25", pairs.AGE.between(22, 25), basis)
        add(margin, "period", "pre", pairs.month.lt("2022-12"), basis)
        add(margin, "period", "post", pairs.month.ge("2023-01"), basis)
        q_series = pairs.beta_quintile_d if basis == "destination" else pairs.beta_quintile
        for q in (1, 5):
            add(margin, "beta_quintile", f"Q{q}", q_series.eq(q), basis)
    return rows


def switching_audit(pairs: pd.DataFrame) -> dict:
    ee = pairs.loc[
        pairs.matched & pairs.employed & pairs.EMPSTAT_d.isin([10, 12])
    ].copy()
    valid_raw = ee.OCC.gt(0) & ee.OCC_d.gt(0)
    valid_2010 = ee.OCC2010.gt(0) & ee.OCC2010_d.gt(0)
    valid_h = ee.occ2018_modal.notna() & ee.occ2018_modal_d.notna()
    ee["raw_change"] = valid_raw & ee.OCC.ne(ee.OCC_d)
    ee["occ2010_change"] = valid_2010 & ee.OCC2010.ne(ee.OCC2010_d)
    ee["harmonized_change"] = valid_h & ee.occ2018_modal.ne(ee.occ2018_modal_d)
    h_switch = ee.harmonized_change
    same_major = ee.soc_major_group.notna() & ee.soc_major_group_d.notna() & ee.soc_major_group.eq(ee.soc_major_group_d)

    first = ee.loc[valid_h, ["CPSIDV", "month_ord", "occ2018_modal", "occ2018_modal_d", "harmonized_change"]].copy()
    second = first.rename(
        columns={
            "month_ord": "month_ord_2", "occ2018_modal": "occ2018_modal_2",
            "occ2018_modal_d": "occ2018_modal_3", "harmonized_change": "second_change",
        }
    )
    # Re-key the second adjacent link at t+1.
    second["origin_match_ord"] = second.month_ord_2 - 1
    triple = first.merge(
        second,
        left_on=["CPSIDV", "month_ord"],
        right_on=["CPSIDV", "origin_match_ord"],
        how="inner",
    )
    first_switch = triple.harmonized_change
    reversals = first_switch & triple.occ2018_modal.eq(triple.occ2018_modal_3)

    boundary = ee.month.eq("2019-12") & ee.month_ord_d.eq(2020 * 12 + 1)
    nonboundary = ~boundary
    return {
        "employed_to_employed_matched": int(len(ee)),
        "raw_valid_pairs": int(valid_raw.sum()),
        "raw_adjacent_occupation_change_rate": float(ee.loc[valid_raw, "raw_change"].mean()),
        "occ2010_valid_pairs": int(valid_2010.sum()),
        "occ2010_change_rate": float(ee.loc[valid_2010, "occ2010_change"].mean()),
        "modal_harmonized_valid_pairs": int(valid_h.sum()),
        "modal_harmonized_change_rate": float(ee.loc[valid_h, "harmonized_change"].mean()),
        "harmonized_switches": int(h_switch.sum()),
        "switches_with_same_SOC_major_group_share": float(same_major.loc[h_switch].mean()),
        "three_month_first_switches_observable": int(first_switch.sum()),
        "immediate_A_B_A_reversals": int(reversals.sum()),
        "immediate_reversal_share_of_observable_first_switches": float(reversals.sum() / first_switch.sum()),
        "same_employer_identifier_available": False,
        "boundary_2019_12_to_2020_01_pairs": int(boundary.sum()),
        "raw_change_rate_at_taxonomy_boundary": float(ee.loc[boundary & valid_raw, "raw_change"].mean()),
        "occ2010_change_rate_at_taxonomy_boundary": float(ee.loc[boundary & valid_2010, "occ2010_change"].mean()),
        "modal_harmonized_change_rate_at_taxonomy_boundary": float(ee.loc[boundary & valid_h, "harmonized_change"].mean()),
        "modal_harmonized_change_rate_other_months": float(ee.loc[nonboundary & valid_h, "harmonized_change"].mean()),
    }


def attrition_rows(pairs: pd.DataFrame) -> list[dict]:
    rows = []
    dimensions = {
        "age_group": pairs.age_bin,
        "employment": np.where(pairs.employed, "employed", "nonemployed"),
        "beta_quintile": pairs.beta_quintile.map(lambda value: f"Q{int(value)}" if pd.notna(value) else "unmapped/not-employed"),
        "education_code": pairs.EDUC.astype(str),
        "sex_code": pairs.SEX.astype(str),
        "broad_occupation": pairs.soc_major_group.fillna("unmapped/not-employed"),
        "period": np.where(pairs.month.ge("2023-01"), "post-2023", "pre-2023"),
    }
    for dimension, values in dimensions.items():
        temp = pd.DataFrame({"level": values, "matched": pairs.matched, "weight": pairs.WTFINL})
        grouped = temp.groupby("level", dropna=False)
        for level, group in grouped:
            rows.append(
                {
                    "analysis_status": LABEL,
                    "link_structure": "adjacent-month",
                    "dimension": f"attrition_{dimension}",
                    "level": str(level),
                    "eligible_raw": len(group),
                    "matched_raw": int(group.matched.sum()),
                    "match_rate": float(group.matched.mean()),
                    "eligible_weighted_origin": float(group.weight.sum()),
                    "matched_weighted_origin": float(group.loc[group.matched, "weight"].sum()),
                    "valid_CPSIDV_rate": 1.0,
                    "notes": "Observable linked-versus-unlinked selection diagnostic only",
                }
            )
    return rows


def run(args: argparse.Namespace) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame, inventory, extract_receipt = load_extract(args.microdata)
    dominant, quintile, major = mapping_inputs(args)
    add_occupation_fields(frame, dominant, quintile, major)
    inventory_path = args.output_dir / "CPS_LONGITUDINAL_VARIABLE_INVENTORY.csv"
    write_csv(inventory_path, inventory)

    _, adjacent = build_pairs(frame, gap=1, allowed_mish={1, 2, 3, 5, 6, 7})
    _, long_gap = build_pairs(frame, gap=9, allowed_mish={4})
    match_rows = match_summary_rows(adjacent, "adjacent-month")
    match_rows.extend(match_summary_rows(long_gap, "MISH 4-to-5 return after 8 absent months"))
    match_rows.extend(attrition_rows(adjacent))

    matched_adjacent = adjacent.loc[adjacent.matched].copy()
    matched_adjacent["origin_age_bin"] = age_bin(matched_adjacent.AGE)
    matched_adjacent["destination_age_bin"] = age_bin(matched_adjacent.AGE_d)
    boundary_valid = matched_adjacent.origin_age_bin.notna() & matched_adjacent.destination_age_bin.notna()
    age_cross = boundary_valid & matched_adjacent.origin_age_bin.ne(matched_adjacent.destination_age_bin)
    match_rows.append(
        {
            "analysis_status": LABEL,
            "link_structure": "adjacent-month",
            "dimension": "age_boundary",
            "level": "crosses one of the fixed six age-bin boundaries",
            "eligible_raw": int(boundary_valid.sum()),
            "matched_raw": int(age_cross.sum()),
            "match_rate": float(age_cross.sum() / boundary_valid.sum()),
            "eligible_weighted_origin": float(matched_adjacent.loc[boundary_valid, "WTFINL"].sum()),
            "matched_weighted_origin": float(matched_adjacent.loc[age_cross, "WTFINL"].sum()),
            "valid_CPSIDV_rate": 1.0,
            "notes": "Confirms future age classification should use age at origin interview",
        }
    )
    match_path = args.output_dir / "CPS_LONGITUDINAL_MATCH_RATES.csv"
    write_csv(match_path, match_rows)

    flow_rows = flow_feasibility_rows(adjacent)
    flow_path = args.output_dir / "CPS_FLOW_SAMPLE_FEASIBILITY.csv"
    write_csv(flow_path, flow_rows)
    switching = switching_audit(adjacent)

    noise_path = args.output_dir / "CPS_OCCUPATION_SWITCHING_NOISE_AUDIT.md"
    noise_path.write_text(
        f"""# CPS occupation-switching noise audit

> **{LABEL}**

No treatment-effect regression was run. The preferred feasibility structure is
the adjacent-month `CPSIDV` link. A switch requires employment at both
interviews and different nonmissing modal-harmonized Census-2018 occupation
codes.

| diagnostic | result |
|---|---:|
| matched employed-to-employed pairs | {switching['employed_to_employed_matched']:,} |
| raw OCC change rate | {switching['raw_adjacent_occupation_change_rate']:.3%} |
| harmonized OCC2010 change rate | {switching['occ2010_change_rate']:.3%} |
| modal Census-2018 change rate | {switching['modal_harmonized_change_rate']:.3%} |
| modal switches within same SOC major group | {switching['switches_with_same_SOC_major_group_share']:.3%} |
| immediate A→B→A reversal share | {switching['immediate_reversal_share_of_observable_first_switches']:.3%} |
| 2019-12→2020-01 modal-harmonized change rate | {switching['modal_harmonized_change_rate_at_taxonomy_boundary']:.3%} |
| other-month modal-harmonized change rate | {switching['modal_harmonized_change_rate_other_months']:.3%} |

The extract contains no same-employer identifier, so the requested
same-employer switch rate cannot be computed. `CLASSWKR` identifies class of
worker, not employer continuity, and is not substituted.

For pre-2020 records, the feasibility-only modal Census bridge selects the
highest-weight 2010→2018 route (stable code-order tie break). This is not the
probabilistic stock routing used by the main YAX estimator and is not approved
for a future treatment regression. The raw-code and OCC2010 comparisons, the
immediate-reversal rate, within-major-group share, and the 2019/2020 boundary
diagnostic jointly show how much apparent switching may be coding noise. No
correction is imposed in Phase 1.
""",
        encoding="utf-8",
    )

    weight_path = args.output_dir / "CPS_LONGITUDINAL_WEIGHT_AUDIT.md"
    weight_path.write_text(
        f"""# CPS longitudinal weight audit

> **{LABEL}**

The actual extract contains no official longitudinal linking weight for the
intended adjacent-month design.

- `WTFINL` is the final basic-month cross-sectional person weight. It targets a
  monthly population and does not by itself correct selection into successful
  longitudinal linkage.
- `EARNWT` is the outgoing-rotation earnings weight. It is limited to earner
  variables and is not a generic panel/link weight.
- Household/person identifiers and `MISH` establish links but are not weights.

Phase-1 weighted counts use the origin `WTFINL` for incumbent-origin margins
and destination `WTFINL` for entry counts, alongside raw counts. These are
sample-size diagnostics only, not a claim of longitudinal representativeness.
A future design would need to predeclare either an unweighted linked-sample
estimand or origin-weighted estimates with an explicit inverse-link-propensity
or calibration sensitivity based only on pre-transition observables. It must
show unweighted results and linked-versus-unlinked balance. Cross-sectional
weights must not be described as solving longitudinal attrition.
""",
        encoding="utf-8",
    )

    receipt = {
        "record": "YAX Scope Phase 1 CPS longitudinal feasibility receipt",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "extract": extract_receipt,
        "input_hashes": {
            "microdata": sha256(args.microdata),
            "codebook": sha256(args.codebook),
            "xml_metadata": sha256(args.xml_metadata),
            "bridge": sha256(args.bridge),
            "v41_membership": sha256(args.membership),
            "computerization": sha256(args.computerization),
        },
        "link_rules": {
            "preferred_id": "CPSIDV",
            "adjacent": "origin MISH 1/2/3/5/6/7, target calendar month present, same CPSIDV, destination MISH=origin+1",
            "long_gap": "origin MISH 4, target month t+9 present, same CPSIDV, destination MISH 5; reported separately",
            "age": "18-65 eligibility and age group classified at origin",
        },
        "age_boundary_crosses": int(age_cross.sum()),
        "age_boundary_eligible_matched": int(boundary_valid.sum()),
        "switching": switching,
        "flow_treatment_effect_regressions_executed": [],
        "output_hashes": {
            path.name: sha256(path)
            for path in (inventory_path, match_path, flow_path, noise_path, weight_path)
        },
    }
    receipt_path = args.output_dir / "CPS_LONGITUDINAL_FEASIBILITY_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", type=pathlib.Path, required=True)
    parser.add_argument("--codebook", type=pathlib.Path, required=True)
    parser.add_argument("--xml-metadata", type=pathlib.Path, required=True)
    parser.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    parser.add_argument("--membership", type=pathlib.Path, default=ROOT / "yax/analysis/postoutcome_v41_quintile_weight/YAX_V41_QUINTILE_MEMBERSHIP.csv")
    parser.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    receipt = run(args)
    print(json.dumps({"status": "PASS_PHASE1_FLOW_FEASIBILITY", "outputs": receipt["output_hashes"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

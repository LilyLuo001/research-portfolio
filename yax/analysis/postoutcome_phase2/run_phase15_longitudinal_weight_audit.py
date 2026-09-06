#!/usr/bin/env python3
"""Audit the official adjacent-month CPS weight before any Phase-2 flow model.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.

This program reads linking information and pre-period exposure assignments only.
It does not construct or estimate an employment-flow outcome coefficient.
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
MERGE_KEY = ["YEAR", "MONTH", "SERIAL", "PERNUM"]
ID_COLUMNS = ["CPSID", "CPSIDP", "CPSIDV"]
MAIN_COLUMNS = [
    "YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP", "CPSIDV",
    "MISH", "AGE", "EMPSTAT", "OCC", "WTFINL", "ASECFLAG",
]
PATCH_COLUMNS = [
    "YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP", "CPSIDV",
    "MISH", "AGE", "LNKFW1MWT",
]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write an empty file: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_aligned(main_path: pathlib.Path, patch_path: pathlib.Path) -> tuple[pd.DataFrame, dict]:
    main_iter = pd.read_csv(main_path, usecols=MAIN_COLUMNS, chunksize=400_000)
    patch_iter = pd.read_csv(patch_path, usecols=PATCH_COLUMNS, chunksize=400_000)
    pieces: list[pd.DataFrame] = []
    rows = 0
    basic_rows = 0
    merge_key_mismatches = 0
    identifier_mismatches = {name: 0 for name in ID_COLUMNS}
    mish_mismatches = 0
    age_mismatches = 0

    while True:
        try:
            main = next(main_iter)
        except StopIteration:
            main = None
        try:
            patch = next(patch_iter)
        except StopIteration:
            patch = None
        if main is None or patch is None:
            if main is not None or patch is not None:
                raise RuntimeError("main and patch extracts have different chunk/row counts")
            break
        if len(main) != len(patch):
            raise RuntimeError("aligned extract chunks have different row counts")
        rows += len(main)
        for column in MERGE_KEY:
            merge_key_mismatches += int(main[column].ne(patch[column]).sum())
        for column in ID_COLUMNS:
            identifier_mismatches[column] += int(main[column].fillna(-1).ne(patch[column].fillna(-1)).sum())
        mish_mismatches += int(main.MISH.fillna(-1).ne(patch.MISH.fillna(-1)).sum())
        age_mismatches += int(main.AGE.fillna(-1).ne(patch.AGE.fillna(-1)).sum())
        if merge_key_mismatches or any(identifier_mismatches.values()) or mish_mismatches or age_mismatches:
            raise RuntimeError("patch is not row-identical to the wide extract on keys/identifiers")

        main["LNKFW1MWT"] = pd.to_numeric(patch.LNKFW1MWT, errors="raise")
        basic = main.loc[
            main.ASECFLAG.ne(1) & pd.to_numeric(main.WTFINL, errors="coerce").gt(0)
        ].drop(columns="ASECFLAG")
        pieces.append(basic)
        basic_rows += len(basic)

    frame = pd.concat(pieces, ignore_index=True)
    del pieces
    for column in ["YEAR", "MONTH", "SERIAL", "PERNUM", "MISH", "AGE", "EMPSTAT", "OCC"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    for column in ID_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("int64")
    frame["WTFINL"] = pd.to_numeric(frame.WTFINL, errors="raise").astype("float64")
    frame["LNKFW1MWT"] = pd.to_numeric(frame.LNKFW1MWT, errors="raise").astype("float64")
    duplicate_merge_keys = int(frame.duplicated(MERGE_KEY).sum())
    if duplicate_merge_keys:
        raise RuntimeError(f"basic sample has {duplicate_merge_keys} duplicate merge keys")
    frame["month_ord"] = frame.YEAR.astype("int32") * 12 + frame.MONTH.astype("int32")
    frame["month"] = frame.YEAR.astype(str) + "-" + frame.MONTH.astype(str).str.zfill(2)
    frame["young"] = frame.AGE.between(22, 25)
    frame["older"] = frame.AGE.between(26, 65)
    frame["employed"] = frame.EMPSTAT.isin([10, 12])
    return frame, {
        "wide_rows": rows,
        "patch_rows": rows,
        "basic_positive_WTFINL_rows": basic_rows,
        "merge_key": MERGE_KEY,
        "merge_success_rate": 1.0,
        "merge_key_mismatches": merge_key_mismatches,
        "identifier_mismatches": identifier_mismatches,
        "mish_mismatches": mish_mismatches,
        "age_mismatches": age_mismatches,
        "duplicate_basic_merge_keys": duplicate_merge_keys,
    }


def add_beta_quintile(frame: pd.DataFrame, bridge_path: pathlib.Path, membership_path: pathlib.Path) -> dict:
    bridge = pd.read_csv(bridge_path, dtype={"census_2010": str, "census_2018": str})
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
        .set_index("census_2010").census_2018.to_dict()
    )
    membership = pd.read_csv(membership_path, dtype={"occ_code": str})
    membership["occ_code"] = membership.occ_code.str.zfill(4)
    quintile = membership.set_index("occ_code").preperiod_quintile.astype(int).to_dict()
    source = frame.OCC.astype(int).map(lambda value: f"{value:04d}")
    mapped = source.copy()
    mapped.loc[frame.YEAR.le(2019)] = source.loc[frame.YEAR.le(2019)].map(dominant)
    mapped = mapped.where(frame.employed)
    frame["occ2018_modal"] = mapped.astype("string")
    frame["beta_quintile"] = frame.occ2018_modal.map(quintile).astype("float32")
    return {
        "membership_occupation_count": int(len(membership)),
        "beta_Q5_codes_sha256": hashlib.sha256(
            "\n".join(sorted(membership.loc[membership.preperiod_quintile.eq(5), "occ_code"])).encode()
        ).hexdigest(),
        "beta_Q5_occupation_count": int(membership.preperiod_quintile.eq(5).sum()),
    }


def eligible_origins(frame: pd.DataFrame) -> pd.DataFrame:
    observed_months = set(frame.month_ord.unique())
    origins = frame.loc[
        frame.AGE.between(22, 65)
        & frame.EMPSTAT.between(10, 36)
        & frame.MISH.isin([1, 2, 3, 5, 6, 7])
    ].copy()
    origins["target_ord"] = origins.month_ord + 1
    origins = origins.loc[origins.target_ord.isin(observed_months)].copy()
    # The missing October 2025 sample means September has no exact t+1 target.
    if int((origins.month.eq("2025-09") & origins.target_ord.eq(2025 * 12 + 10)).sum()):
        raise RuntimeError("September 2025 incorrectly retained despite missing October sample")
    return origins


def attach_matches(origins: pd.DataFrame, frame: pd.DataFrame, identifier: str) -> pd.Series:
    destination = frame.loc[frame[identifier].ne(0), [identifier, "month_ord", "MISH"]].copy()
    duplicate_destinations = int(destination.duplicated([identifier, "month_ord"]).sum())
    if duplicate_destinations:
        raise RuntimeError(f"{identifier} is not unique by month: {duplicate_destinations}")
    destination = destination.rename(columns={"month_ord": "dest_month_ord", "MISH": "dest_MISH"})
    left = origins[[identifier, "target_ord", "MISH"]].copy()
    left["__row"] = np.arange(len(left), dtype=np.int64)
    valid = left[identifier].ne(0)
    merged = left.loc[valid].merge(
        destination,
        left_on=[identifier, "target_ord"],
        right_on=[identifier, "dest_month_ord"],
        how="left",
        validate="many_to_one",
    )
    match = pd.Series(False, index=np.arange(len(left)))
    match.loc[merged.__row.to_numpy()] = (
        merged.dest_month_ord.eq(merged.target_ord) & merged.dest_MISH.eq(merged.MISH + 1)
    ).to_numpy()
    match.index = origins.index
    return match


def audit_rows(origins: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []

    def add(dimension: str, level: str, mask: pd.Series, note: str = "") -> None:
        group = origins.loc[mask]
        p_match = group.cpsidp_match
        v_match = group.cpsidv_match
        weighted_base = p_match & group.LNKFW1MWT.gt(0)
        retained = weighted_base & v_match
        base_sum = float(group.loc[weighted_base, "LNKFW1MWT"].sum())
        retained_sum = float(group.loc[retained, "LNKFW1MWT"].sum())
        rows.append({
            "analysis_status": LABEL,
            "dimension": dimension,
            "level": level,
            "eligible_origins": int(len(group)),
            "CPSIDP_matched": int(p_match.sum()),
            "CPSIDP_match_rate": float(p_match.mean()) if len(group) else "",
            "CPSIDV_matched": int(v_match.sum()),
            "CPSIDV_match_rate": float(v_match.mean()) if len(group) else "",
            "positive_LNKFW1MWT": int(group.LNKFW1MWT.gt(0).sum()),
            "positive_weight_among_CPSIDP_matches": float(group.loc[p_match, "LNKFW1MWT"].gt(0).mean()) if p_match.any() else "",
            "CPSIDP_link_weight_sum": base_sum,
            "CPSIDV_retained_weight_sum": retained_sum,
            "weighted_CPSIDV_retention_rate": retained_sum / base_sum if base_sum else "",
            "note": note,
        })

    universal = pd.Series(True, index=origins.index)
    add("overall", "ages 22-65, legitimate adjacent origins", universal)
    add("age_group", "young 22-25", origins.young)
    add("age_group", "older 26-65", origins.older)
    add("period", "pre (through 2022-11)", origins.month.le("2022-11"))
    add("period", "transition boundary (2022-12)", origins.month.eq("2022-12"))
    add("period", "post (2023-01 onward)", origins.month.ge("2023-01"))
    for q in range(1, 6):
        add(
            "origin_beta_quintile",
            f"Q{q}",
            origins.employed & origins.beta_quintile.eq(q),
            "Employed origins on beta Rule-A support; pre-period quintiles.",
        )
    for mish in [1, 2, 3, 5, 6, 7]:
        add("MISH_transition", f"{mish}->{mish + 1}", origins.MISH.eq(mish))
    return rows


def exposure_composition(origins: pd.DataFrame) -> list[dict]:
    universe = origins.cpsidp_match & origins.LNKFW1MWT.gt(0) & origins.employed & origins.beta_quintile.notna()
    retained = universe & origins.cpsidv_match
    dropped = universe & ~origins.cpsidv_match
    rows = []
    for sample, mask in [("CPSIDV retained", retained), ("CPSIDV rejected", dropped)]:
        total = float(origins.loc[mask, "LNKFW1MWT"].sum())
        for q in range(1, 6):
            qmask = mask & origins.beta_quintile.eq(q)
            weight = float(origins.loc[qmask, "LNKFW1MWT"].sum())
            rows.append({
                "analysis_status": LABEL,
                "dimension": "weighted_beta_quintile_composition",
                "level": f"{sample}: Q{q}",
                "eligible_origins": int(mask.sum()),
                "CPSIDP_matched": int(mask.sum()),
                "CPSIDP_match_rate": 1.0,
                "CPSIDV_matched": int((qmask & origins.cpsidv_match).sum()),
                "CPSIDV_match_rate": float(origins.loc[qmask, "cpsidv_match"].mean()) if qmask.any() else "",
                "positive_LNKFW1MWT": int(qmask.sum()),
                "positive_weight_among_CPSIDP_matches": 1.0,
                "CPSIDP_link_weight_sum": weight,
                "CPSIDV_retained_weight_sum": weight if sample == "CPSIDV retained" else 0.0,
                "weighted_CPSIDV_retention_rate": weight / total if total else "",
                "note": "Final rate column is within-sample weighted quintile share for this row family.",
            })
    return rows


def run(args: argparse.Namespace) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame, merge = load_aligned(args.microdata, args.weight_patch)
    mapping = add_beta_quintile(frame, args.bridge, args.membership)
    origins = eligible_origins(frame)
    origins["cpsidp_match"] = attach_matches(origins, frame, "CPSIDP")
    origins["cpsidv_match"] = attach_matches(origins, frame, "CPSIDV")
    origins["official_weight_positive"] = origins.LNKFW1MWT.gt(0)

    impossible = origins.cpsidv_match & ~origins.cpsidp_match
    if impossible.any():
        raise RuntimeError(f"{int(impossible.sum())} CPSIDV matches lack their parent CPSIDP match")
    false_sep_nov = int((
        origins.month.eq("2025-09")
        & origins.cpsidp_match
        & origins.target_ord.eq(2025 * 12 + 11)
    ).sum())
    if false_sep_nov:
        raise RuntimeError("a false September-to-November 2025 link was created")

    rows = audit_rows(origins) + exposure_composition(origins)
    audit_path = args.output_dir / "YAX_PHASE2_LINK_SAMPLE_AUDIT.csv"
    write_csv(audit_path, rows)

    weighted_base = origins.cpsidp_match & origins.LNKFW1MWT.gt(0)
    retained = weighted_base & origins.cpsidv_match
    denominator = float(origins.loc[weighted_base, "LNKFW1MWT"].sum())
    numerator = float(origins.loc[retained, "LNKFW1MWT"].sum())
    weight_among_p = float(origins.loc[origins.cpsidp_match, "LNKFW1MWT"].gt(0).mean())
    overall = {
        "eligible_origins": int(len(origins)),
        "CPSIDP_matches": int(origins.cpsidp_match.sum()),
        "CPSIDP_match_rate": float(origins.cpsidp_match.mean()),
        "CPSIDV_matches": int(origins.cpsidv_match.sum()),
        "CPSIDV_match_rate": float(origins.cpsidv_match.mean()),
        "positive_weight_rate_among_CPSIDP_matches": weight_among_p,
        "weighted_CPSIDV_retention_rate": numerator / denominator,
        "missing_LNKFW1MWT_rate": float(origins.LNKFW1MWT.isna().mean()),
        "zero_LNKFW1MWT_rate": float(origins.LNKFW1MWT.eq(0).mean()),
        "false_September_to_November_2025_links": false_sep_nov,
        "December_2019_to_January_2020_origins_retained_for_status_only": int(origins.month.eq("2019-12").sum()),
    }
    # Hard technical compatibility conditions. Distributional diagnostics are
    # reported for substantive review rather than hidden behind an invented score.
    conditions = {
        "exact_row_merge": merge["merge_success_rate"] == 1.0 and merge["merge_key_mismatches"] == 0,
        "identifiers_identical": not any(merge["identifier_mismatches"].values()),
        "official_weight_present_for_CPSIDP_links": weight_among_p >= 0.999,
        "CPSIDV_is_strict_subset": not impossible.any(),
        "weighted_CPSIDV_retention_at_least_90pct": (numerator / denominator) >= 0.90,
        "no_false_gap_links": false_sep_nov == 0,
    }
    status = "PASS_DEFENSIBLE_CPSIDV_WITH_OFFICIAL_WEIGHT" if all(conditions.values()) else "STOP_WEIGHT_COMPATIBILITY_FAILED"

    receipt = {
        "record": "YAX Phase 1.5 official longitudinal-weight compatibility audit",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "official_variable": {
            "name": "LNKFW1MWT",
            "label": "Longitudinal weight for two adjacent months (BMS only)",
            "IPUMS_variable_page": "https://cps.ipums.org/cps-action/variables/LNKFW1MWT",
            "IPUMS_CPSIDV_page": "https://cps.ipums.org/cps-action/variables/CPSIDV",
            "construction_note": "IPUMS documents availability for samples linkable to the next month using CPSIDP; CPSIDV is a stricter validated identifier derived from CPSIDP.",
        },
        "input_hashes": {
            "wide_microdata_private": sha256(args.microdata),
            "weight_patch_private": sha256(args.weight_patch),
            "weight_patch_codebook_private": sha256(args.weight_codebook),
            "weight_patch_DDI_private": sha256(args.weight_xml),
            "extract_request_receipt": sha256(args.extract_request),
            "bridge": sha256(args.bridge),
            "preperiod_beta_membership": sha256(args.membership),
        },
        "extract": {
            "IPUMS_extract_number": 10,
            "variables_added": PATCH_COLUMNS,
            "merge": merge,
            "fresh_extract_includes_2024_forward_samples": bool(frame.YEAR.ge(2024).any()),
            "statement_on_revisions": "A fresh IPUMS extract generated on 2026-08-31 is used; the audit does not independently reconstruct IPUMS revision history.",
        },
        "link_rule": {
            "eligible_origin_MISH": [1, 2, 3, 5, 6, 7],
            "calendar_rule": "destination month ordinal equals origin month ordinal plus exactly one",
            "destination_rotation_rule": "destination MISH equals origin MISH plus one",
            "long_gap_links_used": False,
            "September_2025_to_November_2025_allowed": False,
            "age_at_origin": "22-25 young; 26-65 older",
        },
        "overall": overall,
        "beta_membership": mapping,
        "compatibility_conditions": conditions,
        "flow_outcome_variables_read": [],
        "AI_flow_coefficients_estimated": [],
        "outputs": {audit_path.name: sha256(audit_path)},
    }
    receipt_path = args.output_dir / "YAX_PHASE2_LONGITUDINAL_WEIGHT_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    def pct(value: float) -> str:
        return f"{100 * value:.3f}%"

    audit_md = args.output_dir / "YAX_PHASE2_LONGITUDINAL_WEIGHT_AUDIT.md"
    audit_md.write_text(
        f"""# YAX Phase 2 longitudinal-weight audit

> **{LABEL}**

## Decision

**{status}**

The minimum patch is IPUMS CPS extract 10, generated 2026-08-31. It contains
the same {merge['wide_rows']:,} rows as the wide extract and adds
`LNKFW1MWT` plus merge identifiers. The row-level merge on
`YEAR MONTH SERIAL PERNUM` succeeds at {pct(merge['merge_success_rate'])};
`CPSID`, `CPSIDP`, `CPSIDV`, `MISH`, and `AGE` agree exactly.

## Official construction and compatibility

IPUMS labels `LNKFW1MWT` as the basic-month longitudinal weight for two
adjacent months. Its documentation ties eligibility to the next-month
`CPSIDP` link. IPUMS constructs `CPSIDV` from `CPSIDP` and rejects links with
implausible changes in age, sex, or race. Therefore the defensible use tested
here is the official origin weight on the stricter CPSIDV-retained subset—not
a claim that the weight itself was constructed for CPSIDV.

| diagnostic | value |
|---|---:|
| legitimate eligible origins, ages 22–65 | {overall['eligible_origins']:,} |
| CPSIDP adjacent matches | {overall['CPSIDP_matches']:,} |
| CPSIDP match rate | {pct(overall['CPSIDP_match_rate'])} |
| CPSIDV adjacent matches | {overall['CPSIDV_matches']:,} |
| CPSIDV match rate | {pct(overall['CPSIDV_match_rate'])} |
| positive official weight among CPSIDP matches | {pct(overall['positive_weight_rate_among_CPSIDP_matches'])} |
| weighted CPSIDV retention within CPSIDP links | {pct(overall['weighted_CPSIDV_retention_rate'])} |
| missing `LNKFW1MWT` | {pct(overall['missing_LNKFW1MWT_rate'])} |
| false September→November 2025 links | {overall['false_September_to_November_2025_links']} |

The primary Phase-2 weight is consequently the origin observation's
`LNKFW1MWT` on successful validated `CPSIDV` links. Unweighted estimates are a
declared sensitivity. `WTFINL` is only a non-longitudinal sensitivity and must
not be described as correcting link selection.

The official weight does not eliminate selection caused by restricting the
sample to CPSIDV-valid links. Age, period, and beta-quintile retention and the
weighted exposure composition of retained versus rejected CPSIDP links are
reported in `YAX_PHASE2_LINK_SAMPLE_AUDIT.csv` and remain mandatory beside
coefficients.

## Link protections

- Origins are MISH 1, 2, 3, 5, 6, or 7 and destinations are exactly one
  calendar month later with MISH incremented by one.
- MISH 4→5 eight-month returns are never constructed.
- Because October 2025 is absent, September 2025 has no eligible next-month
  destination. November is never substituted.
- December 2019→January 2020 remains eligible for employment-status flows but
  will be excluded from every occupational-switching analysis.

## Scope integrity

No employment-flow outcome was constructed and no AI-flow coefficient was
estimated in this audit. A flow-analysis plan must be committed before those
outcomes are opened.
""",
        encoding="utf-8",
    )
    receipt["outputs"][audit_md.name] = sha256(audit_md)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", type=pathlib.Path, required=True)
    parser.add_argument("--weight-patch", type=pathlib.Path, required=True)
    parser.add_argument("--weight-codebook", type=pathlib.Path, required=True)
    parser.add_argument("--weight-xml", type=pathlib.Path, required=True)
    parser.add_argument("--extract-request", type=pathlib.Path, required=True)
    parser.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    parser.add_argument("--membership", type=pathlib.Path, default=ROOT / "yax/analysis/postoutcome_v41_quintile_weight/YAX_V41_QUINTILE_MEMBERSHIP.csv")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({"status": result["status"], "overall": result["overall"]}, indent=2))
    return 0 if result["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Build pre-period CPS employment cells on the frozen raw-OCC lookup routes."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


PRE_END = (2022, 11)
EARLY_ROLE = "raw_occ_main_2017_2019"
CURRENT_ROLE = "raw_occ_main_2020_plus"
LOOKUP_OUTPUT_KEY = "dax/w2/exposure_gate/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv"
MIN_PRIMARY_WEIGHT_COVERAGE = 0.90
CELL_COLUMNS = (
    "month", "lookup_role", "occ_code", "occupation_key",
    "dv_rating_beta", "exposure_quintile", "age_group",
    "employment_headcount", "unweighted_n", "weight_sq_sum",
)
SOURCE_COLUMNS = (
    "YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "OCC2010",
    "CLASSWKR", "WKSTAT", "WTFINL",
)


def month_key(year, month):
    return year.astype(int) * 100 + month.astype(int)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_split_receipt(path: pathlib.Path, source: pathlib.Path) -> dict[str, object]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS_OUTCOME_BLIND_PREPERIOD_SPLIT":
        raise ValueError("source split receipt is not PASS")
    if receipt.get("cutoff_month") != "2022-11":
        raise ValueError("source split receipt has wrong cutoff")
    if receipt.get("protected_fields_decoded_for_rejected_rows") is not False:
        raise ValueError("source split did not preserve the post-outcome seal")
    if receipt.get("postperiod_rows_written") is not False:
        raise ValueError("source split may contain post-period rows")
    if receipt.get("output_sha256") != sha256_file(source):
        raise ValueError("source hash does not match split receipt")
    return receipt


def authenticate_c1_lookup(receipt_path: pathlib.Path, lookup_path: pathlib.Path) -> dict[str, object]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS":
        raise ValueError("C1 receipt is not PASS")
    expected_hash = receipt.get("lookup_sha256")
    if expected_hash is None:
        expected_hash = (
            receipt.get("outputs", {}).get(LOOKUP_OUTPUT_KEY, {}).get("sha256")
        )
    if expected_hash != sha256_file(lookup_path):
        raise ValueError("C1 lookup hash mismatch")
    measure = receipt.get("primary_exposure", receipt.get("primary_measure"))
    if measure is None:
        measure = receipt.get("design", {}).get("primary_exposure")
    if measure != "dv_rating_beta":
        raise ValueError("C1 primary exposure must be dv_rating_beta")
    return receipt


def expected_pre_months(structural_gaps: set[str]) -> list[str]:
    months = []
    for year in range(2017, 2023):
        for month in range(1, 13):
            if (year, month) > PRE_END:
                continue
            value = f"{year:04d}-{month:02d}"
            if value not in structural_gaps:
                months.append(value)
    return months


def validate_source_is_preperiod_only(path: pathlib.Path) -> dict[str, object]:
    """Inspect only YEAR/MONTH, refusing post-containing inputs before outcomes."""
    import pandas as pd

    if path.suffix == ".parquet":
        safe = pd.read_parquet(path, columns=["YEAR", "MONTH"])
    else:
        safe = pd.read_csv(path, usecols=["YEAR", "MONTH"])
    codes = month_key(safe["YEAR"], safe["MONTH"])
    if bool((codes > 202211).any()):
        raise ValueError(
            "REFUSED before reading outcome columns: source contains 2022-12+ rows"
        )
    return {
        "rows": int(len(safe)),
        "first_month_code": int(codes.min()) if len(safe) else None,
        "last_month_code": int(codes.max()) if len(safe) else None,
        "outcome_columns_read": False,
    }


def read_preperiod_source(path: pathlib.Path, split_receipt: pathlib.Path | None = None):
    import pandas as pd

    audited_split = validate_split_receipt(split_receipt, path) if split_receipt else None
    seal = validate_source_is_preperiod_only(path)
    seal["audited_split_status"] = (
        audited_split["status"] if audited_split else "NOT_SUPPLIED_LIBRARY_CALL"
    )
    seal["source_sha256"] = sha256_file(path)
    if path.suffix == ".parquet":
        frame = pd.read_parquet(path, columns=list(SOURCE_COLUMNS))
    else:
        frame = pd.read_csv(path, usecols=list(SOURCE_COLUMNS))
    return frame, seal


def _normalize_occ_code(values):
    import numpy as np
    import pandas as pd

    numeric = pd.to_numeric(values, errors="coerce")
    invalid = numeric.isna() | (numeric < 0) | (numeric > 9999) | (numeric % 1 != 0)
    if bool(invalid.any()):
        raise ValueError("raw OCC must be integer-valued in 0..9999 for every covered row")
    return numeric.astype(int).map(lambda value: f"{value:04d}")


def validate_lookup(lookup):
    import pandas as pd

    required = {
        "lookup_role", "occ_code", "dv_rating_beta",
        "dv_rating_beta_covered_route_mass",
    }
    missing = required - set(lookup.columns)
    if missing:
        raise ValueError(f"C1 lookup missing columns {sorted(missing)}")
    result = lookup.loc[lookup["lookup_role"].astype(str) == CURRENT_ROLE].copy()
    if result.empty:
        raise ValueError("C1 lookup has no direct Census-2018 role")
    result["lookup_role"] = result["lookup_role"].astype(str)
    result["occ_code"] = result["occ_code"].astype(str).str.zfill(4)
    if not result["occ_code"].str.fullmatch(r"\d{4}").all():
        raise ValueError("lookup occ_code must be exactly four digits")
    if result.duplicated(["lookup_role", "occ_code"]).any():
        raise ValueError("duplicate lookup_role+occ_code in C1 lookup")
    result["dv_rating_beta"] = pd.to_numeric(
        result["dv_rating_beta"], errors="coerce"
    )
    result["dv_rating_beta_covered_route_mass"] = pd.to_numeric(
        result["dv_rating_beta_covered_route_mass"], errors="coerce"
    )
    return result


def validate_bridge(bridge):
    import numpy as np
    import pandas as pd

    required = {"census_2010", "census_2018", "bridge_weight"}
    missing = required - set(bridge.columns)
    if missing:
        raise ValueError(f"Census bridge missing columns {sorted(missing)}")
    result = bridge.copy()
    result["census_2010"] = result["census_2010"].astype(str).str.zfill(4)
    result["census_2018"] = result["census_2018"].astype(str).str.zfill(4)
    if not result["census_2010"].str.fullmatch(r"\d{4}").all():
        raise ValueError("bridge census_2010 must be four digits")
    if not result["census_2018"].str.fullmatch(r"\d{4}").all():
        raise ValueError("bridge census_2018 must be four digits")
    result["bridge_weight"] = pd.to_numeric(result["bridge_weight"], errors="coerce")
    if result[["census_2010", "census_2018"]].duplicated().any():
        raise ValueError("duplicate source-target route in Census bridge")
    if (not np.isfinite(result["bridge_weight"]).all()
            or (result["bridge_weight"] <= 0).any()):
        raise ValueError("bridge weights must be finite and positive")
    sums = result.groupby("census_2010")["bridge_weight"].sum()
    if not np.allclose(sums.to_numpy(), 1.0, atol=1e-8, rtol=0):
        raise ValueError("Census bridge weights must sum to one by source code")
    return result[["census_2010", "census_2018", "bridge_weight"]]


def weighted_quintile_cuts(score, weight) -> list[float]:
    import numpy as np

    score = np.asarray(score, dtype=float)
    weight = np.asarray(weight, dtype=float)
    if len(score) == 0 or np.any(weight <= 0) or np.any(~np.isfinite(score + weight)):
        raise ValueError("invalid weighted quintile inputs")
    order = np.argsort(score, kind="mergesort")
    sorted_score, sorted_weight = score[order], weight[order]
    cumulative = np.cumsum(sorted_weight)
    cuts = [
        float(sorted_score[min(np.searchsorted(cumulative, share * cumulative[-1], side="left"), len(score) - 1)])
        for share in (0.2, 0.4, 0.6, 0.8)
    ]
    if any(left >= right for left, right in zip(cuts, cuts[1:])):
        raise ValueError("employment-weighted exposure quintile cuts are not distinct")
    return cuts


def build_cells(
    frame, contract: dict[str, object], lookup, bridge,
    require_complete_months: bool = True,
):
    import numpy as np
    import pandas as pd

    missing = set(SOURCE_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"source missing columns {sorted(missing)}")
    lookup = validate_lookup(lookup)
    bridge = validate_bridge(bridge)
    data = frame.copy()
    data["_month_code"] = month_key(data["YEAR"], data["MONTH"])
    if bool((data["_month_code"] > 202211).any()):
        raise ValueError("post-period rows prohibited in pre-period cell builder")
    data["month"] = (
        data["YEAR"].astype(int).astype(str).str.zfill(4)
        + "-" + data["MONTH"].astype(int).astype(str).str.zfill(2)
    )
    gaps = set(contract["structural_gaps"]["omit_months"])
    gap_rows = data["month"].isin(gaps)
    data = data.loc[~gap_rows].copy()
    observed_months = sorted(data["month"].unique().tolist())
    expected = expected_pre_months(gaps)
    missing_months = sorted(set(expected) - set(observed_months))
    unexpected_months = sorted(set(observed_months) - set(expected))
    if require_complete_months and (missing_months or unexpected_months):
        raise ValueError(
            f"pre-period month coverage mismatch: missing={missing_months}, unexpected={unexpected_months}"
        )

    age = pd.to_numeric(data["AGE"], errors="coerce")
    in_age = age.between(contract["age"]["primary_min"], contract["age"]["primary_max"])
    empstat = pd.to_numeric(data["EMPSTAT"], errors="coerce")
    employed = empstat.isin(contract["employment"]["employed_codes"])
    weight = pd.to_numeric(data["WTFINL"], errors="coerce")
    valid_weight = np.isfinite(weight) & (weight > 0)
    base = data.loc[in_age & employed & valid_weight].copy()
    base["_weight"] = weight.loc[base.index].astype(float)
    base["source_occ_code"] = _normalize_occ_code(base["OCC"])
    early_base = base.loc[base["YEAR"].astype(int) <= 2019].copy()
    current = base.loc[base["YEAR"].astype(int) >= 2020].copy()
    available_sources = set(bridge["census_2010"])
    missing_bridge = ~early_base["source_occ_code"].isin(available_sources)
    missing_bridge_weight = float(early_base.loc[missing_bridge, "_weight"].sum())
    early = early_base.loc[~missing_bridge].merge(
        bridge, left_on="source_occ_code", right_on="census_2010",
        how="left", validate="many_to_many",
    )
    early["_route_share"] = early["bridge_weight"].astype(float)
    early["occ_code"] = early["census_2018"]
    current["_route_share"] = 1.0
    current["occ_code"] = current["source_occ_code"]
    routes = pd.concat([early, current], ignore_index=True, sort=False)
    routes["_route_n"] = routes["_route_share"]
    routes["_weight"] = routes["_weight"] * routes["_route_share"]
    routes["lookup_role"] = CURRENT_ROLE
    routes["occupation_key"] = "census2018:" + routes["occ_code"]

    merged = routes.merge(
        lookup, on=["lookup_role", "occ_code"], how="left",
        validate="many_to_one", indicator=True,
    )
    full_exposure = (
        (merged["_merge"] == "both")
        & np.isfinite(pd.to_numeric(merged["dv_rating_beta"], errors="coerce"))
        & np.isclose(
            pd.to_numeric(
                merged["dv_rating_beta_covered_route_mass"], errors="coerce"
            ),
            1.0,
            atol=1e-8,
            rtol=0,
        )
    )
    total_route_weight = float(merged["_weight"].sum()) + missing_bridge_weight
    excluded_exposure_weight = float(merged.loc[~full_exposure, "_weight"].sum())
    excluded_weight = missing_bridge_weight + excluded_exposure_weight
    covered_fraction = (
        1.0 - excluded_weight / total_route_weight if total_route_weight > 0 else 0.0
    )
    coverage_pass = covered_fraction >= MIN_PRIMARY_WEIGHT_COVERAGE
    missing_bridge_by_code = (
        early_base.loc[missing_bridge]
        .groupby("source_occ_code")["_weight"].sum()
        .sort_values(ascending=False).head(25)
    )
    missing_exposure_by_code = (
        merged.loc[~full_exposure]
        .groupby("occ_code")["_weight"].sum()
        .sort_values(ascending=False).head(25)
    )
    merged = merged.loc[full_exposure].drop(columns="_merge").copy()
    route_mass = (
        merged.groupby(["lookup_role", "occ_code", "dv_rating_beta"], as_index=False)["_weight"]
        .sum()
    )
    cuts = weighted_quintile_cuts(route_mass["dv_rating_beta"], route_mass["_weight"])
    merged["exposure_quintile"] = (
        np.searchsorted(np.asarray(cuts), merged["dv_rating_beta"].to_numpy(), side="left") + 1
    )
    if set(merged["exposure_quintile"]) != {1, 2, 3, 4, 5}:
        raise ValueError("all five exposure quintiles must have positive covered employment mass")
    merged["age_group"] = np.where(
        pd.to_numeric(merged["AGE"]).between(22, 25), "young_22_25", "older_26_65"
    )
    merged["_weight_sq"] = merged["_weight"] ** 2
    cells = (
        merged.groupby([
            "month", "lookup_role", "occ_code", "occupation_key",
            "dv_rating_beta", "exposure_quintile", "age_group",
        ], as_index=False)
        .agg(
            employment_headcount=("_weight", "sum"),
            unweighted_n=("_route_n", "sum"),
            weight_sq_sum=("_weight_sq", "sum"),
        )
        .sort_values(["month", "lookup_role", "occ_code", "age_group"])
        .reset_index(drop=True)
    )

    classwkr = pd.to_numeric(merged["CLASSWKR"], errors="coerce")
    general_wage = classwkr.isin(contract["class_of_worker"]["general_wage_salary_codes"])
    receipt = {
        "record_version": "cps-young-relative-employment-target-occ-cells-v3",
        "status": (
            "PASS_PREPERIOD_CELLS" if coverage_pass
            else "FAIL_PRIMARY_EXPOSURE_COVERAGE"
        ),
        "post_outcomes_read": False,
        "primary_occupation_variable": "OCC",
        "pre2020_mapping": "raw OCC probabilistically expanded to Census-2018 with official conversion rates",
        "post2020_mapping": "raw OCC directly observed on Census-2018 taxonomy",
        "primary_lookup_key": ["lookup_role", "occ_code"],
        "occ2010_role": "sensitivity_only",
        "rows_input": int(len(frame)),
        "rows_structural_asec_omitted": int(gap_rows.sum()),
        "structural_asec_months": sorted(gaps),
        "rows_primary_age": int(in_age.sum()),
        "rows_employed_primary_age": int((in_age & employed).sum()),
        "rows_invalid_weight_among_employed_primary_age": int((in_age & employed & ~valid_weight).sum()),
        "rows_matched_route": int(len(merged)),
        "missing_bridge_weight": missing_bridge_weight,
        "excluded_nonfull_exposure_weight": excluded_exposure_weight,
        "excluded_total_weight": excluded_weight,
        "covered_route_mass_fraction": covered_fraction,
        "minimum_coverage_threshold": MIN_PRIMARY_WEIGHT_COVERAGE,
        "coverage_gate_pass": coverage_pass,
        "largest_missing_bridge_source_codes": [
            {"occ_code": str(code), "weight": float(value)}
            for code, value in missing_bridge_by_code.items()
        ],
        "largest_nonfull_exposure_target_codes": [
            {"occ_code": str(code), "weight": float(value)}
            for code, value in missing_exposure_by_code.items()
        ],
        "lookup_route_count": int(len(lookup)),
        "matched_route_count": int(route_mass.shape[0]),
        "quintile_measure": "dv_rating_beta",
        "quintile_cutpoints": cuts,
        "quintile_weighting_window": [observed_months[0], observed_months[-1]],
        "quintile_weighting_population": "WTFINL-weighted employed ages 22-65 after raw-route join",
        "general_wage_salary_code20_rows": int(general_wage.sum()),
        "private_wage_salary_sensitivity_ready": bool(not general_wage.any()),
        "months_observed": observed_months,
        "missing_expected_months": missing_months,
        "unexpected_months": unexpected_months,
        "cell_rows": int(len(cells)),
        "cell_columns": list(CELL_COLUMNS),
    }
    return cells[list(CELL_COLUMNS)], receipt


def main() -> int:
    import pandas as pd

    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--split-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--contract", type=pathlib.Path, required=True)
    parser.add_argument("--lookup", type=pathlib.Path, required=True)
    parser.add_argument("--bridge", type=pathlib.Path, required=True)
    parser.add_argument("--c1-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--cells-out", type=pathlib.Path, required=True)
    parser.add_argument("--receipt-out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    c1 = authenticate_c1_lookup(args.c1_receipt, args.lookup)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    frame, seal = read_preperiod_source(args.source, args.split_receipt)
    lookup = pd.read_csv(args.lookup, dtype={"occ_code": str})
    bridge = pd.read_csv(
        args.bridge, dtype={"census_2010": str, "census_2018": str}
    )
    cells, receipt = build_cells(frame, contract, lookup, bridge)
    receipt["source_seal"] = seal
    receipt["lookup_sha256"] = sha256_file(args.lookup)
    receipt["bridge_sha256"] = sha256_file(args.bridge)
    receipt["c1_receipt_status"] = c1["status"]
    args.cells_out.parent.mkdir(parents=True, exist_ok=True)
    cells.to_csv(args.cells_out, index=False)
    receipt["cells_sha256"] = sha256_file(args.cells_out)
    args.receipt_out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"],
        "cell_rows": receipt["cell_rows"],
        "post_outcomes_read": receipt["post_outcomes_read"],
        "covered_route_mass_fraction": receipt["covered_route_mass_fraction"],
    }, indent=2))
    return 0 if receipt["status"] == "PASS_PREPERIOD_CELLS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

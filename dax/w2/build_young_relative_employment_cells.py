"""Build pre-period CPS employment-headcount cells; fail closed on post data."""

from __future__ import annotations

import argparse
import json
import pathlib


PRE_END = (2022, 11)
CELL_COLUMNS = (
    "month", "occ2010", "age_group", "employment_headcount",
    "unweighted_n", "weight_sq_sum",
)
SOURCE_COLUMNS = (
    "YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "OCC2010",
    "CLASSWKR", "WKSTAT", "WTFINL",
)


def month_key(year, month):
    return year.astype(int) * 100 + month.astype(int)


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


def read_preperiod_source(path: pathlib.Path):
    import pandas as pd

    seal = validate_source_is_preperiod_only(path)
    if path.suffix == ".parquet":
        frame = pd.read_parquet(path, columns=list(SOURCE_COLUMNS))
    else:
        frame = pd.read_csv(path, usecols=list(SOURCE_COLUMNS))
    return frame, seal


def build_cells(frame, contract: dict[str, object], require_complete_months: bool = True):
    import numpy as np
    import pandas as pd

    missing = set(SOURCE_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"source missing columns {sorted(missing)}")
    data = frame.copy()
    data["_month_code"] = month_key(data["YEAR"], data["MONTH"])
    if bool((data["_month_code"] > 202211).any()):
        raise ValueError("post-period rows prohibited in pre-period cell builder")
    data["month"] = (
        data["YEAR"].astype(int).astype(str).str.zfill(4)
        + "-"
        + data["MONTH"].astype(int).astype(str).str.zfill(2)
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
            f"pre-period month coverage mismatch: missing={missing_months}, "
            f"unexpected={unexpected_months}"
        )

    age = pd.to_numeric(data["AGE"], errors="coerce")
    in_age = age.between(
        contract["age"]["primary_min"], contract["age"]["primary_max"]
    )
    empstat = pd.to_numeric(data["EMPSTAT"], errors="coerce")
    employed = empstat.isin(contract["employment"]["employed_codes"])
    weight = pd.to_numeric(data["WTFINL"], errors="coerce")
    valid_weight = np.isfinite(weight) & (weight > 0)
    occ = pd.to_numeric(data["OCC2010"], errors="coerce")
    valid_occ = occ.isin(contract["occupation"]["valid_occ2010_codes"])

    base = data.loc[in_age & employed & valid_weight].copy()
    base["_weight"] = weight.loc[base.index].astype(float)
    base["_occ"] = occ.loc[base.index]
    base["_valid_occ"] = valid_occ.loc[base.index]
    classwkr = pd.to_numeric(base["CLASSWKR"], errors="coerce")
    general_wage = classwkr.isin(
        contract["class_of_worker"]["general_wage_salary_codes"]
    )

    matched = base.loc[base["_valid_occ"]].copy()
    matched["occ2010"] = matched["_occ"].astype(int)
    matched["age_group"] = np.where(
        pd.to_numeric(matched["AGE"]).between(22, 25), "young_22_25", "older_26_65"
    )
    matched["_weight_sq"] = matched["_weight"] ** 2
    cells = (
        matched.groupby(["month", "occ2010", "age_group"], as_index=False)
        .agg(
            employment_headcount=("_weight", "sum"),
            unweighted_n=("_weight", "size"),
            weight_sq_sum=("_weight_sq", "sum"),
        )
        .sort_values(["month", "occ2010", "age_group"])
        .reset_index(drop=True)
    )

    unmatched = base.loc[~base["_valid_occ"]]
    receipt = {
        "record_version": "cps-young-relative-employment-cells-v1",
        "status": "PASS_PREPERIOD_CELLS",
        "post_outcomes_read": False,
        "rows_input": int(len(frame)),
        "rows_structural_asec_omitted": int(gap_rows.sum()),
        "structural_asec_months": sorted(gaps),
        "rows_primary_age": int(in_age.sum()),
        "rows_employed_primary_age": int((in_age & employed).sum()),
        "rows_invalid_weight_among_employed_primary_age": int(
            (in_age & employed & ~valid_weight).sum()
        ),
        "rows_matched_occupation": int(len(matched)),
        "rows_unmatched_occupation": int(len(unmatched)),
        "unmatched_weight": float(unmatched["_weight"].sum()),
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--contract", type=pathlib.Path, required=True)
    parser.add_argument("--cells-out", type=pathlib.Path, required=True)
    parser.add_argument("--receipt-out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    frame, seal = read_preperiod_source(args.source)
    cells, receipt = build_cells(frame, contract)
    receipt["source_seal"] = seal
    args.cells_out.parent.mkdir(parents=True, exist_ok=True)
    cells.to_csv(args.cells_out, index=False)
    args.receipt_out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"],
        "cell_rows": receipt["cell_rows"],
        "post_outcomes_read": receipt["post_outcomes_read"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

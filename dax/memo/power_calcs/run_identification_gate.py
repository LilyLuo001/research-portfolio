"""Pre-outcome identification gate for the continuous DAX design.

Input is the real W5 occupation-month dose panel, never an outcome panel. The
script residualizes DAX on the complete registered nuisance design and then
computes the singular-value profile of the residual occupation-by-month
matrix. A rank-one profile is a cross-sectional exposure contrast, not a
dynamic treatment path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib

import numpy as np

REQUIRED = {"cps_occ", "month", "dax", "industry", "static_decile", "weight"}
FORBIDDEN_OUTCOME_TOKENS = {
    "employment", "hours", "wage", "earnings", "outcome", "empstat", "uhrsworkt"
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def matrix_diagnostics(matrix: np.ndarray, rank_tolerance: float = 1e-6) -> dict[str, object]:
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2 or not matrix.size:
        raise ValueError("residual dose matrix must be nonempty and two-dimensional")
    singular = np.linalg.svd(matrix, compute_uv=False)
    if not len(singular) or singular[0] <= 0:
        return {"effective_rank": 0, "leading_singular_share": None,
                "singular_values": [float(x) for x in singular]}
    total = float(np.square(singular).sum())
    return {
        "effective_rank": int((singular > singular[0] * rank_tolerance).sum()),
        "leading_singular_share": float(singular[0] ** 2 / total) if total > 0 else None,
        "singular_values": [float(x) for x in singular],
    }


def evaluate(frame, minimum_rank: int = 2, maximum_leading_share: float = 0.95,
             rank_tolerance: float = 1e-6) -> dict[str, object]:
    import pandas as pd

    lower_columns = {str(column).lower() for column in frame.columns}
    outcome_columns = sorted(
        column for column in lower_columns
        if any(token in column for token in FORBIDDEN_OUTCOME_TOKENS)
    )
    if outcome_columns:
        raise ValueError(f"outcome-like columns forbidden before unsealing: {outcome_columns}")
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"dose panel lacks required columns {sorted(missing)}")
    data = frame.copy()
    if data.duplicated(["cps_occ", "month"]).any():
        raise ValueError("dose panel must have exactly one row per occupation-month")
    counts = data.groupby("cps_occ")["month"].nunique()
    if counts.empty or counts.nunique() != 1:
        raise ValueError("identification gate requires a balanced occupation-month panel")
    if data["dax"].isna().any() or data["weight"].isna().any():
        raise ValueError("dax and weight must be complete")
    weights = data["weight"].astype(float).to_numpy()
    if np.any(weights <= 0):
        raise ValueError("identification weights must be strictly positive")

    month = data["month"].astype(str)
    nuisance_labels = pd.DataFrame({
        "occupation": data["cps_occ"].astype(str),
        "month": month,
        "industry_month": data["industry"].astype(str) + "|" + month,
        "decile_month": data["static_decile"].astype(str) + "|" + month,
    })
    nuisance = pd.get_dummies(nuisance_labels, drop_first=False, dtype=float).to_numpy()
    nuisance = np.column_stack([np.ones(len(data)), nuisance])
    y = data["dax"].astype(float).to_numpy()
    root_weight = np.sqrt(weights)
    coefficients = np.linalg.lstsq(nuisance * root_weight[:, None],
                                    y * root_weight, rcond=None)[0]
    residual = y - nuisance @ coefficients
    residual_frame = pd.DataFrame({
        "cps_occ": data["cps_occ"].astype(str), "month": month, "residual": residual
    })
    matrix = (residual_frame.pivot(index="cps_occ", columns="month", values="residual")
              .sort_index().sort_index(axis=1).to_numpy())
    diagnostics = matrix_diagnostics(matrix, rank_tolerance)
    leading = diagnostics["leading_singular_share"]
    passed = (
        diagnostics["effective_rank"] >= minimum_rank
        and leading is not None and leading <= maximum_leading_share
        and float(np.average(np.square(residual), weights=weights)) > 0
    )
    return {
        "status": "PASS_DYNAMIC_IDENTIFICATION" if passed else "FAIL_DEGENERATE_DESIGN",
        "n_occupations": int(matrix.shape[0]),
        "n_months": int(matrix.shape[1]),
        "n_panel_rows": int(len(data)),
        "weighted_residual_dose_variance": float(
            np.average(np.square(residual), weights=weights)
        ),
        "effective_rank": diagnostics["effective_rank"],
        "leading_singular_share": leading,
        "minimum_rank": minimum_rank,
        "maximum_leading_share": maximum_leading_share,
        "rank_tolerance": rank_tolerance,
        "dynamic_claim_allowed": passed,
        "degenerate_reporting_rule": (
            "If this gate fails, report the coefficient only as a cross-sectional "
            "exposure contrast and strike all dynamic treatment language."
        ),
        "outcome_data_opened": False,
    }


def main() -> int:
    import pandas as pd

    parser = argparse.ArgumentParser()
    parser.add_argument("--dose-panel", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--minimum-rank", type=int, default=2)
    parser.add_argument("--maximum-leading-share", type=float, default=0.95)
    args = parser.parse_args()
    frame = (pd.read_parquet(args.dose_panel) if args.dose_panel.suffix == ".parquet"
             else pd.read_csv(args.dose_panel))
    receipt = evaluate(frame, args.minimum_rank, args.maximum_leading_share)
    receipt["generated_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    receipt["input_name"] = args.dose_panel.name
    receipt["input_sha256"] = sha256(args.dose_panel)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["dynamic_claim_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

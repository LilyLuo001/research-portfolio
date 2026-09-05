#!/usr/bin/env python3
"""Implement the published BCC exposure grouping inside the fixed YAX CPS design.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.

This is not a replication of Brynjolfsson, Chandar, and Chen (BCC): their ADP
microdata, title mapping, balanced-firm panel, and hiring outcomes are not
public. It uses their published primary GPT-4 beta construction and top-two
versus bottom-three quintile grouping inside YAX's CPS stock design.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

import importlib.util
import sys


def import_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = import_path("round2_core", ROOT / "yax/revision/referee_20260905/run_referee_core.py")
FROZEN = CORE.FROZEN
DRAWS = 9999
MEASURES = (
    "aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize_fit(fit, influence, target: int, signs: np.ndarray) -> dict:
    contrast = np.zeros(len(fit.beta))
    contrast[target] = 1.0
    summary, centered = CORE.bootstrap_linear(fit, influence, contrast, signs)
    summary["mde80_normal"] = (1.959964 + 0.841621) * summary["analytic_or_paired_se"]
    return summary


def growth_ratio(end: float, start: float) -> float:
    return float(end / start - 1.0)


def read_external(path: Path, column: str) -> dict[str, float]:
    frame = pd.read_csv(path, dtype={"census2018": str})
    frame["census2018"] = frame.census2018.str.zfill(4)
    return pd.to_numeric(frame.set_index("census2018")[column], errors="coerce").to_dict()


def architecture_fit(data: dict, exposure: dict[str, float], support: list[str],
                     months: list[str], signs: np.ndarray) -> tuple[dict, object, np.ndarray, np.ndarray]:
    young, older = FROZEN.panel_arrays(data["panel"], support, months)
    weights = (young + older).sum(axis=1)
    values = np.array([exposure[code] for code in support], float)
    quintile, cuts = CORE.weighted_quintile_with_cuts(values, weights)
    grouping = np.where(quintile >= 4, 2, 1)
    fit, influence, _, labels = CORE.fit_group_model(
        data["panel"], support, months, grouping,
        data["computers"]["webb_pct_software"],
    )
    result = summarize_fit(fit, influence, 0, signs)
    result.update({
        "support_occupations": len(support),
        "support_hash_sha256": CORE.support_hash(support),
        "high_occupation_count": int(np.sum(grouping == 2)),
        "high_employment_share": float(weights[grouping == 2].sum() / weights.sum()),
        "quintile_cuts": cuts.tolist(),
        "labels": labels,
    })
    return result, fit, influence, grouping


def architecture_comparison(args: argparse.Namespace, data: dict, months: list[str]) -> dict:
    exposures = {name: data["exposures"][name]["A"] for name in MEASURES}
    exposures.update({
        "webb_ai_patent_task": read_external(args.webb_ai_map, "webb_ai"),
        "oecd_ai_capability_gap_reversed": read_external(
            args.oecd_ai_map, "oecd_ai_gap_reversed"
        ),
    })
    webb = data["computers"]["webb_pct_software"]
    base = sorted(data["occupations"])
    native_rows = []
    for index, (name, exposure) in enumerate(exposures.items()):
        support = CORE.V4.finite_support(base, exposure, webb)
        signs = np.random.default_rng(2026090520 + index).choice(
            np.array([-1.0, 1.0]), size=(DRAWS, len(support))
        )
        result, _, _, _ = architecture_fit(data, exposure, support, months, signs)
        native_rows.append({"architecture": name, "support_rule": "native", **result})

    common = sorted(
        code for code in base
        if np.isfinite(webb.get(code, np.nan))
        and all(np.isfinite(exposure.get(code, np.nan)) for exposure in exposures.values())
    )
    common_signs = np.random.default_rng(2026090540).choice(
        np.array([-1.0, 1.0]), size=(DRAWS, len(common))
    )
    common_rows, fits = [], {}
    for name, exposure in exposures.items():
        result, fit, influence, grouping = architecture_fit(
            data, exposure, common, months, common_signs
        )
        common_rows.append({"architecture": name, "support_rule": "literal_common", **result})
        fits[name] = (fit, influence, grouping)

    beta_fit, beta_influence, _ = fits["dv_rating_beta"]
    paired_rows = []
    for name, (fit, influence, _) in fits.items():
        if name == "dv_rating_beta":
            continue
        difference_vector = beta_influence[:, 0] - influence[:, 0]
        centered = common_signs @ difference_vector
        estimate = float(beta_fit.beta[0] - fit.beta[0])
        se = float(np.sqrt(np.sum(np.square(difference_vector))))
        try:
            critical = float(np.quantile(np.abs(centered / se), .95, method="higher"))
        except TypeError:
            critical = float(np.quantile(np.abs(centered / se), .95, interpolation="higher"))
        paired_rows.append({
            "contrast": f"dv_rating_beta_minus_{name}",
            "support_rule": "literal_common",
            "support_occupations": len(common),
            "support_hash_sha256": CORE.support_hash(common),
            "coefficient_difference": estimate,
            "paired_occupation_cluster_se": se,
            "paired_ci_lower": estimate - critical * se,
            "paired_ci_upper": estimate + critical * se,
            "paired_p_value": float(
                (1 + np.sum(np.abs(centered / se) >= abs(estimate / se))) / (DRAWS + 1)
            ),
            "normal_theory_mde80": (1.959964 + 0.841621) * se,
            "common_occupation_multipliers": True,
            "bootstrap_draws": DRAWS,
        })

    pd.DataFrame(native_rows + common_rows).to_csv(
        args.output_dir / "BCC_GROUPING_ARCHITECTURE_RESULTS.csv", index=False
    )
    pd.DataFrame(paired_rows).to_csv(
        args.output_dir / "BCC_GROUPING_PAIRED_DIFFERENCES.csv", index=False
    )
    return {
        "native_results": native_rows,
        "common_results": common_rows,
        "paired_differences": paired_rows,
        "common_support_occupations": len(common),
        "common_support_hash_sha256": CORE.support_hash(common),
    }


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = CORE.load_data(args)
    # Hold the CPS outcome sample and Webb conditioning support fixed to YAX's
    # primary specification.  Some CPS occupations have a beta value but no
    # Webb value; allowing those rows only in the unconditioned regression
    # would turn the control comparison into a simultaneous sample change.
    support = CORE.V4.finite_support(
        sorted(data["occupations"]),
        data["exposures"]["dv_rating_beta"]["A"],
        data["computers"]["webb_pct_software"],
    )
    months = list(data["static_months"])
    young, older = FROZEN.panel_arrays(data["panel"], support, months)
    weights = (young + older).sum(axis=1)
    beta = np.array([data["exposures"]["dv_rating_beta"]["A"][code] for code in support])
    quintile, cuts = CORE.weighted_quintile_with_cuts(beta, weights)
    grouping = np.where(quintile >= 4, 2, 1)
    rng = np.random.default_rng(2026090511)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(DRAWS, len(support)))

    controlled_fit, controlled_influence, _, controlled_labels = CORE.fit_group_model(
        data["panel"], support, months, grouping, data["computers"]["webb_pct_software"]
    )
    controlled = summarize_fit(controlled_fit, controlled_influence, 0, signs)
    controlled["specification"] = "YAX fixed design; BCC top-two vs bottom-three; Webb conditioned"
    controlled["labels"] = controlled_labels

    post = np.array([month >= "2023-01" for month in months])
    regressor = (((grouping == 2)[:, None]) & post[None, :]).reshape(-1).astype(float)[:, None]
    raw_fit, raw_influence = FROZEN.fit_with_influence(young, older, regressor)
    unconditioned = summarize_fit(raw_fit, raw_influence, 0, signs)
    unconditioned["specification"] = "YAX fixed design; BCC top-two vs bottom-three; no computerization control"

    start_month, end_month = "2022-11", "2026-06"
    start, end = months.index(start_month), months.index(end_month)
    low, high = grouping == 1, grouping == 2
    descriptive = {
        "start_month": start_month,
        "end_month": end_month,
        "young_low_growth": growth_ratio(young[low, end].sum(), young[low, start].sum()),
        "young_high_growth": growth_ratio(young[high, end].sum(), young[high, start].sum()),
        "young_high_kept_pace_shortfall": float(
            (young[high, end].sum() / young[high, start].sum()) /
            (young[low, end].sum() / young[low, start].sum()) - 1.0
        ),
        "older_low_growth": growth_ratio(older[low, end].sum(), older[low, start].sum()),
        "older_high_growth": growth_ratio(older[high, end].sum(), older[high, start].sum()),
    }

    membership = pd.DataFrame({
        "occupation_code": support,
        "occupation_name": [data["names"].get(code, code) for code in support],
        "beta_raw": beta,
        "frozen_weight": weights,
        "beta_quintile": quintile,
        "bcc_group": np.where(grouping == 2, "Q4_Q5_more_exposed", "Q1_Q3_less_exposed"),
    })
    membership.to_csv(args.output_dir / "BCC_GROUPING_MEMBERSHIP.csv", index=False)
    pd.DataFrame([controlled, unconditioned]).to_json(
        args.output_dir / "BCC_GROUPING_MODEL_RESULTS.json", orient="records", indent=2
    )
    comparisons = architecture_comparison(args, data, months)
    receipt = {
        "status": "PASS",
        "analysis_status": CORE.LABEL,
        "published_BCC_rule": "GPT-4 beta; Q4-Q5 more exposed versus Q1-Q3 less exposed",
        "not_replicated": [
            "ADP outcome and balanced-firm panel",
            "ADP proprietary title-to-SOC mapping",
            "firm-time controls and hiring/separation outcomes",
        ],
        "support_occupations": len(support),
        "quintile_cuts": cuts.tolist(),
        "high_occupation_count": int(high.sum()),
        "high_employment_share": float(weights[high].sum() / weights.sum()),
        "controlled_model": controlled,
        "unconditioned_model": unconditioned,
        "BCC_style_descriptive_CPS_growth": descriptive,
        "architecture_comparison": comparisons,
        "input_hashes": data["authenticated"]["hashes"],
    }
    (args.output_dir / "BCC_GROUPING_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    value = CORE.parser()
    value.description = __doc__
    value.add_argument(
        "--webb-ai-map", type=Path,
        default=ROOT / "yax/revision/referee_20260905/results/external/WEBB_AI_CENSUS2018_MAP.csv",
    )
    value.add_argument(
        "--oecd-ai-map", type=Path,
        default=ROOT / "yax/revision/referee_20260905/results/external/OECD_CENSUS2018_MAP.csv",
    )
    return value


if __name__ == "__main__":
    run(parser().parse_args())

#!/usr/bin/env python3
"""Run the predeclared realized-transition architecture diagnostic.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.
This is a descriptive measurement test, not a treatment-effect expansion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
ROOT = pathlib.Path(__file__).resolve().parents[3]
PLAN_COMMIT = "aed4ba518800d10b74284a7f3312e90a15b7b0d3"
MEASURES = [
    "aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
]
BOOTSTRAP_DRAWS = 999
BOOTSTRAP_SEED = 2026083121
PRIMARY_PATH = pathlib.Path(__file__).resolve().parent / "run_phase2_primary_beta_flows.py"
SPEC = importlib.util.spec_from_file_location("yax_phase2_primary_import", PRIMARY_PATH)
PRIMARY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PRIMARY
SPEC.loader.exec_module(PRIMARY)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"empty output refused: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def exposure_maps(path: pathlib.Path) -> dict[str, dict[str, float]]:
    frame = pd.read_csv(path, dtype={"occ_code": str})
    frame = frame.loc[frame.lookup_role.eq("occ2010_sensitivity_all_years")].copy()
    frame["occ_code"] = frame.occ_code.str.zfill(4)
    result = {}
    for measure in MEASURES:
        values = pd.to_numeric(frame[measure], errors="coerce")
        result[measure] = dict(zip(frame.occ_code, values))
    return result


def preperiod_occ2010_weights(path: pathlib.Path) -> dict[str, float]:
    totals: dict[str, float] = {}
    usecols = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC2010", "WTFINL", "ASECFLAG"]
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=500_000):
        month = chunk.YEAR.astype(int) * 100 + chunk.MONTH.astype(int)
        keep = (
            month.between(201701, 202211)
            & chunk.ASECFLAG.ne(1)
            & pd.to_numeric(chunk.AGE, errors="coerce").between(22, 65)
            & pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
            & pd.to_numeric(chunk.OCC2010, errors="coerce").gt(0)
            & pd.to_numeric(chunk.WTFINL, errors="coerce").gt(0)
        )
        selected = chunk.loc[keep, ["OCC2010", "WTFINL"]].copy()
        selected["occ_code"] = selected.OCC2010.astype(int).map(lambda value: f"{value:04d}")
        grouped = selected.groupby("occ_code").WTFINL.sum()
        for code, value in grouped.items():
            totals[code] = totals.get(code, 0.0) + float(value)
    return totals


def weighted_midrank(values: dict[str, float], employment: dict[str, float], support: list[str]) -> dict[str, float]:
    rows = pd.DataFrame({
        "code": support,
        "value": [values[code] for code in support],
        "weight": [employment[code] for code in support],
    }).sort_values(["value", "code"], kind="mergesort")
    grouped = rows.groupby("value", sort=True).weight.sum()
    before = grouped.cumsum() - grouped
    rank_by_value = (before + 0.5 * grouped) / grouped.sum()
    return dict(zip(rows.code, rows.value.map(rank_by_value)))


def build_switches(pairs: pd.DataFrame, maps: dict, employment: dict) -> tuple[pd.DataFrame, dict]:
    finite_sets = []
    for measure in MEASURES:
        finite_sets.append({code for code, value in maps[measure].items()
                            if np.isfinite(value) and employment.get(code, 0) > 0})
    support = sorted(set.intersection(*finite_sets))
    ranks = {measure: weighted_midrank(maps[measure], employment, support) for measure in MEASURES}
    origin_code = pairs.OCC2010.astype(int).map(lambda value: f"{value:04d}")
    dest_code = pairs.OCC2010_d.astype(int).map(lambda value: f"{value:04d}")
    base = (
        pairs.employed & pairs.employed_d & pairs.OCC2010.gt(0) & pairs.OCC2010_d.gt(0)
        & pairs.OCC2010.ne(pairs.OCC2010_d) & pairs.month.ne("2019-12")
    )
    frame = pairs.loc[base, ["CPSIDV", "month", "age_group", "LNKFW1MWT", "WTFINL",
                              "legitimate_t2", "EMPSTAT_t2", "OCC2010_t2"]].copy()
    frame["origin_code"] = origin_code.loc[frame.index]
    frame["destination_code"] = dest_code.loc[frame.index]
    before_support = len(frame)
    frame = frame.loc[frame.origin_code.isin(support) & frame.destination_code.isin(support)].copy()
    frame["young"] = frame.age_group.eq("young_22_25")
    frame["post"] = frame.month.ge("2023-01")
    frame["transition_period"] = np.where(frame.month.le("2022-11"), "pre", np.where(frame.post, "post", "transition"))
    frame["persistent"] = (
        frame.legitimate_t2 & frame.EMPSTAT_t2.isin([10, 12])
        & frame.OCC2010_t2.gt(0)
        & frame.OCC2010_t2.astype("Int64").astype(str).str.zfill(4).eq(frame.destination_code)
    )
    for measure in MEASURES:
        frame[f"dx__{measure}"] = frame.destination_code.map(maps[measure]) - frame.origin_code.map(maps[measure])
        frame[f"dr__{measure}"] = frame.destination_code.map(ranks[measure]) - frame.origin_code.map(ranks[measure])
        frame[f"sign__{measure}"] = np.sign(frame[f"dx__{measure}"]).astype(int)
    signs = frame[[f"sign__{measure}" for measure in MEASURES]].to_numpy(int)
    frame["all_six_same_direction"] = np.all(signs > 0, axis=1) | np.all(signs < 0, axis=1)
    frame["any_tie"] = np.any(signs == 0, axis=1)
    frame["opposite_direction_conflict"] = (np.min(signs, axis=1) < 0) & (np.max(signs, axis=1) > 0)
    rank_changes = frame[[f"dr__{measure}" for measure in MEASURES]].to_numpy(float)
    frame["rank_change_sd"] = np.std(rank_changes, axis=1)
    frame["rank_change_range"] = np.max(rank_changes, axis=1) - np.min(rank_changes, axis=1)
    return frame, {
        "common_OCC2010_support": len(support), "common_support_codes_sha256": hashlib.sha256("\n".join(support).encode()).hexdigest(),
        "harmonized_switches_before_six_measure_support": before_support,
        "harmonized_switches_on_six_measure_support": len(frame),
        "six_measure_support_share": len(frame) / before_support if before_support else 0,
        "support": support, "ranks": ranks,
    }


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    return float(np.average(values.to_numpy(float), weights=weights.to_numpy(float)))


def weighted_corr(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    vx = np.average((x - mx) ** 2, weights=w)
    vy = np.average((y - my) ** 2, weights=w)
    return float(cov / math.sqrt(vx * vy)) if vx > 0 and vy > 0 else float("nan")


def agreement_rows(frame: pd.DataFrame) -> list[dict]:
    rows = []
    for sample, sample_mask in [("primary", pd.Series(True, index=frame.index)),
                                ("persistent", frame.persistent)]:
        for weighting, weight_col in [("official", "LNKFW1MWT"), ("unweighted", None)]:
            for subgroup, subgroup_mask in [
                ("overall", pd.Series(True, index=frame.index)),
                ("young_pre", frame.young & frame.transition_period.eq("pre")),
                ("young_post", frame.young & frame.transition_period.eq("post")),
                ("older_pre", ~frame.young & frame.transition_period.eq("pre")),
                ("older_post", ~frame.young & frame.transition_period.eq("post")),
            ]:
                selected = frame.loc[sample_mask & subgroup_mask]
                if selected.empty:
                    continue
                weights = pd.Series(1.0, index=selected.index) if weight_col is None else selected[weight_col]
                rows.append({
                    "analysis_status": LABEL, "switch_sample": sample, "weighting": weighting,
                    "subgroup": subgroup, "switches_raw": len(selected), "weight_sum": float(weights.sum()),
                    "six_way_same_direction_rate": weighted_mean(selected.all_six_same_direction, weights),
                    "six_way_conflict_rate": weighted_mean(selected.opposite_direction_conflict, weights),
                    "any_tie_rate": weighted_mean(selected.any_tie, weights),
                    "mean_rank_change_dispersion_sd": weighted_mean(selected.rank_change_sd, weights),
                    "mean_rank_change_max_minus_min": weighted_mean(selected.rank_change_range, weights),
                })
    return rows


def pairwise_rows(frame: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    sign_rows, corr_rows = [], []
    for sample, selected in [("primary", frame), ("persistent", frame.loc[frame.persistent])]:
        for weighting, weights in [("official", selected.LNKFW1MWT.to_numpy(float)),
                                   ("unweighted", np.ones(len(selected)))]:
            for i, left in enumerate(MEASURES):
                for right in MEASURES[i + 1:]:
                    a = selected[f"sign__{left}"].to_numpy(int)
                    b = selected[f"sign__{right}"].to_numpy(int)
                    comparable = (a != 0) & (b != 0)
                    sign_rows.append({
                        "analysis_status": LABEL, "switch_sample": sample, "weighting": weighting,
                        "measure_1": left, "measure_2": right,
                        "comparable_switches_raw": int(comparable.sum()),
                        "comparable_weight": float(weights[comparable].sum()),
                        "sign_agreement_rate": float(np.average((a[comparable] == b[comparable]).astype(float), weights=weights[comparable])) if comparable.any() else "",
                    })
                    x = selected[f"dr__{left}"].to_numpy(float)
                    y = selected[f"dr__{right}"].to_numpy(float)
                    corr_rows.append({
                        "analysis_status": LABEL, "switch_sample": sample, "weighting": weighting,
                        "measure_1": left, "measure_2": right,
                        "rank_change_correlation": weighted_corr(x, y, weights),
                    })
    return sign_rows, corr_rows


def cross_sectional_conflict(support: list[str], maps: dict) -> dict:
    matrix = np.column_stack([[maps[measure][code] for code in support] for measure in MEASURES])
    conflict = 0
    pairs = 0
    for left in range(len(support)):
        signs = np.sign(matrix[left + 1:] - matrix[left])
        if len(signs) == 0:
            continue
        conflict += int(((np.min(signs, axis=1) < 0) & (np.max(signs, axis=1) > 0)).sum())
        pairs += len(signs)
    return {"unordered_occupation_pairs": pairs, "conflicting_pairs": conflict,
            "cross_sectional_conflict_rate": conflict / pairs}


def did_conflict(frame: pd.DataFrame) -> dict:
    data = frame.loc[frame.transition_period.isin(["pre", "post"])].copy()
    y = data.opposite_direction_conflict.to_numpy(float)
    young = data.young.to_numpy(float)
    post = data.post.to_numpy(float)
    x = np.column_stack([np.ones(len(data)), young, post, young * post])
    w = data.LNKFW1MWT.to_numpy(float)
    bread = np.linalg.inv(x.T @ (w[:, None] * x))
    beta = bread @ (x.T @ (w * y))
    residual = y - x @ beta
    clusters, codes = pd.factorize(data.origin_code, sort=True)
    scores = np.zeros((len(codes), x.shape[1]))
    np.add.at(scores, clusters, x * (w * residual)[:, None])
    influence = scores @ bread.T * math.sqrt(len(codes) / (len(codes) - 1))
    target = 3
    se = float(np.sqrt(np.sum(influence[:, target] ** 2)))
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(BOOTSTRAP_DRAWS, len(codes)))
    shifts = signs @ influence[:, target]
    critical = float(np.quantile(np.abs(shifts / se), 0.95, method="higher"))
    pvalue = float((1 + np.sum(np.abs(shifts / se) >= abs(beta[target] / se))) / (BOOTSTRAP_DRAWS + 1))
    cells = {}
    for age, age_mask in [("young", data.young), ("older", ~data.young)]:
        for period, period_mask in [("pre", ~data.post), ("post", data.post)]:
            selected = data.loc[age_mask & period_mask]
            cells[f"{age}_{period}"] = weighted_mean(selected.opposite_direction_conflict, selected.LNKFW1MWT)
    return {
        "estimand": "young-post DiD in realized six-architecture conflict rate",
        "coefficient": float(beta[target]), "analytic_origin_occupation_cluster_se": se,
        "wild_score_ci_lower": float(beta[target] - critical * se),
        "wild_score_ci_upper": float(beta[target] + critical * se),
        "wild_score_p_value": pvalue, "wild_score_critical": critical,
        "bootstrap_draws": BOOTSTRAP_DRAWS, "bootstrap_seed": BOOTSTRAP_SEED,
        "origin_occupation_clusters": len(codes), "cell_rates": cells,
    }


def run(args: argparse.Namespace) -> dict:
    weight_receipt = json.loads(args.weight_receipt.read_text())
    stage2a = json.loads(args.stage2a_receipt.read_text())
    if weight_receipt.get("status") != "PASS_DEFENSIBLE_CPSIDV_WITH_OFFICIAL_WEIGHT":
        raise RuntimeError("weight gate does not pass")
    if stage2a.get("classification") != "FLOW-M5" or stage2a.get("stage2B_authorized") is not False:
        raise RuntimeError("Stage-2A stop state differs from authenticated FLOW-M5 receipt")
    pairs, link = PRIMARY.load_pairs(args.microdata, args.weight_patch)
    maps = exposure_maps(args.lookup)
    employment = preperiod_occ2010_weights(args.microdata)
    switches, support = build_switches(pairs, maps, employment)
    if switches.empty:
        raise RuntimeError("no realized switches survive the declared common support")

    agreement_path = args.output_dir / "YAX_PHASE2_REALIZED_TRANSITION_AGREEMENT.csv"
    write_csv(agreement_path, agreement_rows(switches))
    sign_rows, corr_rows = pairwise_rows(switches)
    sign_path = args.output_dir / "YAX_PHASE2_PAIRWISE_SIGN_AGREEMENT.csv"
    corr_path = args.output_dir / "YAX_PHASE2_PAIRWISE_RANK_CORRELATION.csv"
    write_csv(sign_path, sign_rows)
    write_csv(corr_path, corr_rows)
    persistence_path = args.output_dir / "YAX_PHASE2_SWITCH_PERSISTENCE_SENSITIVITY.csv"
    write_csv(persistence_path, [row for row in agreement_rows(switches) if row["subgroup"] == "overall"])

    cross = cross_sectional_conflict(support["support"], maps)
    primary_official = pd.read_csv(agreement_path).query("switch_sample == 'primary' and weighting == 'official' and subgroup == 'overall'").iloc[0]
    cross["realized_official_weight_conflict_rate"] = float(primary_official.six_way_conflict_rate)
    cross["realized_minus_cross_sectional_conflict_rate"] = cross["realized_official_weight_conflict_rate"] - cross["cross_sectional_conflict_rate"]
    cross_path = args.output_dir / "YAX_PHASE2_REALIZED_VS_CROSS_SECTIONAL_DISAGREEMENT.json"
    cross_path.write_text(json.dumps(cross, indent=2) + "\n")
    did = did_conflict(switches)
    did_path = args.output_dir / "YAX_PHASE2_YOUNG_POST_ARCHITECTURE_SENSITIVITY.json"
    did_path.write_text(json.dumps(did, indent=2) + "\n")

    figure_path = args.output_dir / "figure_phase2B_pairwise_sign_agreement.png"
    figure_generated = False
    try:
        import matplotlib.pyplot as plt
        primary_sign = pd.DataFrame(sign_rows).query("switch_sample == 'primary' and weighting == 'official'")
        matrix = pd.DataFrame(np.eye(len(MEASURES)), index=MEASURES, columns=MEASURES)
        for row in primary_sign.to_dict("records"):
            matrix.loc[row["measure_1"], row["measure_2"]] = row["sign_agreement_rate"]
            matrix.loc[row["measure_2"], row["measure_1"]] = row["sign_agreement_rate"]
        fig, ax = plt.subplots(figsize=(7.2, 6.2))
        image = ax.imshow(matrix.to_numpy(float), vmin=0, vmax=1, cmap="Blues")
        ax.set_xticks(range(len(MEASURES)), MEASURES, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(MEASURES)), MEASURES, fontsize=8)
        for i in range(len(MEASURES)):
            for j in range(len(MEASURES)):
                ax.text(j, i, f"{matrix.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8,
                        color="white" if matrix.iloc[i, j] > 0.65 else "black")
        ax.set_title("Sign agreement on realized occupational transitions")
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
        fig.tight_layout()
        fig.savefig(figure_path, dpi=180)
        plt.close(fig)
        figure_generated = True
    except ModuleNotFoundError:
        pass

    outputs = [agreement_path, sign_path, corr_path, persistence_path, cross_path, did_path]
    if figure_generated:
        outputs.append(figure_path)
    receipt = {
        "record": "YAX Phase 2C realized-transition architecture receipt", "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "plan_commit": PLAN_COMMIT,
        "execution_head": PRIMARY.git("rev-parse", "HEAD"), "execution_script_sha256": sha256(pathlib.Path(__file__)),
        "input_hashes": {"microdata": sha256(args.microdata), "weight_patch": sha256(args.weight_patch),
                         "lookup": sha256(args.lookup), "weight_receipt": sha256(args.weight_receipt),
                         "stage2a_receipt": sha256(args.stage2a_receipt)},
        "link_sample": link, "support": {key: value for key, value in support.items() if key not in {"support", "ranks"}},
        "switch_definition": "adjacent CPSIDV, employed-to-employed, different valid OCC2010, excluding 2019-12 origin",
        "persistence_definition": "next legitimate adjacent observation remains employed in destination OCC2010",
        "primary_weight": "origin LNKFW1MWT", "unweighted_sensitivity": True,
        "rank_window": "2017-01 through 2022-11 ages 22-65 employed, WTFINL employment-weighted mid-CDF",
        "neutral_threshold": "exact zero only; no band", "cross_sectional_comparison": cross,
        "young_post_comparison": did, "figure_generated_in_execution_environment": figure_generated,
        "new_outcome_regressions_executed": ["realized_conflict__young_x_post__official_weight_WLS"],
        "treatment_effect_architecture_regressions_executed": [], "stage2B_executed": False,
        "long_gap_links_used": False, "excluded_analyses_executed": [],
        "outputs": {path.name: sha256(path) for path in outputs},
    }
    receipt_path = args.output_dir / "YAX_PHASE2_STAGE2C_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"support": receipt["support"], "cross": cross, "young_post": did}, indent=2))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", required=True, type=pathlib.Path)
    parser.add_argument("--weight-patch", required=True, type=pathlib.Path)
    parser.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    parser.add_argument("--weight-receipt", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent / "YAX_PHASE2_LONGITUDINAL_WEIGHT_RECEIPT.json")
    parser.add_argument("--stage2a-receipt", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent / "YAX_PHASE2_STAGE2A_RECEIPT.json")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

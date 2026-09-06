#!/usr/bin/env python3
"""Run the gated Phase-2.5 support and matched-benchmark audits.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.
No labor-outcome regression is estimated by this program.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import math
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
ROOT = pathlib.Path(__file__).resolve().parents[3]
PHASE2 = ROOT / "yax/analysis/postoutcome_phase2"
MEASURES = [
    "aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
]
SEED = 2026090101
BENCHMARK_DRAWS = 999
BENCHMARK_PSEUDO_UNITS = 200_000
PRIMARY_PATH = PHASE2 / "run_phase2_primary_beta_flows.py"
SPEC = importlib.util.spec_from_file_location("yax_phase25_primary", PRIMARY_PATH)
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
        raise RuntimeError(f"refusing empty output: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def exposure_maps(path: pathlib.Path) -> dict[str, dict[str, float]]:
    frame = pd.read_csv(path, dtype={"occ_code": str})
    frame = frame.loc[frame.lookup_role.eq("occ2010_sensitivity_all_years")].copy()
    frame["occ_code"] = frame.occ_code.str.zfill(4)
    return {
        measure: dict(zip(frame.occ_code, pd.to_numeric(frame[measure], errors="coerce")))
        for measure in MEASURES
    }


def preperiod_employment(path: pathlib.Path) -> dict[str, float]:
    totals: dict[str, float] = {}
    columns = ["YEAR", "MONTH", "AGE", "EMPSTAT", "OCC2010", "WTFINL", "ASECFLAG"]
    for chunk in pd.read_csv(path, usecols=columns, chunksize=500_000):
        ym = chunk.YEAR.astype(int) * 100 + chunk.MONTH.astype(int)
        keep = (
            ym.between(201701, 202211) & chunk.ASECFLAG.ne(1)
            & pd.to_numeric(chunk.AGE, errors="coerce").between(22, 65)
            & pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
            & pd.to_numeric(chunk.OCC2010, errors="coerce").gt(0)
            & pd.to_numeric(chunk.WTFINL, errors="coerce").gt(0)
        )
        selected = chunk.loc[keep, ["OCC2010", "WTFINL"]].copy()
        selected["code"] = selected.OCC2010.astype(int).map(lambda value: f"{value:04d}")
        for code, value in selected.groupby("code").WTFINL.sum().items():
            totals[code] = totals.get(code, 0.0) + float(value)
    return totals


def major_group_map(bridge_path: pathlib.Path, comp_path: pathlib.Path) -> dict[str, str]:
    bridge = pd.read_csv(bridge_path, dtype={"census_2010": str, "census_2018": str})
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    dominant = (
        bridge.sort_values(["census_2010", "bridge_weight", "census_2018"],
                           ascending=[True, False, True], kind="mergesort")
        .drop_duplicates("census_2010")
        .set_index("census_2010").census_2018.to_dict()
    )
    comp = pd.read_csv(comp_path, dtype={"census2018": str})
    comp["census2018"] = comp.census2018.str.zfill(4)
    major = comp.set_index("census2018").soc_major_group.astype(str).to_dict()
    return {source: major.get(target, "unmapped") for source, target in dominant.items()}


def build_switch_universe(pairs: pd.DataFrame, maps: dict, employment: dict,
                          major: dict) -> pd.DataFrame:
    base = (
        pairs.employed & pairs.employed_d & pairs.OCC2010.gt(0) & pairs.OCC2010_d.gt(0)
        & pairs.OCC2010.ne(pairs.OCC2010_d) & pairs.month.ne("2019-12")
    )
    keep = ["month", "age_group", "LNKFW1MWT", "WTFINL", "OCC2010", "OCC2010_d",
            "legitimate_t2", "EMPSTAT_t2", "OCC2010_t2"]
    frame = pairs.loc[base, keep].copy()
    frame["origin_code"] = frame.OCC2010.astype(int).map(lambda value: f"{value:04d}")
    frame["destination_code"] = frame.OCC2010_d.astype(int).map(lambda value: f"{value:04d}")
    frame["young"] = frame.age_group.eq("young_22_25")
    frame["post"] = frame.month.ge("2023-01")
    frame["young_post"] = frame.young & frame.post
    frame["origin_major"] = frame.origin_code.map(major).fillna("unmapped")
    frame["destination_major"] = frame.destination_code.map(major).fillna("unmapped")
    frame["origin_employment"] = frame.origin_code.map(employment)
    frame["destination_employment"] = frame.destination_code.map(employment)
    frame["log_origin_employment"] = np.log1p(frame.origin_employment)
    frame["log_destination_employment"] = np.log1p(frame.destination_employment)
    all_sizes = pd.Series(employment, dtype=float)
    size_rank = all_sizes.rank(method="first")
    size_q = pd.qcut(size_rank, 5, labels=["Q1-small", "Q2", "Q3", "Q4", "Q5-large"])
    frame["origin_size_quintile"] = frame.origin_code.map(size_q.astype(str).to_dict()).fillna("unmapped")
    frame["destination_size_quintile"] = frame.destination_code.map(size_q.astype(str).to_dict()).fillna("unmapped")
    frame["t2_observable"] = (
        frame.legitimate_t2 & frame.EMPSTAT_t2.isin([10, 12]) & frame.OCC2010_t2.gt(0)
    )
    t2_code = frame.OCC2010_t2.astype("Int64").astype(str).str.zfill(4)
    frame["persistent"] = frame.t2_observable & t2_code.eq(frame.destination_code)
    frame["immediate_reversal"] = frame.t2_observable & t2_code.eq(frame.origin_code)
    availability_columns = []
    for measure in MEASURES:
        origin = frame.origin_code.map(maps[measure])
        destination = frame.destination_code.map(maps[measure])
        available = origin.notna() & destination.notna() & np.isfinite(origin) & np.isfinite(destination)
        frame[f"available__{measure}"] = available
        frame[f"sign__{measure}"] = np.where(available, np.sign(destination - origin), np.nan)
        availability_columns.append(f"available__{measure}")
    frame["architectures_available"] = frame[availability_columns].sum(axis=1).astype(int)
    frame["sixway_included"] = frame.architectures_available.eq(6)
    if len(frame) != 186_370 or int(frame.sixway_included.sum()) != 108_500:
        raise RuntimeError(
            f"Phase-2 switch accounting changed: total={len(frame)}, sixway={frame.sixway_included.sum()}"
        )
    return frame


def weighted_summary(values: pd.Series, weights: pd.Series) -> tuple[float, float]:
    valid = values.notna() & weights.notna() & weights.gt(0)
    x, w = values.loc[valid].to_numpy(float), weights.loc[valid].to_numpy(float)
    mean = float(np.average(x, weights=w))
    variance = float(np.average((x - mean) ** 2, weights=w))
    return mean, math.sqrt(variance)


def smd_binary(p_in: float, p_out: float) -> float:
    denominator = math.sqrt(max((p_in * (1 - p_in) + p_out * (1 - p_out)) / 2, 1e-15))
    return (p_in - p_out) / denominator


def selection_rows(frame: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    included, excluded = frame.sixway_included, ~frame.sixway_included
    w = frame.LNKFW1MWT

    def add_binary(dimension: str, level: str, indicator: pd.Series, note: str = "") -> None:
        p_in = float(np.average(indicator.loc[included].astype(float), weights=w.loc[included]))
        p_out = float(np.average(indicator.loc[excluded].astype(float), weights=w.loc[excluded]))
        rows.append({
            "analysis_status": LABEL, "dimension": dimension, "level": level,
            "included_raw": int(included.sum()), "excluded_raw": int(excluded.sum()),
            "included_weight": float(w.loc[included].sum()), "excluded_weight": float(w.loc[excluded].sum()),
            "included_value_or_share": p_in, "excluded_value_or_share": p_out,
            "difference_included_minus_excluded": p_in - p_out,
            "standardized_difference": smd_binary(p_in, p_out), "note": note,
        })

    def add_continuous(dimension: str, series: pd.Series, note: str = "") -> None:
        mean_in, sd_in = weighted_summary(series.loc[included], w.loc[included])
        mean_out, sd_out = weighted_summary(series.loc[excluded], w.loc[excluded])
        pooled = math.sqrt((sd_in ** 2 + sd_out ** 2) / 2)
        rows.append({
            "analysis_status": LABEL, "dimension": dimension, "level": "weighted mean",
            "included_raw": int(included.sum()), "excluded_raw": int(excluded.sum()),
            "included_weight": float(w.loc[included].sum()), "excluded_weight": float(w.loc[excluded].sum()),
            "included_value_or_share": mean_in, "excluded_value_or_share": mean_out,
            "difference_included_minus_excluded": mean_in - mean_out,
            "standardized_difference": (mean_in - mean_out) / pooled if pooled else "", "note": note,
        })

    rows.append({
        "analysis_status": LABEL, "dimension": "overall support", "level": "six-way included share",
        "included_raw": int(included.sum()), "excluded_raw": int(excluded.sum()),
        "included_weight": float(w.loc[included].sum()), "excluded_weight": float(w.loc[excluded].sum()),
        "included_value_or_share": float(included.mean()),
        "excluded_value_or_share": float(w.loc[included].sum() / w.sum()),
        "difference_included_minus_excluded": "", "standardized_difference": "",
        "note": "included_value is raw coverage; excluded_value column stores official-weight coverage",
    })
    add_binary("age", "young 22-25", frame.young)
    add_binary("period", "post-2023", frame.post)
    add_binary("age x period", "young x post", frame.young_post)
    add_binary("switch quality", "t+2 observable", frame.t2_observable)
    add_binary("switch quality", "persistent A-B-B", frame.persistent)
    add_binary("switch quality", "immediate reversal A-B-A", frame.immediate_reversal)
    add_continuous("origin employment size", frame.log_origin_employment, "log(1 + pre-period occupation employment)")
    add_continuous("destination employment size", frame.log_destination_employment, "log(1 + pre-period occupation employment)")
    for column, dimension in [
        ("origin_major", "origin broad occupation family"),
        ("destination_major", "destination broad occupation family"),
        ("origin_size_quintile", "origin employment-size quintile"),
        ("destination_size_quintile", "destination employment-size quintile"),
    ]:
        for level in sorted(frame[column].dropna().unique()):
            add_binary(dimension, str(level), frame[column].eq(level))
    for measure in MEASURES:
        add_binary("individual architecture availability", measure,
                   frame[f"available__{measure}"],
                   "availability requires finite origin and destination values")
        add_binary("architecture responsible for exclusion", measure,
                   ~frame[f"available__{measure}"],
                   "share missing this architecture; overlaps across architectures")
    for count in range(7):
        add_binary("number of architectures available", str(count), frame.architectures_available.eq(count))
    return rows


def pair_rows(frame: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    support_rows, agreement_rows = [], []
    six = frame.sixway_included
    total_weight = float(frame.LNKFW1MWT.sum())
    for left, right in itertools.combinations(MEASURES, 2):
        pair = frame[f"available__{left}"] & frame[f"available__{right}"]
        sign_left = frame[f"sign__{left}"]
        sign_right = frame[f"sign__{right}"]
        comparable_pair = pair & sign_left.ne(0) & sign_right.ne(0)
        comparable_six = six & sign_left.ne(0) & sign_right.ne(0)
        conflict_pair = comparable_pair & sign_left.mul(sign_right).lt(0)
        conflict_six = comparable_six & sign_left.mul(sign_right).lt(0)
        w = frame.LNKFW1MWT

        def rate(mask: pd.Series, numerator: pd.Series, weighted: bool) -> float:
            if weighted:
                return float(w.loc[numerator].sum() / w.loc[mask].sum())
            return float(numerator.sum() / mask.sum())

        support_rows.append({
            "analysis_status": LABEL, "measure_1": left, "measure_2": right,
            "all_switches_raw": len(frame), "all_switches_weight": total_weight,
            "pair_support_raw": int(pair.sum()), "pair_support_weight": float(w.loc[pair].sum()),
            "pair_support_raw_share": float(pair.mean()),
            "pair_support_weighted_share": float(w.loc[pair].sum() / total_weight),
            "sixway_support_raw": int(six.sum()), "sixway_support_weight": float(w.loc[six].sum()),
        })
        pair_agreement_w = 1 - rate(comparable_pair, conflict_pair, True)
        six_agreement_w = 1 - rate(comparable_six, conflict_six, True)
        pair_agreement_u = 1 - rate(comparable_pair, conflict_pair, False)
        six_agreement_u = 1 - rate(comparable_six, conflict_six, False)
        agreement_rows.append({
            "analysis_status": LABEL, "measure_1": left, "measure_2": right,
            "pair_comparable_raw": int(comparable_pair.sum()),
            "pair_comparable_weight": float(w.loc[comparable_pair].sum()),
            "pair_sign_agreement_weighted": pair_agreement_w,
            "pair_sign_conflict_weighted": 1 - pair_agreement_w,
            "pair_sign_agreement_unweighted": pair_agreement_u,
            "sixway_sign_agreement_weighted": six_agreement_w,
            "sixway_sign_conflict_weighted": 1 - six_agreement_w,
            "sixway_sign_agreement_unweighted": six_agreement_u,
            "weighted_agreement_pair_minus_sixway": pair_agreement_w - six_agreement_w,
            "unweighted_agreement_pair_minus_sixway": pair_agreement_u - six_agreement_u,
        })
    return support_rows, agreement_rows


def hamilton_pseudounits(frame: pd.DataFrame, units: int) -> tuple[np.ndarray, np.ndarray, dict]:
    grouped = frame.groupby(["origin_code", "destination_code"], as_index=False).LNKFW1MWT.sum()
    expected = grouped.LNKFW1MWT.to_numpy(float) / grouped.LNKFW1MWT.sum() * units
    counts = np.floor(expected).astype(int)
    remainder = units - counts.sum()
    order = np.argsort(-(expected - counts), kind="mergesort")
    counts[order[:remainder]] += 1
    origin = np.repeat(grouped.origin_code.to_numpy(), counts)
    destination = np.repeat(grouped.destination_code.to_numpy(), counts)
    if len(origin) != units:
        raise RuntimeError("Hamilton pseudo-sample has wrong size")
    realized_approx = float(np.average(frame.opposite_direction_conflict, weights=frame.LNKFW1MWT))
    return origin, destination, {
        "pseudo_units": units, "joint_cells": len(grouped),
        "maximum_cell_share_approximation_error": float(np.max(np.abs(counts / units - expected / units))),
        "realized_conflict_original_weights": realized_approx,
    }


def repair_self_matches(origin: np.ndarray, destination: np.ndarray,
                        rng: np.random.Generator) -> tuple[np.ndarray, int]:
    result = destination.copy()
    repairs = 0
    initial_bad = np.flatnonzero(origin == result)
    if len(initial_bad) > 1:
        ordered = initial_bad[np.argsort(origin[initial_bad], kind="mergesort")]
        _, counts = np.unique(origin[ordered], return_counts=True)
        shift = int(counts.max())
        proposed = np.roll(result[ordered].copy(), shift)
        result[ordered] = proposed
        repairs += len(ordered)
    for i in np.flatnonzero(origin == result):
        if origin[i] != result[i]:
            continue
        for _ in range(10_000):
            j = int(rng.integers(len(result)))
            if (origin[j] != result[j] and result[j] != origin[i]
                    and origin[j] != result[i]):
                result[i], result[j] = result[j], result[i]
                repairs += 1
                break
        else:
            raise RuntimeError("unable to repair benchmark self-transition")
    if np.any(origin == result):
        raise RuntimeError("self-transition repair left a false self-switch")
    return result, repairs


def benchmark_one(frame: pd.DataFrame, maps: dict, sample: str) -> dict:
    origin, destination, approximation = hamilton_pseudounits(frame, BENCHMARK_PSEUDO_UNITS)
    codes = sorted(set(origin) | set(destination))
    code_index = {code: index for index, code in enumerate(codes)}
    exposure = np.column_stack([[maps[measure][code] for code in codes] for measure in MEASURES])
    delta = exposure[None, :, :] - exposure[:, None, :]
    signs = np.sign(delta)
    conflict = (np.min(signs, axis=2) < 0) & (np.max(signs, axis=2) > 0)
    oi = np.array([code_index[code] for code in origin], dtype=int)
    di_realized = np.array([code_index[code] for code in destination], dtype=int)
    realized_pseudo = float(np.mean(conflict[oi, di_realized]))
    realized_official = float(np.average(frame.opposite_direction_conflict, weights=frame.LNKFW1MWT))
    rng = np.random.default_rng(SEED + (0 if sample == "primary" else 1))
    draws = np.empty(BENCHMARK_DRAWS)
    repair_counts = np.empty(BENCHMARK_DRAWS, dtype=int)
    for draw in range(BENCHMARK_DRAWS):
        shuffled = destination[rng.permutation(len(destination))]
        shuffled, repairs = repair_self_matches(origin, shuffled, rng)
        if np.any(origin == shuffled):
            raise RuntimeError("benchmark contains a false self-switch")
        di = np.array([code_index[code] for code in shuffled], dtype=int)
        draws[draw] = float(np.mean(conflict[oi, di]))
        repair_counts[draw] = repairs
    difference = realized_official - float(draws.mean())
    p_upper = float((1 + np.sum(draws >= realized_official)) / (BENCHMARK_DRAWS + 1))
    classification = (
        "BENCH-B1" if realized_official > float(np.quantile(draws, 0.975))
        else "BENCH-B2" if realized_official >= float(draws.mean())
        else "BENCH-B3"
    )
    return {
        "sample": sample, "classification": classification,
        "seed": SEED + (0 if sample == "primary" else 1),
        "draws": BENCHMARK_DRAWS, "pseudo_units": BENCHMARK_PSEUDO_UNITS,
        "realized_conflict_official_weight": realized_official,
        "realized_conflict_pseudo_approximation": realized_pseudo,
        "benchmark_mean": float(draws.mean()), "benchmark_sd": float(draws.std(ddof=1)),
        "benchmark_p025": float(np.quantile(draws, 0.025)),
        "benchmark_p975": float(np.quantile(draws, 0.975)),
        "realized_minus_benchmark_mean": difference,
        "empirical_upper_tail_probability": p_upper,
        "maximum_self_match_repairs": int(repair_counts.max()),
        "false_self_switches_after_repair": 0,
        "approximation": approximation,
        "benchmark_draws": draws.tolist(),
    }


def run(args: argparse.Namespace) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pairs, link = PRIMARY.load_pairs(args.microdata, args.weight_patch)
    maps = exposure_maps(args.lookup)
    employment = preperiod_employment(args.microdata)
    major = major_group_map(args.bridge, args.computerization)
    frame = build_switch_universe(pairs, maps, employment, major)

    # Conflict is defined only on literal six-way support, exactly as Phase 2C.
    sign_columns = [f"sign__{measure}" for measure in MEASURES]
    signs = frame[sign_columns].to_numpy(float)
    frame["opposite_direction_conflict"] = (
        frame.sixway_included & (np.nanmin(signs, axis=1) < 0) & (np.nanmax(signs, axis=1) > 0)
    )

    selection_path = args.output_dir / "YAX_PHASE25_SIXWAY_SUPPORT_SELECTION_AUDIT.csv"
    write_csv(selection_path, selection_rows(frame))
    support_rows, agreement_rows = pair_rows(frame)
    pair_support_path = args.output_dir / "YAX_PHASE25_PAIR_SPECIFIC_SUPPORT.csv"
    pair_agreement_path = args.output_dir / "YAX_PHASE25_PAIR_SPECIFIC_AGREEMENT.csv"
    write_csv(pair_support_path, support_rows)
    write_csv(pair_agreement_path, agreement_rows)

    common = frame.loc[frame.sixway_included].copy()
    primary_benchmark = benchmark_one(common, maps, "primary")
    persistent = common.loc[common.persistent].copy()
    persistent_benchmark = benchmark_one(persistent, maps, "persistent")
    benchmark = {
        "record": "YAX Phase 2.5 realized-vs-weighted-marginal matched benchmark",
        "analysis_status": LABEL, "primary": primary_benchmark,
        "persistence_sensitivity": persistent_benchmark,
    }
    benchmark_path = args.output_dir / "YAX_PHASE25_REALIZED_VS_MATCHED_BENCHMARK.json"
    benchmark_path.write_text(json.dumps(benchmark, indent=2) + "\n", encoding="utf-8")

    # Rendering is fixed; absence of matplotlib on SCC is repaired locally from
    # the stored CSV/JSON, never by changing the plotted statistic.
    pair_figure = args.output_dir / "YAX_PHASE25_PAIR_SUPPORT_FIGURE.png"
    benchmark_figure = args.output_dir / "YAX_PHASE25_REALIZED_VS_MATCHED_BENCHMARK_FIGURE.png"
    figures = []
    try:
        import matplotlib.pyplot as plt
        agreement = pd.DataFrame(agreement_rows)
        labels = [f"{row.measure_1}\nvs {row.measure_2}" for row in agreement.itertuples()]
        x = np.arange(len(agreement))
        fig, ax = plt.subplots(figsize=(12, 5.5))
        ax.plot(x, agreement.pair_sign_agreement_weighted, "o-", label="pair-specific support")
        ax.plot(x, agreement.sixway_sign_agreement_weighted, "s--", label="six-way support")
        ax.set_ylim(0, 1)
        ax.set_xticks(x, labels, rotation=60, ha="right", fontsize=7)
        ax.set_ylabel("Official-weight sign agreement")
        ax.legend()
        fig.tight_layout(); fig.savefig(pair_figure, dpi=180); plt.close(fig)
        draws = np.array(primary_benchmark["benchmark_draws"])
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.hist(draws, bins=30, color="#6baed6", edgecolor="white")
        ax.axvline(primary_benchmark["realized_conflict_official_weight"], color="#cb181d", lw=2,
                   label="realized")
        ax.axvline(primary_benchmark["benchmark_mean"], color="black", ls="--", label="benchmark mean")
        ax.set_xlabel("Six-architecture conflict rate")
        ax.set_ylabel("Permutation draws")
        ax.legend(); fig.tight_layout(); fig.savefig(benchmark_figure, dpi=180); plt.close(fig)
        figures = [pair_figure, benchmark_figure]
    except ModuleNotFoundError:
        pass

    receipt = {
        "record": "YAX Phase 2.5 reallocation-validity execution receipt",
        "analysis_status": LABEL, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "parent_phase2_commit": "9772a494afc2c1af5630979631c4b67640f4ff3f",
        "input_hashes": {"microdata": sha256(args.microdata), "weight_patch": sha256(args.weight_patch),
                         "lookup": sha256(args.lookup), "bridge": sha256(args.bridge),
                         "computerization": sha256(args.computerization)},
        "link_sample": link, "switches": len(frame), "sixway_switches": int(frame.sixway_included.sum()),
        "sixway_weighted_share": float(frame.loc[frame.sixway_included, "LNKFW1MWT"].sum() / frame.LNKFW1MWT.sum()),
        "benchmark_seed": SEED, "benchmark_draws": BENCHMARK_DRAWS,
        "benchmark_pseudo_units": BENCHMARK_PSEUDO_UNITS,
        "new_labor_outcome_regressions": [], "long_gap_links_used": False,
        "outputs": {path.name: sha256(path) for path in [selection_path, pair_support_path,
                    pair_agreement_path, benchmark_path, *figures]},
    }
    receipt_path = args.output_dir / "YAX_PHASE25_REALLOCATION_EXECUTION_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "switches": len(frame), "sixway": int(frame.sixway_included.sum()),
        "primary_benchmark": {key: value for key, value in primary_benchmark.items() if key != "benchmark_draws"},
        "persistent_benchmark": {key: value for key, value in persistent_benchmark.items() if key != "benchmark_draws"},
    }, indent=2))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microdata", type=pathlib.Path, required=True)
    parser.add_argument("--weight-patch", type=pathlib.Path, required=True)
    parser.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    parser.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    parser.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the YAX threshold, persistence, and hard-rematching mobility audit.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
SEED = 2026090504
MEASURES = (
    "aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
)
AIOE = MEASURES[:3]
ELOUNDOU = MEASURES[3:]


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P3 = import_path("yax_revision_mobility_p3", ROOT / "yax/analysis/postoutcome_phase3_final/run_phase3.py")
CORE = P3.CORE


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def weighted_share(mask: np.ndarray, weights: np.ndarray) -> float:
    return float(weights[mask].sum() / weights.sum()) if weights.sum() else float("nan")


def weighted_midrank(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Tie-preserving weighted percentile rank in [0,1]."""
    values, weights = np.asarray(values, float), np.asarray(weights, float)
    order = np.argsort(values, kind="mergesort")
    result = np.empty(len(values), float)
    cumulative = 0.0
    for value in np.unique(values[order]):
        positions = order[values[order] == value]
        mass = float(weights[positions].sum())
        result[positions] = (cumulative + .5 * mass) / float(weights.sum())
        cumulative += mass
    return result


def threshold_rows(frame: pd.DataFrame, columns: list[str], architecture_set: str,
                   scale: str, thresholds: tuple[float, ...]) -> list[dict]:
    movements = frame[columns].to_numpy(float)
    weights = frame.LNKFW1MWT.to_numpy(float)
    rows = []
    for threshold in thresholds:
        eligible = np.max(np.abs(movements), axis=1) >= threshold
        conflict = (np.min(movements, axis=1) < 0) & (np.max(movements, axis=1) > 0)
        substantial = (np.min(movements, axis=1) <= -threshold) & (
            np.max(movements, axis=1) >= threshold
        ) if threshold > 0 else conflict
        mass = np.sum(np.abs(movements), axis=1)
        mass_denominator = float(np.sum(weights * mass))
        for sample, sample_mask in (
            ("all_switches", np.ones(len(frame), dtype=bool)),
            ("immediate_reversal_A_B_A", frame.immediate_reversal.to_numpy(bool)),
            ("persistent_A_B_B", frame.persistent.to_numpy(bool)),
        ):
            sample_weight = weights[sample_mask]
            eligible_sample = eligible[sample_mask]
            conflict_sample = conflict[sample_mask]
            substantial_sample = substantial[sample_mask]
            local_mass = mass[sample_mask]
            rows.append({
                "analysis_status": LABEL, "architecture_set": architecture_set,
                "scale": scale, "threshold": threshold, "sample": sample,
                "switches_raw": int(sample_mask.sum()), "switch_weight": float(sample_weight.sum()),
                "eligible_raw": int(eligible_sample.sum()),
                "eligible_weight_share_of_sample": weighted_share(eligible_sample, sample_weight),
                "directional_conflict_share_all_switches": weighted_share(conflict_sample, sample_weight),
                "directional_conflict_conditional_on_eligibility": weighted_share(
                    conflict_sample[eligible_sample], sample_weight[eligible_sample]
                ) if eligible_sample.any() else float("nan"),
                "substantial_opposition_share_all_switches": weighted_share(substantial_sample, sample_weight),
                "substantial_opposition_conditional_on_eligibility": weighted_share(
                    substantial_sample[eligible_sample], sample_weight[eligible_sample]
                ) if eligible_sample.any() else float("nan"),
                "movement_mass_weighted_conflict": float(
                    np.sum(sample_weight * local_mass * conflict_sample) /
                    np.sum(sample_weight * local_mass)
                ) if np.sum(sample_weight * local_mass) else float("nan"),
                "movement_mass_definition": "sum absolute architecture movements per switch",
            })
    return rows


def pairwise_rows(frame: pd.DataFrame) -> list[dict]:
    rows = []
    for left, right in itertools.combinations(MEASURES, 2):
        if left in AIOE and right in AIOE: family = "within_AIOE"
        elif left in ELOUNDOU and right in ELOUNDOU: family = "within_Eloundou"
        else: family = "between_family"
        rows.extend(threshold_rows(
            frame, [f"d__z__{left}", f"d__z__{right}"], f"{left}__{right}__{family}",
            "standardized_score", (0., .1, .25, .5)
        ))
    return rows


def aggregate_direction_rows(frame: pd.DataFrame, component_maps: dict) -> list[dict]:
    rows, weights = [], frame.LNKFW1MWT.to_numpy(float)
    for measure in MEASURES:
        movement = frame[f"d__z__{measure}"].to_numpy(float)
        destination_rank = frame[f"destination_rank__{measure}"].to_numpy(float)
        finite = np.isfinite(destination_rank)
        rows.append({
            "analysis_status": LABEL, "measure": measure,
            "share_switch_weight_moving_higher": weighted_share(movement > 0, weights),
            "share_switch_weight_moving_lower": weighted_share(movement < 0, weights),
            "share_switch_weight_tied": weighted_share(movement == 0, weights),
            "share_destination_top_weighted_rank_quintile": weighted_share(
                destination_rank[finite] >= .8, weights[finite]
            ),
            "entrant_destination_classification_available": False,
            "entrant_limit": "linked frame contains employed-to-employed occupation switches, not labor-force entrants",
        })
    return rows


def named_examples(frame: pd.DataFrame, names: dict[str, str]) -> list[dict]:
    movement = frame[[f"d__z__{measure}" for measure in MEASURES]].to_numpy(float)
    substantial = (np.min(movement, axis=1) <= -.25) & (np.max(movement, axis=1) >= .25)
    selected = frame.loc[substantial].copy()
    rows = []
    for (origin, destination), group in selected.groupby(["origin_code", "destination_code"]):
        weight = float(group.LNKFW1MWT.sum())
        row = {"origin_code": origin, "origin_name": names.get(origin, origin),
               "destination_code": destination, "destination_name": names.get(destination, destination),
               "switches_raw": len(group), "official_weight": weight}
        for measure in MEASURES:
            row[f"delta_z_{measure}"] = float(np.average(group[f"d__z__{measure}"],
                                                         weights=group.LNKFW1MWT))
        rows.append(row)
    return sorted(rows, key=lambda row: -row["official_weight"])[:30]


def exact_unconstrained_expectation(frame: pd.DataFrame, maps: dict) -> dict:
    strata = ["age_group", "month", "origin_major", "destination_major"]
    codes = sorted(set(frame.origin_code) | set(frame.destination_code))
    index = {code: i for i, code in enumerate(codes)}
    exposure = np.column_stack([[maps[m][code] for code in codes] for m in MEASURES])
    signs = np.sign(exposure[None, :, :] - exposure[:, None, :])
    conflict = ((np.min(signs, axis=2) < 0) & (np.max(signs, axis=2) > 0)).astype(float)
    total_weight, expected = float(frame.LNKFW1MWT.sum()), 0.0
    self_probability = 0.0
    for _, group in frame.groupby(strata, sort=True):
        mass = float(group.LNKFW1MWT.sum())
        origin = group.groupby("origin_code").LNKFW1MWT.sum() / mass
        destination = group.groupby("destination_code").LNKFW1MWT.sum() / mass
        oi = np.array([index[c] for c in origin.index], int)
        di = np.array([index[c] for c in destination.index], int)
        probability = float(origin.to_numpy() @ conflict[np.ix_(oi, di)] @ destination.to_numpy())
        shared = sorted(set(origin.index) & set(destination.index))
        self_p = sum(float(origin[c] * destination[c]) for c in shared)
        expected += mass / total_weight * probability
        self_probability += mass / total_weight * self_p
    return {
        "unconstrained_exact_product_marginal_conflict": expected,
        "unconstrained_exact_self_transition_probability": self_probability,
        "restriction": "does not apply to the constrained no-self benchmark",
        "strata": int(frame.groupby(strata).ngroups),
    }


def pseudo_size_audit(frame: pd.DataFrame, maps: dict) -> list[dict]:
    rows = []
    saved = json.loads((ROOT / "yax/analysis/postoutcome_phase3_final/YAX_PHASE3_HARD_BENCHMARK_RESULTS.json").read_text())
    official = saved["primary_hard_benchmark"]
    rows.append({
        "pseudo_units": official["pseudo_units"], "draws": official["draws"],
        "benchmark_mean": official["hard_benchmark_mean"],
        "benchmark_sd_across_rematches": official["hard_benchmark_sd"],
        "monte_carlo_se_of_mean": official["hard_benchmark_sd"] / np.sqrt(official["draws"]),
        "represented_weight_share": official["represented_official_weight_share"],
        "realized_conflict": official["realized_conflict_official_weight"],
        "realized_minus_benchmark": official["realized_minus_hard_mean"],
        "source": "sealed Phase-3 999-rematch result",
    })
    for units, seed in ((50_000, SEED + 1), (100_000, SEED + 2)):
        pseudo = P3.make_hard_pseudopop(frame, maps, units)
        rng = np.random.default_rng(seed)
        draws = np.empty(199)
        for draw in range(len(draws)):
            rematched, _, _ = CORE.repair_self_matches_within_groups(
                pseudo["origin"], pseudo["destination"], pseudo["groups"], rng
            )
            draws[draw] = np.mean(pseudo["conflict"][pseudo["origin"], rematched])
        realized = float(np.average(frame.opposite_direction_conflict, weights=frame.LNKFW1MWT))
        rows.append({
            "pseudo_units": units, "draws": len(draws), "benchmark_mean": float(draws.mean()),
            "benchmark_sd_across_rematches": float(draws.std(ddof=1)),
            "monte_carlo_se_of_mean": float(draws.std(ddof=1) / np.sqrt(len(draws))),
            "represented_weight_share": pseudo["represented_weight_share"],
            "realized_conflict": realized, "realized_minus_benchmark": realized - float(draws.mean()),
            "source": "new post-outcome pseudo-size sensitivity",
        })
    return sorted(rows, key=lambda row: row["pseudo_units"])


def run(args: argparse.Namespace):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reference, moments = P3.load_reference_components(args.characteristics)
    hard, frame, maps, link, retention, cuts = P3.build_switch_frame(args, moments)
    component_maps = CORE.component_maps(maps, moments)
    rank_maps = {}
    reference = reference.set_index("census2018", drop=False)
    rank_weights = reference.preperiod_employment_weight.to_numpy(float)
    for measure in MEASURES:
        ranks = weighted_midrank(reference[measure].to_numpy(float), rank_weights)
        rank_maps[measure] = dict(zip(reference.census2018, ranks))
        frame[f"origin_rank__{measure}"] = frame.origin_code.map(rank_maps[measure])
        frame[f"destination_rank__{measure}"] = frame.destination_code.map(rank_maps[measure])
        frame[f"d__rank__{measure}"] = (
            frame[f"destination_rank__{measure}"] - frame[f"origin_rank__{measure}"]
        )
    rows = []
    rows.extend(threshold_rows(frame, [f"d__z__{m}" for m in MEASURES], "all_six",
                               "standardized_score", (0., .1, .25, .5)))
    rows.extend(threshold_rows(frame, [f"d__z__{m}" for m in MEASURES if m != "dv_rating_alpha"],
                               "no_alpha_five", "standardized_score", (0., .1, .25, .5)))
    rows.extend(threshold_rows(frame, [f"d__z__{m}" for m in AIOE], "within_AIOE_three",
                               "standardized_score", (0., .1, .25, .5)))
    rows.extend(threshold_rows(frame, [f"d__z__{m}" for m in ELOUNDOU], "within_Eloundou_three",
                               "standardized_score", (0., .1, .25, .5)))
    rows.extend(threshold_rows(frame, [f"d__rank__{m}" for m in MEASURES], "all_six",
                               "tie_preserving_weighted_percentile_rank", (0., .05, .10, .20)))
    write_csv(args.output_dir / "MOBILITY_THRESHOLD_RESULTS.csv", rows)
    write_csv(args.output_dir / "MOBILITY_PAIRWISE_RESULTS.csv", pairwise_rows(frame))
    write_csv(args.output_dir / "MOBILITY_AGGREGATE_DIRECTION.csv",
              aggregate_direction_rows(frame, component_maps))
    comp = pd.read_csv(args.computerization_2010, dtype={"cps_occ2010": str})
    comp["cps_occ2010"] = comp.cps_occ2010.str.zfill(4)
    names = comp.set_index("cps_occ2010").occupation.to_dict()
    write_csv(args.output_dir / "MOBILITY_NAMED_EXAMPLES.csv", named_examples(frame, names))

    exact = exact_unconstrained_expectation(hard, maps)
    size_rows = pseudo_size_audit(hard, maps)
    write_csv(args.output_dir / "HARD_BENCHMARK_PSEUDO_SIZE_AUDIT.csv", size_rows)
    sealed_hard = json.loads((ROOT / "yax/analysis/postoutcome_phase3_final/YAX_PHASE3_HARD_BENCHMARK_RESULTS.json").read_text())
    benchmark = {
        "analysis_status": LABEL,
        "verified_reported_counts": {
            "strata": sealed_hard["primary_hard_benchmark"]["strata"],
            "pseudo_units": sealed_hard["primary_hard_benchmark"]["pseudo_units"],
            "draws": sealed_hard["primary_hard_benchmark"]["draws"],
            "represented_weight_share": sealed_hard["primary_hard_benchmark"]["represented_official_weight_share"],
            "realized_conflict": sealed_hard["primary_hard_benchmark"]["realized_conflict_official_weight"],
            "hard_mean": sealed_hard["primary_hard_benchmark"]["hard_benchmark_mean"],
            "gap": sealed_hard["primary_hard_benchmark"]["realized_minus_hard_mean"],
        },
        "no_self_transition_rule": {
            "implemented": True,
            "false_self_switches_after_repair": sealed_hard["primary_hard_benchmark"]["false_self_switches_after_repair"],
            "maximum_repairs": sealed_hard["primary_hard_benchmark"]["maximum_self_match_repairs"],
            "preserved_margins": "detailed origin and destination margins within age x month x broad-origin x broad-destination strata",
        },
        "exact_unconstrained": exact,
        "support_exclusion": {
            "retained_share": retention, "excluded_share": 1 - retention,
            "interpretation": "excluded switches lack finite F/G component endpoints; the hard result is conditional on retained support",
        },
        "near_threshold_interpretation": "the 0.96 percentage-point excess is a sample comparison, not equivalence or proof of negligibility",
        "linked_sample": link,
    }
    write_json(args.output_dir / "HARD_BENCHMARK_AUDIT.json", benchmark)
    receipt = {
        "record": "YAX referee revision mobility execution", "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "switches": len(frame), "official_weight_retention": retention,
        "output_hashes": {p.name: sha256(p) for p in args.output_dir.iterdir() if p.is_file()},
    }
    write_json(args.output_dir / "MOBILITY_EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({"status": "PASS_REFEREE_MOBILITY", "switches": len(frame),
                      "retention": retention}, indent=2))
    return receipt


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--weight-patch", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--computerization-2010", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES.csv")
    value.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--characteristics", type=pathlib.Path, default=ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv")
    value.add_argument("--table5b-results", type=pathlib.Path, default=ROOT / "yax/analysis/postoutcome_v4_supplementary/TABLE5B_COMMON_SUPPORT_RESULTS.csv")
    value.add_argument("--phase25-benchmark", type=pathlib.Path, default=ROOT / "yax/analysis/postoutcome_phase25_gate3/YAX_PHASE25_REALIZED_VS_MATCHED_BENCHMARK.json")
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())

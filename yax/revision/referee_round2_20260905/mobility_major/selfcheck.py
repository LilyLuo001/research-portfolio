#!/usr/bin/env python3
"""Self-check the aggregate RR1-M11 / RR2-M8 mobility artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib

import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(name: str):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def close(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0, abs_tol=tolerance)


def main() -> None:
    expected = {
        "FAMILY_BALANCED_PAIRWISE_DISAGREEMENT.csv",
        "FAMILY_BALANCED_DEFINITION.json",
        "TASK_ENDPOINT_IDENTITY.json",
        "HARD_SUPPORT_RECONCILIATION.json",
        "HARD_SUPPORT_CELL_SUMMARY.csv",
        "HOUSEHOLD_CLUSTER_BOOTSTRAP.json",
        "HOUSEHOLD_CLUSTER_BOOTSTRAP_DRAWS.csv",
        "REMATCH_RULE_SENSITIVITY.json",
        "REMATCH_RULE_DRAWS.csv",
        "ENTRY_DESTINATION_EVIDENCE.json",
        "CODING_INSTABILITY_DECISION.json",
        "EXECUTION_RECEIPT.json",
    }
    missing = sorted(name for name in expected if not (RESULTS / name).is_file())
    assert not missing, missing

    identity = load("TASK_ENDPOINT_IDENTITY.json")
    assert identity["maximum_absolute_raw_occupation_identity_error"] < 1e-12
    assert identity["beta_sign_violations_when_endpoints_agree"] == 0
    assert identity["beta_new_conflict_violations"] == 0

    pairs = pd.read_csv(RESULTS / "FAMILY_BALANCED_PAIRWISE_DISAGREEMENT.csv")
    for support in ("sixway_all", "hard_benchmark_represented"):
        local = pairs.loc[pairs.support.eq(support)]
        assert len(local.loc[~local.measure_1.isin(["BLOCK_AVERAGE", "FAMILY_BALANCED"])]) == 15
        blocks = local.loc[local.measure_1.eq("BLOCK_AVERAGE")]
        assert set(blocks.family_block) == {
            "within_AIOE", "within_task_share", "between_families"
        }
        balanced = local.loc[local.measure_1.eq("FAMILY_BALANCED")].iloc[0]
        assert close(
            balanced.conflict_share_all_switches,
            blocks.conflict_share_all_switches.mean(),
        )

    support = load("HARD_SUPPORT_RECONCILIATION.json")
    s = support["represented_official_weight_share"]
    assert close(s + support["omitted_official_weight_share"], 1)
    assert close(
        support["represented_support_conditional_gap"],
        support["represented_support_realized_conflict"]
        - support["represented_support_benchmark_mean"],
    )
    benchmark_bounds = support["all_support_benchmark_conflict_bounds"]
    assert close(benchmark_bounds[1] - benchmark_bounds[0], 1 - s)
    gap_bounds = support["all_support_realized_minus_benchmark_bounds"]
    assert close(gap_bounds[1] - gap_bounds[0], 1 - s)
    cells = pd.read_csv(RESULTS / "HARD_SUPPORT_CELL_SUMMARY.csv")
    assert set(cells.support) == {"represented", "omitted_by_Hamilton_rounding"}
    assert close(
        cells.loc[cells.support.eq("represented"), "official_weight"].iloc[0]
        / cells.official_weight.sum(),
        s,
    )

    rematch = load("REMATCH_RULE_SENSITIVITY.json")
    assert rematch["draws_per_rule"] == 999
    assert rematch["alternative_rule"]["uniform_over_feasible_derangements"] is False
    assert rematch["existing_rule"]["uniform_over_feasible_derangements"] is False
    assert rematch["margins_and_no_self_verified_first_five_draws"] is True
    assert len(pd.read_csv(RESULTS / "REMATCH_RULE_DRAWS.csv")) == 999

    bootstrap = load("HOUSEHOLD_CLUSTER_BOOTSTRAP.json")
    assert bootstrap["requested_draws"] == 399
    assert bootstrap["successful_draws"] >= 379
    assert bootstrap["rematches_per_bootstrap"] == 2
    assert bootstrap["pseudo_units_per_bootstrap"] == 200000
    assert len(pd.read_csv(RESULTS / "HOUSEHOLD_CLUSTER_BOOTSTRAP_DRAWS.csv")) == bootstrap["successful_draws"]
    gap = bootstrap["realized_minus_benchmark"]
    raw_var = gap["raw_cluster_bootstrap_plus_mc_se"] ** 2
    adjusted = gap["variance_subtracted_cluster_sampling_se"] ** 2
    mc_var = gap["mean_within_replicate_mc_variance_of_rematch_mean"]
    assert close(adjusted, max(raw_var - mc_var, 0), tolerance=1e-10)
    assert bootstrap["benchmark"]["sealed_mc_se_of_mean"] < bootstrap["benchmark"]["sealed_sd_across_rematches"]

    entry = load("ENTRY_DESTINATION_EVIDENCE.json")
    assert "conditional" in entry["estimand"].lower()
    assert "employment-finding" in entry["not_an_estimand"].lower()
    assert entry["wild_score_ci"][0] < 0 < entry["wild_score_ci"][1]

    coding = load("CODING_INSTABILITY_DECISION.json")
    assert coding["measured_occupation_coding_error_rate"] is None
    assert coding["stock_misclassification_curve_adopted"] is False
    assert coding["decision"] == "principled non-adoption"
    assert close(coding["earlier_phase1_universe"]["raw_conditional_share"], 0.09864639511779733)
    assert close(
        coding["immediate_reversal_share_conditional_t2_observable_raw"],
        coding["immediate_reversal_switches"] / coding["t2_observable_switches"],
    )

    forbidden = {"CPSID", "CPSIDV", "SERIAL", "PERNUM", "password", "api_key"}
    for path in RESULTS.iterdir():
        if path.suffix == ".csv":
            with path.open(newline="", encoding="utf-8") as handle:
                header = next(csv.reader(handle))
            assert not forbidden.intersection(header), (path, forbidden.intersection(header))

    receipt = load("EXECUTION_RECEIPT.json")
    assert receipt["private_identifiers_written"] is False
    for name, expected_hash in receipt["output_hashes"].items():
        assert sha256(RESULTS / name) == expected_hash, name
    assert sha256(HERE / "ANALYSIS_SPEC_BEFORE_RESULTS.md") == receipt["input_hashes"]["analysis_spec"]
    assert sha256(HERE / "TECHNICAL_CORRECTION_BEFORE_FINAL_RERUN.md") == receipt["input_hashes"]["technical_correction"]

    memo = (HERE / "MAJOR_MOBILITY_FINDINGS.md").read_text(encoding="utf-8")
    for required in (
        "200,000-unit plug-in benchmark",
        "averages two no-self rematches",
        "0.1979 pp",
        "0.0776 pp",
        "[52.8947%, 53.6591%]",
        "[0.8070 pp, 1.1113 pp]",
        "11,121 immediate A-B-A reversals among 112,736",
        "10.336% raw and 10.663%",
    ):
        assert required in memo, required
    for stale in ("0.2480 pp", "0.1185 pp", "about 69 times"):
        assert stale not in memo, stale

    print(json.dumps({
        "status": "PASS_MAJOR_MOBILITY_SELFCHECK",
        "files": len(expected),
        "bootstrap_draws": bootstrap["successful_draws"],
        "represented_share": s,
    }, indent=2))


if __name__ == "__main__":
    main()

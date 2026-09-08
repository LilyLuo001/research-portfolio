import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import json

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BATCH = load("yax_test_shortfall_batch", "run_shortfall_refit_batch.py")
CROSSFIT = load("yax_test_shortfall_crossfit", "run_shortfall_crossfit.py")
VALIDATE = load("yax_test_shortfall_validate", "validate_shortfall_outputs.py")
SUMMARIZE = load("yax_test_shortfall_summarize", "summarize_shortfall_refits.py")


def test_fit_collection_uses_q5_and_appended_control_indices(monkeypatch):
    months = ["2022-11", "2023-01"]
    arrays = {
        "months": np.asarray(months),
        "families": np.asarray(["11", "13", "15", "17", "19"]),
    }
    support = np.ones(5, bool)
    quintiles = np.arange(1, 6)
    webb = np.linspace(-1, 1, 5)
    young = np.ones((5, 2))
    older = np.ones((5, 2)) * 2
    controls = {"total": np.linspace(-1, 1, 5),
                "young_relative": np.linspace(1, -1, 5)}

    def fake_fit(_engine, _young, _total, design):
        count = design.regressors.shape[1]
        beta = np.arange(count, dtype=float)
        beta[BATCH.CORE.TARGET_INDEX] = 1.0 if design.structure == "pooled" else 3.0
        if count == 6:
            beta[-1] = .25 if design.structure == "pooled" else .75
        occ = np.zeros((5, count))
        fam = np.zeros((5, count))
        return SimpleNamespace(
            beta=beta, occupation_influence=occ, family_influence=fam,
            iterations=7, separated_observation_count=0,
        )

    monkeypatch.setattr(BATCH.CORE, "fit_with_influence", fake_fit)
    result = BATCH.fit_collection(
        young, older, arrays, support, quintiles, webb, controls)
    assert result["baseline"]["pooled"]["q5"] == 1.0
    assert result["baseline"]["family_month"]["q5"] == 3.0
    assert result["baseline"]["family_month_minus_pooled"]["q5"] == 2.0
    for control in controls:
        assert result[control]["pooled"]["shortfall_z"] == .25
        assert result[control]["family_month"]["shortfall_z"] == .75
        assert result[control]["family_month_minus_pooled"]["shortfall_z"] == .5


def test_crossfit_equal_average_and_full_sample_differences():
    template = []
    for control in CROSSFIT.CONTROLS:
        for target in CROSSFIT.TARGETS:
            template.append({
                "sample": "left", "control": control, "target": target,
                "baseline_q5": 1.0, "augmented_q5": 2.0,
                "conditioning_movement": 1.0,
                "shortfall_z_coefficient": 3.0,
                "shortfall_raw_coefficient": 4.0,
            })
    right = [{**row, "sample": "right", "baseline_q5": 3.0,
              "augmented_q5": 6.0, "conditioning_movement": 3.0,
              "shortfall_z_coefficient": 7.0,
              "shortfall_raw_coefficient": 8.0} for row in template]
    averaged = CROSSFIT.average_directions(template, right)
    assert len(averaged) == 6
    assert all(row["baseline_q5"] == 2.0 for row in averaged)
    assert all(row["conditioning_movement"] == 2.0 for row in averaged)
    assert all(row["shortfall_raw_coefficient"] == 6.0 for row in averaged)


def test_output_validator_checks_paired_and_scaling_identities():
    rows = []
    for control in VALIDATE.CONTROLS:
        bootstrap = {
            "pooled": {"q5": 1.0, "base": .5, "z": .3, "raw": .15},
            "family_month": {"q5": 1.4, "base": .7, "z": .5, "raw": .25},
        }
        observed = {
            "pooled": {"q5": .9, "base": .45, "z": .28, "raw": .14},
            "family_month": {"q5": 1.3, "base": .65, "z": .48, "raw": .24},
        }
        for collection in (bootstrap, observed):
            collection["family_month_minus_pooled"] = {
                key: collection["family_month"][key] - collection["pooled"][key]
                for key in collection["pooled"]
            }
        for target in VALIDATE.TARGETS:
            value = bootstrap[target]
            observed_value = observed[target]
            observed_q5 = observed_value["q5"]
            observed_base = observed_value["base"]
            observed_z = observed_value["z"]
            observed_raw = observed_value["raw"]
            rows.append({
                "draw": 1, "mode": "fixed_shortfalls_fixed_labels",
                "control": control, "target": target,
                "observed_q5": observed_q5, "bootstrap_q5": value["q5"],
                "q5_shift": value["q5"] - observed_q5,
                "observed_baseline_q5": observed_base,
                "bootstrap_baseline_q5": value["base"],
                "observed_conditioning_movement": observed_q5 - observed_base,
                "bootstrap_conditioning_movement": value["q5"] - value["base"],
                "conditioning_movement_shift": (
                    (value["q5"] - value["base"])
                    - (observed_q5 - observed_base)),
                "observed_shortfall_z_coefficient": observed_z,
                "bootstrap_shortfall_z_coefficient": value["z"],
                "shortfall_z_coefficient_shift": value["z"] - observed_z,
                "observed_shortfall_raw_coefficient": observed_raw,
                "bootstrap_shortfall_raw_coefficient": value["raw"],
                "shortfall_raw_coefficient_shift": value["raw"] - observed_raw,
                "shortfall_weighted_sd": 2.0,
                "support_occupations": 300,
                "occupations_reclassified": 0,
            })
    frame = pd.DataFrame(rows)
    assert VALIDATE.validate_within_draw_identities(frame) <= 1e-12


def test_shortfall_summary_and_independent_validator_agree(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    batch = run_dir / "batch_0001_0199"
    batch.mkdir(parents=True)
    rows = []
    for draw in range(1, 200):
        shift = draw / 100000.0
        for mode in SUMMARIZE.MODES:
            for control in SUMMARIZE.CONTROLS:
                observed = {
                    "pooled": {"base": .5, "q5": .6, "z": .3},
                    "family_month": {"base": .7, "q5": .8, "z": .5},
                }
                bootstrap = {
                    "pooled": {"base": .5 + shift, "q5": .6 + 1.5 * shift,
                               "z": .3 + .2 * shift},
                    "family_month": {"base": .7 + 2 * shift,
                                     "q5": .8 + 2.5 * shift,
                                     "z": .5 + .3 * shift},
                }
                for collection in (observed, bootstrap):
                    collection["family_month_minus_pooled"] = {
                        key: collection["family_month"][key] - collection["pooled"][key]
                        for key in collection["pooled"]
                    }
                for target in SUMMARIZE.TARGETS:
                    obs, boot = observed[target], bootstrap[target]
                    observed_movement = obs["q5"] - obs["base"]
                    bootstrap_movement = boot["q5"] - boot["base"]
                    rows.append({
                        "draw": draw, "mode": mode, "control": control,
                        "target": target,
                        "observed_q5": obs["q5"], "bootstrap_q5": boot["q5"],
                        "q5_shift": boot["q5"] - obs["q5"],
                        "observed_baseline_q5": obs["base"],
                        "bootstrap_baseline_q5": boot["base"],
                        "observed_conditioning_movement": observed_movement,
                        "bootstrap_conditioning_movement": bootstrap_movement,
                        "conditioning_movement_shift": bootstrap_movement - observed_movement,
                        "observed_shortfall_z_coefficient": obs["z"],
                        "bootstrap_shortfall_z_coefficient": boot["z"],
                        "shortfall_z_coefficient_shift": boot["z"] - obs["z"],
                        "observed_shortfall_raw_coefficient": obs["z"] / 2,
                        "bootstrap_shortfall_raw_coefficient": boot["z"] / 2,
                        "shortfall_raw_coefficient_shift": (boot["z"] - obs["z"]) / 2,
                        "support_occupations": 300,
                        "occupations_reclassified": 0,
                        "shortfall_weighted_mean": 0,
                        "shortfall_weighted_sd": 2,
                        "fit_iterations": 3, "baseline_iterations": 3,
                    })
    frame = pd.DataFrame(rows)
    draws_path = batch / "SHORTFALL_REFIT_DRAWS.csv"
    frame.to_csv(draws_path, index=False, lineterminator="\n")
    (batch / "MODEL_FAILURES.json").write_text("[]\n")
    (batch / "OBSERVED_CORRECTED_SHORTFALL_MODELS.csv").write_text("x\n1\n")
    (batch / "OBSERVED_CONSTRUCTION.json").write_text("{}\n")
    output_names = [
        "SHORTFALL_REFIT_DRAWS.csv", "MODEL_FAILURES.json",
        "OBSERVED_CORRECTED_SHORTFALL_MODELS.csv", "OBSERVED_CONSTRUCTION.json",
    ]
    receipt = {
        "status": "PASS_SHORTFALL_REFIT_BATCH", "start_draw": 1,
        "last_draw": 199, "requested_draws": 199,
        "successful_rows": len(frame), "failure_records": 0,
        "output_hashes": {
            name: SUMMARIZE.sha256_file(batch / name) for name in output_names
        },
    }
    (batch / "EXECUTION_RECEIPT.json").write_text(json.dumps(receipt) + "\n")
    monkeypatch.setattr(SUMMARIZE, "endpoint_monte_carlo_error",
                        lambda _values, _seed: (.001, .002))
    monkeypatch.setattr(sys, "argv", [
        "summarize_shortfall_refits.py", "--batch-root", str(run_dir),
        "--through-draw", "199", "--output-dir", str(run_dir / "summary"),
    ])
    assert SUMMARIZE.main() == 0
    summary = pd.read_csv(run_dir / "summary" / "SHORTFALL_REFIT_SUMMARY.csv")
    assert len(summary) == 18
    assert summary.failed_or_missing_draws.eq(0).all()
    monkeypatch.setattr(VALIDATE, "endpoint_error", lambda _values, _seed: (.001, .002))
    monkeypatch.setattr(sys, "argv", [
        "validate_shortfall_outputs.py", "--run-dir", str(run_dir),
    ])
    assert VALIDATE.main() == 0
    validation = json.loads(
        (run_dir / "summary" / "INDEPENDENT_VALIDATION.json").read_text())
    assert validation["status"] == "PASS_SHORTFALL_PUBLIC_OUTPUT_VALIDATION"

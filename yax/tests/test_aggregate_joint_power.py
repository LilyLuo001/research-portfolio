import importlib.util
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "power" / "aggregate_joint_power.py"
SPEC = importlib.util.spec_from_file_location("aggregate_joint_power", PATH)
A = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = A
SPEC.loader.exec_module(A)


def record(ai, comp, beta_c=A.PRIMARY_BETA_C):
    return {
        "status": "PASS_SIMULATION_COMPLETE",
        "post_outcomes_read": False,
        "ai_measure": ai,
        "computerization_measure": comp,
        "beta_c": beta_c,
        "design": {
            "post_start": "2023-01",
            "transition_excluded": "2022-12",
            "post_end": "2026-07",
            "post_gaps": ["2025-10"],
        },
        "occupation_clusters": 400,
        "empirical_mde80_relative_decline": 0.05,
        "identifying_support": {
            "weighted_partial_variance_ai_given_computerization": 0.5,
            "effective_occupations_identifying_beta_ai": 30.0,
        },
        "bootstrap": {"mde_monte_carlo_interval": {"lower": 0.04, "upper": 0.06}},
        "results": [{"true_log_effect": 0.0,
                     "rejection_probability_zero": 0.05}],
    }


def write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_build_requires_and_preserves_all_four_primary_scenarios(tmp_path):
    primary = [
        write(tmp_path, "bo.json", record("dv_rating_beta", "onet_computers_importance")),
        write(tmp_path, "bw.json", record("dv_rating_beta", "webb_pct_software")),
        write(tmp_path, "ao.json", record("dv_rating_alpha", "onet_computers_importance")),
        write(tmp_path, "aw.json", record("dv_rating_alpha", "webb_pct_software")),
    ]
    result = A.build(primary)
    assert result["post_outcomes_read"] is False
    assert len(result["scenarios"]) == 4
    assert result["bootstrap"]["draws_per_scenario"] == 999


def test_markdown_states_fitted_dgp_limits(tmp_path):
    primary = [
        write(tmp_path, "bo.json", record("dv_rating_beta", "onet_computers_importance")),
        write(tmp_path, "bw.json", record("dv_rating_beta", "webb_pct_software")),
        write(tmp_path, "ao.json", record("dv_rating_alpha", "onet_computers_importance")),
        write(tmp_path, "aw.json", record("dv_rating_alpha", "webb_pct_software")),
    ]
    text = A.markdown(A.build(primary))
    assert "Limits of the fitted-DGP" in text
    assert "not evidence" in text


def test_build_rejects_superseded_december_window(tmp_path):
    payloads = [
        record("dv_rating_beta", "onet_computers_importance"),
        record("dv_rating_beta", "webb_pct_software"),
        record("dv_rating_alpha", "onet_computers_importance"),
        record("dv_rating_alpha", "webb_pct_software"),
    ]
    payloads[0]["design"]["post_start"] = "2022-12"
    paths = [write(tmp_path, f"{index}.json", payload)
             for index, payload in enumerate(payloads)]
    try:
        A.build(paths)
    except ValueError as error:
        assert "frozen v5 post window" in str(error)
    else:
        raise AssertionError("superseded window was accepted")

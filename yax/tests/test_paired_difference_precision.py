import importlib.util
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "yax" / "power" / "build_paired_difference_precision.py"
SPEC = importlib.util.spec_from_file_location("build_paired_difference_precision", PATH)
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def _source():
    draws = [(-1 if i % 2 else 1) * (i + 1) / 100000 for i in range(999)]
    import statistics
    return {
        "post_outcomes_read": False,
        "paired_delta_distribution": draws,
        "paired_failures": 0,
        "paired_draws": 999,
        "paired_attempts": 999,
        "paired_delta_se": statistics.stdev(draws),
        "paired_covariance_beta_primary_beta_contrast": 0.00009,
        "paired_95_critical_halfwidth_log_points": 0.02,
        "mde_delta_80_log_points": 0.0327,
        "mde_delta_80_relative_magnitude": 0.0333,
        "comparison_scope": {"delta_definition": "beta - alpha"},
        "design": {},
        "inputs": {},
        "benchmark": {
            "status": "BLOCKED_NO_COMMON_SCALE_BENCHMARK",
            "required_match_dimensions": ["YAX estimand"],
            "rejected_shortcuts": {"headline": "wrong scale"},
        },
    }


def test_builder_preserves_failed_sesoi_and_adds_no_threshold(tmp_path):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(_source()), encoding="utf-8")
    result = MOD.build(source)
    assert result["status"] == "PASS_PAIRED_DIFFERENCE_PRECISION"
    assert result["post_outcomes_read"] is False
    assert result["failed_sesoi_instantiation_preserved"]["benchmark_status"] == (
        "BLOCKED_NO_COMMON_SCALE_BENCHMARK"
    )
    assert result["retired_equivalence_requirements"][
        "arbitrary_replacement_threshold_prohibited"
    ] is True
    assert result["binding_interpretation"][
        "economic_equivalence_claim_permitted"
    ] is False


def test_builder_fails_if_protected_outcomes_were_read(tmp_path):
    record = _source()
    record["post_outcomes_read"] = True
    source = tmp_path / "source.json"
    source.write_text(json.dumps(record), encoding="utf-8")
    try:
        MOD.build(source)
    except ValueError as exc:
        assert "protected" in str(exc)
    else:
        raise AssertionError("builder must fail closed on protected outcomes")

import importlib.util
import json
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "memo" / "power_calcs" / "person_level_power.py"
SPEC = importlib.util.spec_from_file_location("person_level_power", PATH)
assert SPEC and SPEC.loader
POWER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = POWER
SPEC.loader.exec_module(POWER)


def dose_fixture():
    rows = []
    months = pd.date_range("2021-11-01", "2023-05-01", freq="MS")
    for occ, decile in ((10, 1), (20, 2)):
        for number, month in enumerate(months):
            rows.append({
                "cps_occ": occ,
                "month": month.strftime("%Y-%m-%d"),
                "dax": (0.02 * number if occ == 10 else 0.01 * max(0, number - 1)),
                "industry": "A" if occ == 10 else "B",
                "static_decile": decile,
                "weight": 1.0,
            })
    return pd.DataFrame(rows)


def test_w5_contract_accepts_balanced_outcome_free_panel():
    shuffled = dose_fixture().sample(frac=1.0, random_state=20260819)
    result = POWER.validate_w5_dose_panel(shuffled)
    assert result["month_code"].min() == 202111
    assert result["month_code"].max() == 202305
    assert result.groupby("cps_occ")["month"].nunique().nunique() == 1


def test_w5_contract_rejects_outcomes_and_duplicates():
    outcome = dose_fixture()
    outcome["employment_rate"] = 0.8
    with pytest.raises(ValueError, match="outcome-like columns forbidden"):
        POWER.validate_w5_dose_panel(outcome)

    duplicate = pd.concat([dose_fixture(), dose_fixture().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="one row per occupation-month"):
        POWER.validate_w5_dose_panel(duplicate)


def test_w5_contract_rejects_unbalanced_or_pre_only_panel():
    unbalanced = dose_fixture().drop(index=0)
    with pytest.raises(ValueError, match="balanced"):
        POWER.validate_w5_dose_panel(unbalanced)

    pre_only = dose_fixture().query("month < '2023-03-01'")
    with pytest.raises(ValueError, match="post-event"):
        POWER.validate_w5_dose_panel(pre_only)


def test_extract_seal_checks_safe_columns_before_outcomes(tmp_path, monkeypatch):
    pyarrow = pytest.importorskip("pyarrow.parquet")
    path = tmp_path / "intruding.parquet"
    pd.DataFrame({
        "YEAR": [2023], "MONTH": [3], "AGE": [22],
        "EMPSTAT": [10], "UHRSWORKT": [40],
    }).to_parquet(path, index=False)
    calls = []
    original = pyarrow.read_table

    def observed_read(*args, **kwargs):
        calls.append(tuple(kwargs.get("columns") or ()))
        return original(*args, **kwargs)

    monkeypatch.setattr(pyarrow, "read_table", observed_read)
    with pytest.raises(ValueError, match="REFUSED before reading outcomes"):
        POWER.read_pre_event_extract(path)
    assert calls == [POWER.SAFE_SEAL_COLUMNS]
    assert "EMPSTAT" not in calls[0] and "UHRSWORKT" not in calls[0]


def test_reference_occupation_is_strictly_prior_and_expires():
    frame = pd.DataFrame({
        "CPSIDP": [1, 1, 1, 2],
        "YEAR": [2021, 2021, 2023, 2022],
        "MONTH": [11, 12, 4, 1],
        "OCC2010": [100, 200, 300, 400],
    })
    result = POWER.assign_reference_occupation(frame)
    assert np.isnan(result.loc[0, "reference_occ"])
    assert result.loc[1, "reference_occ"] == 100
    assert np.isnan(result.loc[2, "reference_occ"]), "16-month gap exceeds lookback"
    assert np.isnan(result.loc[3, "reference_occ"]), "first observation is never its own prior"


def test_reference_occupation_never_uses_same_month():
    frame = pd.DataFrame({
        "CPSIDP": [1, 1, 1],
        "YEAR": [2022, 2022, 2022],
        "MONTH": [1, 1, 2],
        "OCC2010": [100, 200, 300],
    })
    result = POWER.assign_reference_occupation(frame)
    assert result.loc[:1, "reference_occ"].isna().all()
    assert result.loc[2, "reference_occ"] == 200


def test_employed_missing_hours_is_not_recoded_to_zero():
    frame = pd.DataFrame({
        "CPSIDP": [1, 1, 2, 2], "YEAR": [2022] * 4,
        "MONTH": [1, 2, 1, 2], "OCC2010": [100, 100, 200, 200],
        "WTFINL": [1.0] * 4, "EMPSTAT": [10, 10, 30, 30],
        "UHRSWORKT": [40, 999, 999, 999],
    })
    result = POWER.prepare_person_records(frame)
    employed = result.loc[result["CPSIDP"] == 1, "hours_unconditional"].iloc[0]
    nonemployed = result.loc[result["CPSIDP"] == 2, "hours_unconditional"].iloc[0]
    assert np.isnan(employed)
    assert nonemployed == 0.0


def test_weighted_absorber_matches_dense_dummy_projection():
    weights = np.array([1.0, 2.0, 1.5, 0.5, 1.0, 3.0])
    first = np.array(["a", "a", "a", "b", "b", "b"])
    second = np.array(["x", "y", "x", "y", "x", "y"])
    y = np.array([1.0, 4.0, 2.0, 8.0, 3.0, 7.0])
    absorber = POWER.WeightedAbsorber([first, second], weights)
    actual = absorber.residualize(y)

    labels = pd.DataFrame({"first": first, "second": second})
    design = pd.get_dummies(labels, drop_first=True, dtype=float).to_numpy()
    design = np.column_stack([np.ones(len(y)), design])
    root = np.sqrt(weights)
    coefficient = np.linalg.lstsq(design * root[:, None], y * root, rcond=None)[0]
    expected = y - design @ coefficient
    assert actual == pytest.approx(expected, abs=1e-8)


def test_cluster_estimator_counts_occupation_clusters():
    weights = np.ones(8)
    occupation = np.array(["a"] * 4 + ["b"] * 4)
    month = np.array(["1", "2", "3", "4"] * 2)
    x = np.array([0, 1, 0, 1, 0, 0, 1, 1], dtype=float)
    absorber = POWER.WeightedAbsorber([occupation, month], weights)
    estimator = POWER.OccupationClusterEstimator(x, weights, occupation, absorber)
    fit = estimator.fit(np.array([0, 1, 0, 1, 1, 0, 2, 1], dtype=float))
    assert estimator.n_clusters == 2
    assert np.isfinite(fit.standard_error)


def test_pending_receipt_is_fail_closed(tmp_path, monkeypatch):
    standard = tmp_path / "standard.json"
    standard.write_text(json.dumps({
        "status": "PLACEHOLDER_REQUIRES_REAL_CPS",
        "benchmark": {"relative_decline": None, "version_status": "UNRESOLVED"},
    }))
    output = tmp_path / "receipt.json"
    monkeypatch.setattr(POWER, "_safe_extract_manifest", lambda _: {
        "rows": 10, "start_month": "2021-11", "end_month": "2023-02",
        "age_min": 22, "age_max": 25, "post_event_rows": 0,
    })
    receipt = POWER.emit_pending(
        tmp_path / "private.parquet", tmp_path / "missing_w5.parquet",
        output, standard, 999, 20260819,
    )
    assert receipt["status"] == "PENDING_W5_DOSE_PANEL"
    assert receipt["gate_1_pass"] is False
    assert receipt["benchmark_value"] is None
    assert receipt["post_event_outcomes_read"] is False
    assert "occupation-month cell arithmetic" in receipt["substitutes_explicitly_rejected"]


def test_no_unproved_cell_level_upper_bound_claim_remains():
    paths = [
        ROOT / "memo" / "design_memo_v1.md",
        ROOT / "memo" / "power_calcs" / "README.md",
        ROOT / "memo" / "power_calcs" / "simulate_power.py",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        assert "upper bound on the person-level mde" not in text
        assert "upper bound on the secondary design's power" not in text


def test_shipped_smoke_receipt_cannot_be_mistaken_for_gate_evidence():
    receipt = json.loads(
        (ROOT / "data_raw" / "person_level_power_engine_validation_receipt.json")
        .read_text(encoding="utf-8")
    )
    assert receipt["status"] == "ENGINE_SMOKE_PASS_NOT_GATE_EVIDENCE"
    assert receipt["gate_1_pass"] is False
    assert receipt["dose_input_is_real_w5"] is False
    assert receipt["adequately_powered"] == {
        "employment": None, "hours_unconditional": None,
    }

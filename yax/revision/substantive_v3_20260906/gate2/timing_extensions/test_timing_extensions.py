from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "yax_test_timing_extensions", HERE / "run_timing_extensions.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def observed_months():
    return [value for value in pd.period_range("2017-01", "2026-07", freq="M").astype(str)
            if value != "2025-10"]


def test_model_inventory_and_frozen_windows():
    rows = MODULE.model_definitions(observed_months())
    assert len(rows) == len({row.model_id for row in rows}) == 34
    assert sum(row.requirement == "N04" for row in rows) == 6
    assert sum(row.requirement == "T05" for row in rows) == 4
    assert sum(row.requirement == "Y08" for row in rows) == 16
    assert sum(row.requirement == "Y09" for row in rows) == 8
    assert all("2022-12" not in row.months for row in rows)
    assert all("2025-10" not in row.months for row in rows)
    late = next(row for row in rows if row.model_id == "era_2025_2026_unconditioned")
    assert "2023-01" not in late.months and "2024-12" not in late.months
    assert "2022-11" in late.months and "2025-01" in late.months


def test_pair_inventory_is_complete_and_unique():
    rows = MODULE.pair_inventory()
    assert len(rows) == 47
    assert len({row[0] for row in rows}) == len(rows)
    models = {row.model_id for row in MODULE.model_definitions(observed_months())}
    assert all(left in models and right in models for _, _, left, right in rows)


class Bundle:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeA1:
    ModelBundle = Bundle


def synthetic_cells():
    occupations = [f"{value:04d}" for value in range(1, 6)]
    months = ["2022-11", "2023-01", "2023-02"]
    rows = []
    for index, occupation in enumerate(occupations, start=1):
        for month in months:
            rows.append({
                "occ_code": occupation, "month": month,
                "family": "11" if index < 4 else "13",
                "young": 100.0 + index, "older": 300.0 + index,
                "beta_quintile": index, "webb_z": index / 10,
            })
    return pd.DataFrame(rows)


def test_bundle_builds_onset_and_both_seasonal_designs():
    cells = synthetic_cells()
    base = MODULE.ModelDefinition(
        "onset", "Y08", "onset", "family_month", "2023-02",
        tuple(sorted(cells.month.unique())))
    bundle, occupations = MODULE.make_bundle(FakeA1, cells, base)
    assert occupations == ["0001", "0002", "0003", "0004", "0005"]
    assert bundle.regressor_labels == [
        "Q2_x_post", "Q3_x_post", "Q4_x_post", "Q5_x_post", "Webb_z_x_post"]
    assert bundle.regressors.shape == (15, 5)
    assert np.all(bundle.regressors[np.asarray(bundle.frame.month) < "2023-02"] == 0)
    assert len(set(bundle.second_labels)) == 6

    quintile = MODULE.ModelDefinition(
        "season_q", "N04", "seasonality", "unconditioned", "2023-01",
        tuple(sorted(cells.month.unique())), "quintile_month_of_year")
    q_bundle, _ = MODULE.make_bundle(FakeA1, cells, quintile)
    assert q_bundle.regressors.shape == (15, 49)
    assert q_bundle.regressor_labels[-1] == "Q5_x_month_of_year_12"

    occupation = MODULE.ModelDefinition(
        "season_occ", "N04", "seasonality", "unconditioned", "2023-01",
        tuple(sorted(cells.month.unique())), "occupation_month_of_year")
    o_bundle, _ = MODULE.make_bundle(FakeA1, cells, occupation)
    assert o_bundle.regressors.shape == (15, 5)
    assert len(set(o_bundle.first_labels)) == 15


def test_paired_difference_uses_difference_influence_and_common_draws():
    rows = {"left": {"coefficient": .3}, "right": {"coefficient": .1}}
    influences = {"left": np.array([.1, .2, .3]),
                  "right": np.array([.05, .1, .15])}
    signs = np.asarray([[1, 1, 1], [-1, -1, -1], [1, -1, 1], [-1, 1, -1]], float)
    result = MODULE.paired_row("pair", "test", "left", "right", rows, influences, signs)
    expected = influences["left"] - influences["right"]
    assert np.isclose(result["coefficient_difference"], .2)
    assert np.isclose(result["paired_occupation_cluster_se"], np.sqrt(expected @ expected))
    assert result["common_occupation_draws"] is True


def test_custom_family_month_bundle_passes_full_a1_numerical_interface():
    root = HERE.parents[4]
    support_path = root / "yax/revision/substantive_v3_20260906/gate2/support_inference/run_support_inference.py"
    numerical_path = root / "yax/revision/substantive_v3_20260906/numerical_existence/run_numerical_existence_audit.py"
    support_spec = importlib.util.spec_from_file_location("yax_test_timing_support", support_path)
    support = importlib.util.module_from_spec(support_spec)
    sys.modules[support_spec.name] = support
    support_spec.loader.exec_module(support)
    analysis = MODULE.load_json(
        root / "yax/revision/substantive_v3_20260906/numerical_existence/ANALYSIS_SPEC_A1.json")
    a1 = support.load_a1(numerical_path, analysis["software"]["artifact_safety_sha256"])
    months = [f"2022-{month:02d}" for month in range(1, 7)] + [
        f"2023-{month:02d}" for month in range(1, 7)]
    rows = []
    for index in range(15):
        quintile = index // 3 + 1
        occupation = f"{index + 1:04d}"
        family = "11" if index < 8 else "13"
        webb = (index - 7) / 7
        for month_index, month in enumerate(months):
            post = month >= "2023-01"
            eta = (-.5 + (index - 7) * .04 + (month_index - 5) * .01 +
                   (quintile == 5) * post * -.08 + webb * post * .01)
            probability = 1 / (1 + np.exp(-eta))
            rows.append({
                "occ_code": occupation, "month": month, "family": family,
                "young": 10_000 * probability, "older": 10_000 * (1 - probability),
                "beta_quintile": quintile, "webb_z": webb,
            })
    definition = MODULE.ModelDefinition(
        "synthetic_timing", "Y08", "onset", "family_month", "2023-01", tuple(months))
    bundle, _ = MODULE.make_bundle(a1, pd.DataFrame(rows), definition)
    fit = support.certified_fit(a1, bundle, analysis)
    assert fit.audit["a1_certification"]["status"] == "PASS_A1_NUMERICAL_CERTIFICATE"
    assert np.isclose(fit.treatment[bundle.regressor_labels.index("Q5_x_post")], -.08,
                      rtol=0, atol=1e-6)


def test_frozen_spec_identity_and_runner_hash():
    spec = MODULE.load_json(HERE / "TIMING_EXTENSIONS_SPEC.json")
    MODULE.validate_spec(spec)

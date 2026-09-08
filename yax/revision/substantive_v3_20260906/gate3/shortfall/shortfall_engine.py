#!/usr/bin/env python3
"""Pure construction helpers for corrected pandemic-shortfall analyses."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def one_to_one_mask(occupations: np.ndarray, bridge: pd.DataFrame) -> np.ndarray:
    """Return a true target-level one-to-one Census occupation bridge mask."""
    occupations = np.asarray(occupations).astype(str)
    frame = bridge.copy()
    required = {"census_2010", "census_2018", "bridge_weight", "n_routes",
                "ambiguity_status"}
    require(required.issubset(frame.columns), "bridge schema differs")
    frame["census_2010"] = frame.census_2010.astype(str).str.zfill(4)
    frame["census_2018"] = frame.census_2018.astype(str).str.zfill(4)
    frame["bridge_weight"] = pd.to_numeric(frame.bridge_weight, errors="raise")
    frame["n_routes"] = pd.to_numeric(frame.n_routes, errors="raise").astype(int)
    source_count = frame.groupby("census_2010").size()
    target_count = frame.groupby("census_2018").size()
    eligible = frame.loc[
        frame.ambiguity_status.eq("one_to_one")
        & frame.n_routes.eq(1)
        & np.isclose(frame.bridge_weight, 1.0, rtol=0, atol=1e-12)
        & frame.census_2010.map(source_count).eq(1)
        & frame.census_2018.map(target_count).eq(1),
        "census_2018",
    ]
    return np.isin(occupations, eligible.to_numpy(str))


def corrected_shortfalls(young: np.ndarray, older: np.ndarray,
                         months: list[str]) -> dict[str, Any]:
    """Construct bounded total-stock and young-relative shortfalls."""
    young = np.asarray(young, float)
    older = np.asarray(older, float)
    require(young.shape == older.shape and young.ndim == 2,
            "shortfall cell matrices differ")
    require(young.shape[1] == len(months), "shortfall calendar differs")
    require(np.all(young >= 0) and np.all(older >= 0), "negative shortfall stock")
    pre = np.asarray(["2017-01" <= value <= "2019-12" for value in months])
    pandemic = np.asarray(["2020-01" <= value <= "2022-11" for value in months])
    require(int(pre.sum()) == 36 and int(pandemic.sum()) == 35,
            "shortfall windows differ")
    time = np.asarray([
        (int(value[:4]) - 2017) * 12 + int(value[5:7]) - 1 for value in months
    ], float)
    centered = time - float(np.mean(time[pre]))
    x_pre = np.column_stack([np.ones(int(pre.sum())), centered[pre]])
    x_all = np.column_stack([np.ones(len(months)), centered])
    total = young + older
    total_shortfall = np.full(len(young), np.nan)
    relative_shortfall = np.full(len(young), np.nan)
    pre_weight = np.sum(total[:, pre], axis=1)
    total_negative_predictions = np.zeros(len(young), int)
    share_out_of_bounds = np.zeros(len(young), int)
    positive_pre_months = np.sum(total[:, pre] > 0, axis=1)
    positive_pandemic_months = np.sum(total[:, pandemic] > 0, axis=1)
    for index in range(len(young)):
        mean_pre = float(np.mean(total[index, pre]))
        if mean_pre > 0:
            normalized = total[index] / mean_pre
            coefficient = np.linalg.lstsq(x_pre, normalized[pre], rcond=None)[0]
            raw_prediction = x_all @ coefficient
            total_negative_predictions[index] = int(np.sum(raw_prediction[pandemic] < 0))
            prediction = np.maximum(raw_prediction, 0.0)
            total_shortfall[index] = float(np.mean(
                prediction[pandemic] - normalized[pandemic]))
        valid_pre = pre & (total[index] > 0)
        valid_pandemic = pandemic & (total[index] > 0)
        if int(valid_pre.sum()) >= 24 and int(valid_pandemic.sum()) > 0:
            share = np.divide(young[index], total[index], out=np.zeros(len(months)),
                              where=total[index] > 0)
            x = np.column_stack([np.ones(int(valid_pre.sum())), centered[valid_pre]])
            root_weight = np.sqrt(total[index, valid_pre])
            coefficient = np.linalg.lstsq(
                x * root_weight[:, None], share[valid_pre] * root_weight,
                rcond=None,
            )[0]
            raw_prediction = x_all @ coefficient
            share_out_of_bounds[index] = int(np.sum(
                (raw_prediction[pandemic] < 0) | (raw_prediction[pandemic] > 1)))
            prediction = np.clip(raw_prediction, 0.0, 1.0)
            relative_shortfall[index] = float(np.average(
                prediction[valid_pandemic] - share[valid_pandemic],
                weights=total[index, valid_pandemic],
            ))
    valid = (np.isfinite(total_shortfall) & np.isfinite(relative_shortfall)
             & (positive_pre_months >= 24) & (positive_pandemic_months > 0))
    return {
        "total": total_shortfall, "young_relative": relative_shortfall,
        "pre_weight": pre_weight, "finite_support": valid,
        "positive_pre_months": positive_pre_months,
        "positive_pandemic_months": positive_pandemic_months,
        "total_negative_predictions_before_bound": total_negative_predictions,
        "share_out_of_bounds_predictions_before_bound": share_out_of_bounds,
    }


def weighted_standardize(values: np.ndarray, weights: np.ndarray,
                         support: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    support = np.asarray(support, bool)
    require(values.shape == weights.shape == support.shape,
            "shortfall standardization arrays differ")
    require(np.all(np.isfinite(values[support])) and np.all(weights[support] > 0),
            "invalid shortfall standardization support")
    mean = float(np.average(values[support], weights=weights[support]))
    sd = float(np.sqrt(np.average((values[support] - mean) ** 2,
                                  weights=weights[support])))
    require(np.isfinite(sd) and sd > 0, "shortfall standardization collapses")
    z = np.full(len(values), np.nan)
    z[support] = (values[support] - mean) / sd
    return z, {"weighted_mean": mean, "weighted_sd": sd,
               "standardization_weight": float(weights[support].sum())}


def subset_cells(matrix: np.ndarray, support: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, float)
    support = np.asarray(support, bool)
    require(matrix.ndim == 2 and matrix.shape[0] == len(support),
            "shortfall cell subset differs")
    return matrix[support].reshape(-1)


def augment_design(core: Any, base: Any, control_z: np.ndarray,
                   months: list[str], label: str) -> Any:
    control_z = np.asarray(control_z, float)
    n_occ = len(base.occupation_codes) // len(months)
    require(control_z.shape == (n_occ,), "shortfall control support differs")
    post = np.asarray([value >= "2023-01" for value in months], float)
    column = np.repeat(control_z, len(months)) * np.tile(post, n_occ)
    return replace(
        base,
        regressors=np.column_stack([base.regressors, column]),
        regressor_labels=tuple(base.regressor_labels) + (f"{label}_z_x_post",),
    )

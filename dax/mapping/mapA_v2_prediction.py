"""Prospectively frozen Mapping A v2 binary prediction procedure.

This module is deliberately label-file agnostic.  It exposes deterministic
feature construction, development-only model selection, calibration-only
Platt scaling, and the signed constrained cutoff rule.  It has no locked-test
reader and no downstream-data inputs.
"""

from __future__ import annotations

import dataclasses
import math
from collections import defaultdict
from collections.abc import Iterable, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler


PREDICTION_SEED = 20260821
EXPECTED_GDPVAL_TASKS = 220
RRF_CONSTANT = 60
CV_FOLDS = 5
C_GRID = (0.01, 0.1, 1.0, 10.0, 100.0)
SOLVER = "liblinear"
TOLERANCE = 1e-8
MAX_ITERATIONS = 5000
CLASS_WEIGHT = "balanced"
PLATT_SOLVER = "lbfgs"
PLATT_C = 1_000_000.0
PLATT_TOLERANCE = 1e-12
PLATT_MAX_ITERATIONS = 5000
PPV_FLOOR = 0.95
FPR_CEILING = 0.05

FEATURE_NAMES = (
    "dense_cosine_similarity",
    "dense_rank_percentile",
    "bm25_score_log1p",
    "lexical_rank_percentile",
    "reciprocal_rank_fusion_k60",
    "absolute_rank_gap_percentile",
    "signed_dense_minus_lexical_rank_gap_percentile",
    "both_channels_top10",
    "both_channels_top40",
    "either_channel_top40",
)


@dataclasses.dataclass(frozen=True)
class RetrievalPair:
    onet_task_id: str
    gdpval_task_id: str
    dense_score: float
    lexical_score: float


@dataclasses.dataclass(frozen=True)
class CutoffResult:
    cutoff: float
    ppv: float
    false_positive_rate: float
    recall: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int


def _ranks(rows: Sequence[RetrievalPair], field: str) -> dict[str, int]:
    return {
        row.gdpval_task_id: index
        for index, row in enumerate(
            sorted(rows, key=lambda item: (-float(getattr(item, field)), item.gdpval_task_id)),
            start=1,
        )
    }


def build_feature_rows(
    rows: Iterable[RetrievalPair],
    selected_pairs: Iterable[tuple[str, str]],
    *,
    expected_gdpval_tasks: int = EXPECTED_GDPVAL_TASKS,
) -> tuple[np.ndarray, list[tuple[str, str]]]:
    """Construct the exact frozen feature vector for requested task pairs.

    Missing or non-finite scores are hard failures; there is no imputation.
    BM25 is transformed with log1p.  Ranks are deterministic (GDPval ID breaks
    score ties), and percentiles are (rank - 1) / (N - 1).  Features are later
    standardized with development-only means and population standard deviations.
    """
    if expected_gdpval_tasks < 2:
        raise ValueError("expected GDPval universe must contain at least two tasks")
    grouped: dict[str, list[RetrievalPair]] = defaultdict(list)
    for row in rows:
        if not row.onet_task_id or not row.gdpval_task_id:
            raise ValueError("task IDs must be non-empty")
        if not math.isfinite(row.dense_score) or not math.isfinite(row.lexical_score):
            raise ValueError("retrieval features must be finite; imputation is forbidden")
        if not 0.0 <= row.dense_score <= 1.0:
            raise ValueError("frozen dense cosine input must be clipped to [0, 1]")
        if row.lexical_score < 0.0:
            raise ValueError("BM25 score must be non-negative")
        grouped[row.onet_task_id].append(row)

    selected = sorted(set(selected_pairs))
    if not selected:
        raise ValueError("selected pair list must not be empty")
    output: list[list[float]] = []
    order: list[tuple[str, str]] = []
    denominator = expected_gdpval_tasks - 1
    for onet_id, gdpval_id in selected:
        task_rows = grouped.get(onet_id, [])
        ids = [row.gdpval_task_id for row in task_rows]
        if len(task_rows) != expected_gdpval_tasks or len(ids) != len(set(ids)):
            raise ValueError(f"incomplete or duplicate retrieval universe for {onet_id}")
        by_id = {row.gdpval_task_id: row for row in task_rows}
        if gdpval_id not in by_id:
            raise ValueError(f"selected GDPval task absent for {onet_id}")
        dense_ranks = _ranks(task_rows, "dense_score")
        lexical_ranks = _ranks(task_rows, "lexical_score")
        row = by_id[gdpval_id]
        dense_rank = dense_ranks[gdpval_id]
        lexical_rank = lexical_ranks[gdpval_id]
        dense_percentile = (dense_rank - 1) / denominator
        lexical_percentile = (lexical_rank - 1) / denominator
        output.append(
            [
                row.dense_score,
                dense_percentile,
                math.log1p(row.lexical_score),
                lexical_percentile,
                1.0 / (RRF_CONSTANT + dense_rank) + 1.0 / (RRF_CONSTANT + lexical_rank),
                abs(dense_rank - lexical_rank) / denominator,
                (dense_rank - lexical_rank) / denominator,
                float(dense_rank <= 10 and lexical_rank <= 10),
                float(dense_rank <= 40 and lexical_rank <= 40),
                float(dense_rank <= 40 or lexical_rank <= 40),
            ]
        )
        order.append((onet_id, gdpval_id))
    matrix = np.asarray(output, dtype=np.float64)
    if matrix.shape != (len(order), len(FEATURE_NAMES)) or not np.isfinite(matrix).all():
        raise AssertionError("frozen feature matrix invariant failed")
    return matrix, order


def _binary_labels(labels: Sequence[str]) -> np.ndarray:
    normalized = [str(value).strip().upper() for value in labels]
    invalid = sorted(set(normalized) - {"D", "F", "N", "U"})
    if invalid:
        raise ValueError(f"invalid D/F/N/U labels: {invalid}")
    return np.asarray([1 if value == "D" else 0 for value in normalized], dtype=np.int8)


def select_and_fit_development_model(
    features: np.ndarray,
    relation_labels: Sequence[str],
) -> tuple[StandardScaler, LogisticRegression, dict[str, object]]:
    """Select C by mean 5-fold development PR-AUC, then refit on all dev.

    Every fold fits its own scaler.  Exact-score ties select the smallest C
    (strongest regularization), prospectively and without locked data.
    """
    x = np.asarray(features, dtype=np.float64)
    y = _binary_labels(relation_labels)
    if x.ndim != 2 or x.shape != (len(y), len(FEATURE_NAMES)):
        raise ValueError("development feature shape mismatch")
    if not np.isfinite(x).all() or len(np.unique(y)) != 2:
        raise ValueError("development data require finite features and both classes")
    class_counts = np.bincount(y, minlength=2)
    if int(class_counts.min()) < CV_FOLDS:
        raise ValueError("each development class needs at least five examples")

    splitter = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=PREDICTION_SEED)
    candidate_results: list[dict[str, object]] = []
    for c_value in C_GRID:
        fold_scores = []
        for train_index, validation_index in splitter.split(x, y):
            scaler = StandardScaler(with_mean=True, with_std=True)
            train_x = scaler.fit_transform(x[train_index])
            validation_x = scaler.transform(x[validation_index])
            model = LogisticRegression(
                penalty="l2",
                C=c_value,
                solver=SOLVER,
                tol=TOLERANCE,
                max_iter=MAX_ITERATIONS,
                class_weight=CLASS_WEIGHT,
                random_state=PREDICTION_SEED,
                fit_intercept=True,
            )
            model.fit(train_x, y[train_index])
            fold_scores.append(float(average_precision_score(y[validation_index], model.predict_proba(validation_x)[:, 1])))
        candidate_results.append(
            {"C": c_value, "fold_pr_auc": fold_scores, "mean_pr_auc": float(np.mean(fold_scores))}
        )
    selected = max(candidate_results, key=lambda result: (result["mean_pr_auc"], -result["C"]))

    final_scaler = StandardScaler(with_mean=True, with_std=True)
    scaled = final_scaler.fit_transform(x)
    final_model = LogisticRegression(
        penalty="l2",
        C=float(selected["C"]),
        solver=SOLVER,
        tol=TOLERANCE,
        max_iter=MAX_ITERATIONS,
        class_weight=CLASS_WEIGHT,
        random_state=PREDICTION_SEED,
        fit_intercept=True,
    )
    final_model.fit(scaled, y)
    receipt = {
        "criterion": "maximum mean development five-fold PR-AUC",
        "tie_break": "smallest_C_strongest_regularization",
        "candidate_results": candidate_results,
        "selected_C": float(selected["C"]),
    }
    return final_scaler, final_model, receipt


def fit_platt_calibrator(
    development_scaler: StandardScaler,
    development_model: LogisticRegression,
    calibration_features: np.ndarray,
    relation_labels: Sequence[str],
) -> LogisticRegression:
    """Fit the frozen one-variable sigmoid on calibration only."""
    x = np.asarray(calibration_features, dtype=np.float64)
    y = _binary_labels(relation_labels)
    if x.ndim != 2 or x.shape != (len(y), len(FEATURE_NAMES)):
        raise ValueError("calibration feature shape mismatch")
    if not np.isfinite(x).all() or len(np.unique(y)) != 2:
        raise ValueError("calibration data require finite features and both classes")
    decision = development_model.decision_function(development_scaler.transform(x)).reshape(-1, 1)
    calibrator = LogisticRegression(
        penalty="l2",
        C=PLATT_C,
        solver=PLATT_SOLVER,
        tol=PLATT_TOLERANCE,
        max_iter=PLATT_MAX_ITERATIONS,
        class_weight=None,
        random_state=PREDICTION_SEED,
        fit_intercept=True,
    )
    calibrator.fit(decision, y)
    return calibrator


def calibrated_probabilities(
    development_scaler: StandardScaler,
    development_model: LogisticRegression,
    calibrator: LogisticRegression,
    features: np.ndarray,
) -> np.ndarray:
    x = np.asarray(features, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != len(FEATURE_NAMES) or not np.isfinite(x).all():
        raise ValueError("prediction feature shape or finiteness failure")
    decision = development_model.decision_function(development_scaler.transform(x)).reshape(-1, 1)
    return calibrator.predict_proba(decision)[:, 1]


def select_calibration_cutoff(
    probabilities: Sequence[float],
    relation_labels: Sequence[str],
    *,
    ppv_floor: float = PPV_FLOOR,
    fpr_ceiling: float = FPR_CEILING,
) -> CutoffResult:
    """Apply the signed PPV/FPR constraints and maximum-recall rule.

    Candidate cutoffs are the distinct observed calibration probabilities and
    predictions use p >= cutoff.  Recall ties select higher PPV, then lower
    FPR, then the higher (more conservative) cutoff.  No feasible cutoff is a
    hard ``MAPPING_A_V2_CALIBRATION_FAIL``.
    """
    probability = np.asarray(probabilities, dtype=np.float64)
    y = _binary_labels(relation_labels)
    if probability.ndim != 1 or len(probability) != len(y) or not np.isfinite(probability).all():
        raise ValueError("calibration probabilities are invalid")
    if np.any((probability < 0) | (probability > 1)) or len(np.unique(y)) != 2:
        raise ValueError("calibration probabilities require [0,1] and both classes")
    if not 0 <= ppv_floor <= 1 or not 0 <= fpr_ceiling <= 1:
        raise ValueError("cutoff constraints must lie in [0,1]")

    feasible: list[CutoffResult] = []
    for cutoff in sorted(set(float(value) for value in probability), reverse=True):
        predicted = probability >= cutoff
        tp = int(np.sum(predicted & (y == 1)))
        fp = int(np.sum(predicted & (y == 0)))
        tn = int(np.sum(~predicted & (y == 0)))
        fn = int(np.sum(~predicted & (y == 1)))
        ppv = tp / (tp + fp)
        fpr = fp / (fp + tn)
        recall = tp / (tp + fn)
        result = CutoffResult(cutoff, ppv, fpr, recall, tp, fp, tn, fn)
        if ppv >= ppv_floor and fpr <= fpr_ceiling:
            feasible.append(result)
    if not feasible:
        raise RuntimeError("MAPPING_A_V2_CALIBRATION_FAIL")
    return max(feasible, key=lambda result: (result.recall, result.ppv, -result.false_positive_rate, result.cutoff))


def frozen_algorithm_specification() -> dict[str, object]:
    """Return a JSON-serializable prospective specification."""
    return {
        "target": "D_vs_non_D_where_non_D_is_F_N_or_U",
        "feature_names_in_order": list(FEATURE_NAMES),
        "feature_rules": {
            "dense_cosine_similarity": "frozen clipped score in [0,1]",
            "rank_ties": "ascending_gdpval_task_id",
            "rank_percentile": "(rank-1)/(220-1)",
            "bm25_score_log1p": "natural_log(1+nonnegative_BM25)",
            "rrf": "1/(60+dense_rank)+1/(60+lexical_rank)",
            "rank_gaps": "absolute and signed dense-minus-lexical ranks divided by 219",
            "agreement": "both_top10, both_top40, either_top40 indicators",
            "missing_values": "hard_fail_no_imputation",
            "normalization": "StandardScaler fit on development training data only; fold-local inside CV",
        },
        "model": {
            "family": "sklearn.linear_model.LogisticRegression",
            "penalty": "l2",
            "solver": SOLVER,
            "tolerance": TOLERANCE,
            "max_iterations": MAX_ITERATIONS,
            "class_weight": CLASS_WEIGHT,
            "fit_intercept": True,
            "C_grid": list(C_GRID),
        },
        "development_selection": {
            "folds": CV_FOLDS,
            "stratified": True,
            "shuffle": True,
            "seed": PREDICTION_SEED,
            "criterion": "mean_PR_AUC",
            "tie_break": "smallest_C",
        },
        "calibration": {
            "method": "sigmoid_Platt_logistic_on_development_decision_score",
            "partition": "calibration_only",
            "solver": PLATT_SOLVER,
            "C": PLATT_C,
            "tolerance": PLATT_TOLERANCE,
            "max_iterations": PLATT_MAX_ITERATIONS,
            "class_weight": None,
        },
        "cutoff": {
            "candidates": "distinct_observed_calibration_probabilities",
            "prediction": "probability_greater_than_or_equal_to_cutoff",
            "constraints": {"PPV_min": PPV_FLOOR, "FPR_max": FPR_CEILING},
            "objective": "maximum_recall",
            "tie_break_in_order": ["higher_PPV", "lower_FPR", "higher_cutoff"],
            "no_feasible_cutoff": "MAPPING_A_V2_CALIBRATION_FAIL",
        },
    }

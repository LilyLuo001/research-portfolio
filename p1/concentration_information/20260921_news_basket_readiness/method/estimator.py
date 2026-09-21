"""Bounded, synthetic-only estimator interfaces for the proposed V2 method.

No function here reads prices, news, holdings, or metadata.  The caller must pass
already-authorized, prevalidated inputs.  Parameters and the standardization
target are PROPOSED_NOT_FROZEN; this is not production inference.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import sqrt
from typing import Any, Mapping, Sequence

import numpy as np


class InputRejected(ValueError):
    """Raised when a required design guard is absent or invalid."""


PROPOSED_LABEL = "PROPOSED_NOT_FROZEN"


def _array(value: Any, name: str, ndim: int | None = None) -> np.ndarray:
    a = np.asarray(value, dtype=float)
    if (ndim is not None and a.ndim != ndim) or not np.all(np.isfinite(a)):
        raise InputRejected(f"{name} must be finite" + (f" and {ndim}-D" if ndim else ""))
    return a


def _symmetric_psd(covariance: Any, size: int, name: str = "covariance") -> np.ndarray:
    cov = _array(covariance, name, 2)
    if cov.shape != (size, size):
        raise InputRejected(f"{name} must have shape {(size, size)}")
    if not np.allclose(cov, cov.T, atol=1e-10, rtol=1e-10):
        raise InputRejected(f"{name} must be symmetric")
    if np.linalg.eigvalsh(cov).min() < -1e-10:
        raise InputRejected(f"{name} must be positive semidefinite")
    return (cov + cov.T) / 2


@dataclass(frozen=True)
class PairedQuote:
    """One already-aligned quote side at anchor, h, and H.

    ``valid_*`` means a live two-sided quote state, even if unchanged; it does
    not mean a trade occurred.  Timestamps are intervals, so fine ordering is
    rejected when their uncertainty overlaps.
    """
    anchor: float
    horizon: float
    terminal: float
    valid_anchor: bool
    valid_horizon: bool
    valid_terminal: bool
    anchor_interval: tuple[float, float]
    horizon_interval: tuple[float, float]
    terminal_interval: tuple[float, float]


def _interval_ok(interval: tuple[float, float], name: str) -> None:
    if len(interval) != 2 or not all(np.isfinite(interval)) or interval[0] > interval[1]:
        raise InputRejected(f"{name} must be a finite ordered interval")


def paired_response(etf: PairedQuote, basket: PairedQuote, *, actual_basket: bool,
                    basket_kind: str, quote_side: str) -> dict[str, float | str]:
    """Return paired cumulative simple responses; reject proxy/invalid clocks.

    The actual basket is supplied by the caller and cannot be silently replaced
    by an index, PCF, or a proxy.  This is a guard, not a holdings constructor.
    """
    if not actual_basket or basket_kind != "ACTUAL_HOLDINGS":
        raise InputRejected("actual pre-event holdings basket is required; proxy rejected")
    if quote_side not in {"bid", "ask", "mid"}:
        raise InputRejected("quote_side must be bid, ask, or mid")
    for label, quote in (("etf", etf), ("basket", basket)):
        if not (quote.valid_anchor and quote.valid_horizon and quote.valid_terminal):
            raise InputRejected(f"{label} has invalid/cancelled/stale quote state")
        for n, interval in (("anchor", quote.anchor_interval), ("horizon", quote.horizon_interval),
                            ("terminal", quote.terminal_interval)):
            _interval_ok(interval, f"{label}.{n}_interval")
        if not all(np.isfinite(v) and v > 0 for v in (quote.anchor, quote.horizon, quote.terminal)):
            raise InputRejected(f"{label} anchor, horizon, and terminal quote values must be finite and positive")
        # At the intended scale, chronology has to be identified, not guessed.
        if quote.anchor_interval[1] > quote.horizon_interval[0] or quote.horizon_interval[1] > quote.terminal_interval[0]:
            raise InputRejected(f"{label} clock ordering unresolved at requested horizon")
    if (etf.anchor_interval != basket.anchor_interval or etf.horizon_interval != basket.horizon_interval
            or etf.terminal_interval != basket.terminal_interval):
        raise InputRejected("ETF and basket require identical evaluation-time uncertainty intervals at anchor, h, and H")
    return {
        "etf_h": etf.horizon / etf.anchor - 1.0,
        "basket_h": basket.horizon / basket.anchor - 1.0,
        "etf_H": etf.terminal / etf.anchor - 1.0,
        "basket_H": basket.terminal / basket.anchor - 1.0,
        "quote_side": quote_side,
    }


def fixed_common_support_weights(rows: Sequence[Mapping[str, Any]], *, fstar_cells: Sequence[Any],
                                 groups: Sequence[Any], issuer_weights: Mapping[tuple[Any, Any], Mapping[Any, float]],
                                 event_etf_weights: Mapping[tuple[Any, Any, Any], Mapping[Any, float]],
                                 cell_weights: Mapping[Any, float] | None = None) -> np.ndarray:
    """Make proposed fixed-F* weights with issuer, not event-frequency, mass.

    Required row keys are ``cell``, ``group``, ``issuer_id``, ``event_id``, and
    ``etf_id``.  ``event_etf_weights`` is a predeclared mapping keyed by
    (cell, group, event_id); its ETF weights sum to one *within the repeated
    event* before issuer weights are applied.  Thus no response averaging is
    invented: each ETF--basket paired observation remains a row and same-news
    rows are later clustered by event ID.
    Every proposed F* cell must support every group.  Within a (cell, group,
    issuer), that issuer's predeclared mass is divided equally across its events;
    hence each cell/group total is one before fixed cell mass is applied.  This
    prevents a prolific issuer from obtaining extra weight solely by event count.
    The resulting records sum to one.  It estimates a *conditional weighted
    linear projection*, not an issuer-average speed or an information share.
    """
    if not rows or not fstar_cells or not groups:
        raise InputRejected("nonempty rows, F* cells, and groups are required")
    cell_set, group_set = set(fstar_cells), set(groups)
    if len(cell_set) != len(fstar_cells) or len(group_set) != 1:
        raise InputRejected("one explicitly selected group and unique F* cells are required; TOP/REST pooling is prohibited")
    buckets: dict[tuple[Any, Any, Any], list[int]] = defaultdict(list)
    seen_event_etf = set()
    for j, row in enumerate(rows):
        try:
            key = (row["cell"], row["group"], row["issuer_id"])
            event_key = (row["cell"], row["group"], row["event_id"], row["etf_id"])
        except KeyError as exc:
            raise InputRejected(f"missing required row key {exc.args[0]}") from exc
        if key[0] not in cell_set or key[1] not in group_set:
            raise InputRejected("row outside declared fixed common support")
        if event_key in seen_event_etf:
            raise InputRejected("duplicate cell/group/event_id/etf_id row")
        seen_event_etf.add(event_key)
        buckets[key].append(j)
    weights = np.zeros(len(rows))
    raw_cell = cell_weights or {c: 1.0 for c in fstar_cells}
    if set(raw_cell) != cell_set or any(not np.isfinite(v) or v <= 0 for v in raw_cell.values()):
        raise InputRejected("cell_weights must be positive for exactly F* cells")
    cell_total = sum(raw_cell.values())
    for cell in fstar_cells:
        for group in groups:
            declared = issuer_weights.get((cell, group))
            if not declared or any(not np.isfinite(v) or v <= 0 for v in declared.values()):
                raise InputRejected("positive predeclared issuer weights required in every F* cell/group")
            if not np.isclose(sum(declared.values()), 1.0):
                raise InputRejected("issuer weights must sum to one within cell/group")
            observed = {issuer for c, g, issuer in buckets if c == cell and g == group}
            if observed != set(declared):
                raise InputRejected("common support failure: observed issuers differ from fixed issuer target")
            for issuer, issuer_mass in declared.items():
                idx = buckets[(cell, group, issuer)]
                event_rows: dict[Any, list[int]] = defaultdict(list)
                for j in idx:
                    event_rows[rows[j]["event_id"]].append(j)
                for event_id, event_idx in event_rows.items():
                    declared_etf = event_etf_weights.get((cell, group, event_id))
                    observed_etf = {rows[j]["etf_id"] for j in event_idx}
                    if not declared_etf or set(declared_etf) != observed_etf or any(
                            not np.isfinite(v) or v <= 0 for v in declared_etf.values()) or not np.isclose(sum(declared_etf.values()), 1.0):
                        raise InputRejected("positive predeclared ETF weights summing to one required within each event")
                    for j in event_idx:
                        weights[j] = ((raw_cell[cell] / cell_total) * issuer_mass / len(event_rows)
                                      * declared_etf[rows[j]["etf_id"]])
    if not np.isclose(weights.sum(), 1.0):
        raise AssertionError("internal fixed-support normalization failure")
    return weights


def _cluster_slope_covariance(design: np.ndarray, residuals: np.ndarray, clusters: Sequence[Any],
                              slope_positions: Sequence[int]) -> np.ndarray:
    """Cluster sandwich covariance for all requested slope/outcome coefficients."""
    inv = np.linalg.inv(design.T @ design)
    size = len(slope_positions) * residuals.shape[1]
    scores: dict[Any, np.ndarray] = defaultdict(lambda: np.zeros(size))
    for row, residual, cluster in zip(design, residuals, clusters):
        leverage = inv @ row
        scores[cluster] += np.concatenate([leverage[position] * residual for position in slope_positions])
    if len(scores) < 2:
        raise InputRejected("at least two event clusters required")
    meat = sum(np.outer(score, score) for score in scores.values())
    # Small-sample multiplier is illustrative only; no real issuer/date correction.
    return meat * len(scores) / (len(scores) - 1)


def fit_joint_standardized_slopes(x: Any, responses: Any, weights: Any, event_ids: Sequence[Any], *,
                                  cell_ids: Sequence[Any], fstar_cells: Sequence[Any],
                                  standardization_cell_weights: Mapping[Any, float],
                                  covariance_mode: str = "EVENT_CLUSTER_SYNTHETIC_ONLY") -> dict[str, Any]:
    """Fit cell-specific slopes, then linearly apply declared fixed F* weights.

    Response columns are ETF-h, basket-h, ETF-H, basket-H. Same-news ETF rows
    remain rows and are clustered by event ID. This block design is necessary:
    a pooled x regression would reweight F* cells by their within-cell x squared.
    Issuer/date multiway covariance and overlap calibration remain unimplemented.
    """
    x, y, w = _array(x, "x", 1), _array(responses, "responses", 2), _array(weights, "weights", 1)
    if y.shape != (len(x), 4) or len(w) != len(x) or len(event_ids) != len(x) or len(cell_ids) != len(x):
        raise InputRejected("responses, weights, event IDs, and cells must share n")
    if np.any(w <= 0) or not np.isclose(w.sum(), 1.0):
        raise InputRejected("weights must be positive and sum to one")
    if len(set(event_ids)) == len(event_ids):
        raise InputRejected("this interface is for repeated event dependence; no repeated event IDs supplied")
    if covariance_mode != "EVENT_CLUSTER_SYNTHETIC_ONLY":
        raise InputRejected("only EVENT_CLUSTER_SYNTHETIC_ONLY is implemented")
    cells = tuple(fstar_cells)
    if not cells or len(set(cells)) != len(cells) or set(cell_ids) != set(cells):
        raise InputRejected("each and only declared F* cells must have observations")
    if set(standardization_cell_weights) != set(cells) or any(
            not np.isfinite(v) or v <= 0 for v in standardization_cell_weights.values()) or not np.isclose(sum(standardization_cell_weights.values()), 1.0):
        raise InputRejected("positive fixed cell weights summing to one are required")
    raw_design = np.zeros((len(x), 2 * len(cells)))
    for k, cell in enumerate(cells):
        mask = np.asarray([value == cell for value in cell_ids])
        raw_design[mask, 2*k] = 1.
        raw_design[mask, 2*k+1] = x[mask]
    design = raw_design * np.sqrt(w)[:, None]
    wy = y * np.sqrt(w)[:, None]
    if np.linalg.matrix_rank(design) < 2 * len(cells):
        raise InputRejected("each F* cell needs usable x variation")
    beta = np.linalg.solve(design.T @ design, design.T @ wy)
    residual = wy - design @ beta
    cell_covariance = _symmetric_psd(_cluster_slope_covariance(design, residual, event_ids,
                                                                 [2*k+1 for k in range(len(cells))]),
                                     4 * len(cells), "estimated cell-specific joint covariance")
    standardizer = np.zeros((4, 4 * len(cells)))
    for k, cell in enumerate(cells):
        standardizer[:, 4*k:4*k+4] = np.eye(4) * standardization_cell_weights[cell]
    slopes = sum(standardization_cell_weights[cell] * beta[2*k+1] for k, cell in enumerate(cells))
    covariance = _symmetric_psd(standardizer @ cell_covariance @ standardizer.T, 4,
                                "standardized joint covariance")
    transform = np.array([[1., -1., 0., 0.], [0., 0., .5, .5]])
    nd_cov = transform @ covariance @ transform.T
    return {"slopes": slopes.tolist(), "joint_covariance": covariance.tolist(),
            "cell_specific_slopes": {str(cell): beta[2*k+1].tolist() for k, cell in enumerate(cells)},
            "cell_specific_joint_covariance": cell_covariance.tolist(),
            "early_difference": float((transform @ slopes)[0]),
            "terminal_response": float((transform @ slopes)[1]),
            "nd_covariance": nd_cov.tolist(), "covariance_mode": covariance_mode,
            "dependence_status": "EVENT_CLUSTER_ONLY;_ISSUER_DATE_MULTIWAY_NOT_IMPLEMENTED",
            "estimand": "FIXED_FSTAR_CELL_SPECIFIC_CONDITIONAL_WEIGHTED_LINEAR_PROJECTION"}


def fieller_set(numerator: float, denominator: float, covariance: Any, *, critical: float = 1.96) -> dict[str, Any]:
    """Invert the joint ratio test, retaining empty and unbounded confidence sets."""
    n, d = float(numerator), float(denominator)
    if not np.isfinite(n) or not np.isfinite(d) or not np.isfinite(critical) or critical <= 0:
        raise InputRejected("finite numerator, denominator, and positive critical required")
    cov = _symmetric_psd(covariance, 2)
    c2 = critical * critical
    a, b, c = d*d-c2*cov[1, 1], -2*n*d+2*c2*cov[0, 1], n*n-c2*cov[0, 0]
    disc = b*b-4*a*c
    if abs(a) < 1e-14:
        if abs(b) < 1e-14:
            return {"kind": "ALL_REAL" if c <= 0 else "EMPTY"}
        return {"kind": "HALF_LINE", "boundary": float(-c/b), "direction": "LE" if b > 0 else "GE"}
    if disc < 0:
        return {"kind": "ALL_REAL" if a < 0 else "EMPTY"}
    roots = sorted(((-b-sqrt(disc))/(2*a), (-b+sqrt(disc))/(2*a)))
    return {"kind": "BOUNDED" if a > 0 else "TWO_UNBOUNDED_RAYS", "boundaries": roots}


def ratio_contrast_confidence_set(*_: Any, **__: Any) -> dict[str, str]:
    """Honest placeholder: no subtraction of marginal Fieller intervals is valid."""
    return {"status": "NOT_IMPLEMENTED", "reason": "Requires validated joint four-coefficient test inversion; marginal ratio confidence sets are not subtracted.", "grid_search": "NOT_USED_MAY_MISS_UNBOUNDED_TAILS"}


def composition_decomposition(p0: Any, p1: Any, d0: Any, d1: Any) -> dict[str, float]:
    """Symmetric accounting decomposition, rejecting absent support or invalid weights."""
    p0, p1, d0, d1 = (_array(v, name, 1) for v, name in ((p0, "p0"), (p1, "p1"), (d0, "d0"), (d1, "d1")))
    if not (len(p0) == len(p1) == len(d0) == len(d1)) or np.any(p0 < 0) or np.any(p1 < 0):
        raise InputRejected("aligned supported groups and nonnegative weights required")
    if not np.isclose(p0.sum(), 1) or not np.isclose(p1.sum(), 1):
        raise InputRejected("composition weights must each sum to one")
    within = np.dot((p1+p0)/2, d1-d0)
    composition = np.dot((d1+d0)/2, p1-p0)
    return {"total_change": float(np.dot(p1, d1)-np.dot(p0, d0)),
            "within_response_change": float(within), "composition_change": float(composition)}

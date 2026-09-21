#!/usr/bin/env python3
"""Frozen estimand and support checks; contains no data-source reads."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

H1_X_MEAN = -7.120058696390034
H1_X_SD = 1.575275281258204
TERMS = ["x_std", "same_sic2", "x_same", "log_size", "log_liquidity"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_frozen_terms(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if (out["pair_strength"] <= 0).any():
        raise ValueError("pair_strength must be observed and positive; missing is not zero")
    out["x_std"] = (np.log(out["pair_strength"]) - H1_X_MEAN) / H1_X_SD
    out["x_same"] = out["x_std"] * out["same_sic2"]
    return out


def analysis_rows(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["outcome", "event_id", "block_id", "issuer_id", "receiver_id", "pair_strength",
                "same_sic2", "log_size", "log_liquidity"]
    missing = [c for c in required if c not in frame]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    use = add_frozen_terms(frame).dropna(subset=["outcome"] + TERMS).copy()
    n = use.groupby("event_id")["receiver_id"].transform("size")
    use["weight"] = 1.0 / n
    for c in ["outcome"] + TERMS:
        mean = use.groupby("event_id")[c].transform(lambda z: np.average(z, weights=use.loc[z.index, "weight"]))
        use[c + "_w"] = use[c] - mean
    return use


def design_diagnostics(frame: pd.DataFrame) -> dict:
    use = analysis_rows(frame.assign(outcome=0.0) if "outcome" not in frame else frame)
    if use.empty:
        return {
            "rows": 0, "issuer_events": 0, "calendar_blocks": 0,
            "design_rank": 0, "design_columns": len(TERMS),
            "blocks_by_same_sic2": {"0": 0, "1": 0},
            "duplicate_event_receiver_keys": 0,
            "max_block_weight_share": None, "leave_one_block_ranks": {},
        }
    X = use[[c + "_w" for c in TERMS]].to_numpy(float)
    rank = int(np.linalg.matrix_rank(X))
    blocks = sorted(use.block_id.unique())
    block_weight = use.groupby("block_id").weight.sum()
    group_blocks = {}
    for s in (0, 1):
        g = use[use.same_sic2 == s]
        varying = (g.groupby(["block_id", "event_id"])["x_std"]
                   .agg(lambda z: bool(len(z) >= 2 and np.ptp(z.to_numpy(float)) > 1e-12)))
        group_blocks[str(s)] = int(varying[varying].reset_index().block_id.nunique())
    loo_ranks = {}
    for b in blocks:
        g = use[use.block_id != b]
        loo_ranks[str(b)] = int(np.linalg.matrix_rank(g[[c + "_w" for c in TERMS]].to_numpy(float)))
    return {
        "rows": int(len(use)), "issuer_events": int(use.event_id.nunique()),
        "calendar_blocks": int(len(blocks)), "design_rank": rank, "design_columns": len(TERMS),
        "blocks_by_same_sic2": group_blocks,
        "duplicate_event_receiver_keys": int(use.duplicated(["event_id", "receiver_id"]).sum()),
        "max_block_weight_share": float(block_weight.max() / block_weight.sum()) if len(block_weight) else None,
        "leave_one_block_ranks": loo_ranks,
    }


def support_gate(diagnostics: dict, calendar_reuse_count: int, minimum_controls: int) -> tuple[bool, list[str]]:
    reasons = []
    if diagnostics["calendar_blocks"] < 8:
        reasons.append("fewer_than_8_disjoint_calendar_blocks")
    if min(diagnostics["blocks_by_same_sic2"].get("0", 0), diagnostics["blocks_by_same_sic2"].get("1", 0)) < 6:
        reasons.append("either_industry_group_in_fewer_than_6_blocks")
    if diagnostics["max_block_weight_share"] is None or diagnostics["max_block_weight_share"] > .25 + 1e-12:
        reasons.append("calendar_block_exceeds_25pct_weight")
    if diagnostics["design_rank"] < diagnostics["design_columns"]:
        reasons.append("main_design_not_full_rank")
    if diagnostics.get("duplicate_event_receiver_keys", 0) != 0:
        reasons.append("duplicate_event_receiver_design_keys")
    if any(r < diagnostics["design_columns"] for r in diagnostics["leave_one_block_ranks"].values()):
        reasons.append("leave_one_block_design_not_full_rank")
    if calendar_reuse_count != 0:
        reasons.append("calendar_dates_reused_across_blocks")
    if minimum_controls < 2:
        reasons.append("receiver_event_with_fewer_than_2_controls")
    return not reasons, reasons


def fit_primary(frame: pd.DataFrame) -> dict:
    use = analysis_rows(frame)
    X = use[[c + "_w" for c in TERMS]].to_numpy(float)
    y = use["outcome_w"].to_numpy(float)
    w = use.weight.to_numpy(float)
    xtwx = X.T @ (w[:, None] * X)
    if np.linalg.matrix_rank(xtwx) != len(TERMS):
        raise ValueError("rank-deficient primary design")
    bread = np.linalg.inv(xtwx)
    beta = bread @ (X.T @ (w * y))
    resid = y - X @ beta
    scores = []
    for _, g in use.assign(_row=np.arange(len(use))).groupby("block_id"):
        ix = g._row.to_numpy(int)
        scores.append(X[ix].T @ (w[ix] * resid[ix]))
    scores = np.vstack(scores)
    G, N, K = len(scores), len(use), len(TERMS)
    # Within-event absorption is algebraically equivalent to including one
    # intercept for every event (and no global intercept), so those dimensions
    # count in the CR1 residual-degrees correction even though they are not in X.
    K_full = K + int(use.event_id.nunique())
    if G < 2 or N <= K_full:
        raise ValueError("insufficient clusters or residual degrees of freedom")
    factor = (G / (G - 1)) * ((N - 1) / (N - K_full))
    cov = bread @ (factor * scores.T @ scores) @ bread
    names = TERMS
    coef = dict(zip(names, beta))
    x_i, int_i = names.index("x_std"), names.index("x_same")
    same_slope = beta[x_i] + beta[int_i]
    same_var = cov[x_i, x_i] + cov[int_i, int_i] + 2 * cov[x_i, int_i]
    return {
        "coefficients": {k: float(v) for k, v in coef.items()},
        "covariance": {a: {b: float(cov[i, j]) for j, b in enumerate(names)} for i, a in enumerate(names)},
        "same_industry_slope": float(same_slope),
        "same_industry_slope_se": float(np.sqrt(max(0.0, same_var))),
        "same_minus_other_slope": float(beta[int_i]),
        "same_minus_other_slope_se": float(np.sqrt(max(0.0, cov[int_i, int_i]))),
        "rows": N, "issuer_events": int(use.event_id.nunique()), "calendar_blocks": G,
        "cluster_df": G - 1, "cr1_k_full_including_event_fixed_effects": K_full,
    }


def verify_opening_gate(stage: Path, metadata_paths: list[Path]) -> dict:
    gate_path = stage / "PREOUTCOME_REVIEW.json"
    if not gate_path.is_file():
        raise PermissionError("PREOUTCOME_REVIEW.json absent: H2 responses must remain unread")
    gate = json.loads(gate_path.read_text())
    if gate.get("status") != "PASS_OPEN_RESULTS":
        raise PermissionError("independent pre-outcome status is not PASS_OPEN_RESULTS")
    expected = gate.get("bound_sha256", {})
    core = ["analysis_config.json", "SPECIFICATION.md", "replication_statistics.py",
            "build_replication_response.py", "run_frozen_estimation.py"]
    targets = [stage / name for name in core] + metadata_paths
    if len({p.name for p in targets}) != len(targets):
        raise PermissionError("bound filenames must be unique because the gate manifest is basename-keyed")
    absent = [str(p) for p in targets if not p.is_file()]
    if absent:
        raise PermissionError(f"bound pre-outcome files absent: {absent}")
    actual = {p.name: sha256(p) for p in targets}
    if actual != expected:
        raise PermissionError(f"pre-outcome hashes changed: expected {expected}, got {actual}")
    return gate

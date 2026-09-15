#!/usr/bin/env python3
"""Outcome-sealed P1 exposure diagnostics and generic development fixture.

This module deliberately permits only the three frozen exposure metadata CSVs.
It never discovers, opens, or infers earnings, surprise, calendar, quote, CAR,
or other outcome files. ``power_results.csv`` is a
``GENERIC_POOLED_CONTINUOUS_ORACLE_FIXTURE / DEVELOPMENT_FIXTURE``: it is not
candidate A/B/C, equal-wave, stock×wave, the full estimator, empirical power,
an empirical MDE, or a selection among unresolved estimands.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

RUN_DATE = "2026-09-13"
SEED = 20260913
HORIZONS = ("5m", "15m", "30m", "60m", "close", "+1d")
TERMINAL = len(HORIZONS) - 1
ALLOWED_FILENAMES = {
    "exposure_stock_wave_all.csv",
    "exposure_stock_wave_dimensional_only.csv",
    "exposure_stock_wave_ex_dimensional.csv",
}
CANONICAL_EXPOSURE_ROOT = Path("/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure")
EXPECTED_EXPOSURE_SHA256 = {
    "exposure_stock_wave_all.csv": "905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320",
    "exposure_stock_wave_dimensional_only.csv": "c4acb697f4d8e2a13168deca58187ebfc9bcfcc73b086c77ed6cd6b925044967",
    "exposure_stock_wave_ex_dimensional.csv": "383ea34668d74efcaf1da771dfa2e994960a7e56c2d28f99d829639ad259a9ba",
}
PROTECTED_DESIGN_ROOT = Path("/Users/lilyluo/research-portfolio-p1-protected-readonly")
REQUIRED_ACTUAL_DESIGN_COMPONENTS = (
    "calendar", "announcement_times", "sue", "forecast_actual", "controls", "stack_membership",
    "weights", "session_horizon_masks", "economic_sponsor_crosswalk", "covariance_calibration",
)
FORBIDDEN_PATH_TOKENS = ("earn", "sue", "quote", "return", "car", "irr", "vecm", "refraction", "outcome")


class SealedInputError(ValueError):
    """Attempt to use data beyond explicitly permitted exposure metadata."""


class MissingRequiredInputError(RuntimeError):
    """Raised if someone requests an empirical design without protected inputs."""


class RankFailure(RuntimeError):
    """A required design column is unidentified; it must not be silently dropped."""


@dataclass(frozen=True)
class Cell:
    permno: str
    wave: str
    effective: str
    exposure: float
    adviser_proxy: str
    dimensional: bool
    pre_report_max: str


@dataclass
class FWLFit:
    beta_operator: np.ndarray  # p by n; maps unweighted y to coefficients
    a: np.ndarray              # Zr'Zr
    rank_x0: int
    rank_full: int
    leverage: np.ndarray


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def assert_safe_metadata_path(path: Path, *, fixture_only: bool = False) -> None:
    """Validate canonical detached input and hash before CSV parsing.

    ``fixture_only`` exists solely for isolated tests and must never be exposed
    by the production CLI path.
    """
    lower = str(path).lower()
    if path.name not in ALLOWED_FILENAMES or any(t in lower for t in FORBIDDEN_PATH_TOKENS):
        raise SealedInputError(f"FORBIDDEN_PATH_DENIED: {path}")
    if fixture_only:
        return
    resolved = path.resolve()
    expected = (CANONICAL_EXPOSURE_ROOT / path.name).resolve()
    if resolved != expected:
        raise SealedInputError(f"CANONICAL_EXPOSURE_ROOT_GUARD: {path}")
    observed_hash = _sha256(path)
    if observed_hash != EXPECTED_EXPOSURE_SHA256[path.name]:
        raise SealedInputError(f"EXPOSURE_HASH_GUARD: {path.name}")


def _truth(v: str) -> bool:
    return str(v).strip().lower() == "true"


def load_cells(path: Path, as_of: str = RUN_DATE, *, fixture_only: bool = False) -> list[Cell]:
    assert_safe_metadata_path(path, fixture_only=fixture_only)
    out: list[Cell] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for line, row in enumerate(csv.DictReader(fh), start=2):
            try:
                ownership = float(row.get("exposure_ownership") or 0)
            except ValueError as exc:
                raise SealedInputError(f"OWNERSHIP_PARSE_GUARD line={line}") from exc
            if not 0 <= ownership <= 1:
                raise SealedInputError(f"OWNERSHIP_UNIT_RANGE_GUARD line={line}")
            if not (_truth(row.get("primary_ready", "")) and ownership > 0):
                continue
            required = ("permno", "wave_id", "effective_date", "advisers", "pre_report_date_max")
            if any(not str(row.get(k, "")).strip() for k in required):
                raise SealedInputError(f"BLANK_KEY_GUARD line={line}")
            if row["effective_date"] > as_of:
                raise SealedInputError(f"FUTURE_EFFECTIVE_DATE_GUARD line={line}")
            if row["pre_report_date_max"] >= row["effective_date"]:
                raise SealedInputError(f"LEAKAGE_GUARD line={line}")
            out.append(Cell(str(row["permno"]).strip(), str(row["wave_id"]).strip(), row["effective_date"],
                            ownership, str(row["advisers"]).strip(),
                            _truth(row.get("is_dimensional", "")), row["pre_report_date_max"]))
    if not out:
        raise SealedInputError("No primary-ready positive-exposure metadata cells")
    return out


def validate_pre_announcement_eligibility(cells: Iterable[Cell], announcement_by_wave: dict[str, str] | None) -> None:
    """Block absent anticipation mapping; reject holdings reported after announcement.

    This is intentionally not run on the current exposure support because the
    authorized metadata has no complete earliest-announcement mapping.
    """
    cells = list(cells)
    if not announcement_by_wave:
        raise MissingRequiredInputError("PRE_ANNOUNCEMENT_ELIGIBILITY_BLOCK: announcement mapping is NOT_AVAILABLE")
    missing = sorted({c.wave for c in cells if not announcement_by_wave.get(c.wave)})
    if missing:
        raise MissingRequiredInputError("PRE_ANNOUNCEMENT_ELIGIBILITY_BLOCK: missing waves=" + ",".join(missing))
    offenders = [c.wave for c in cells if c.pre_report_max > announcement_by_wave[c.wave]]
    if offenders:
        raise SealedInputError("PRE_ANNOUNCEMENT_LEAKAGE_GUARD: " + ",".join(sorted(set(offenders))))


def _counts(cells: Iterable[Cell]) -> dict[str, float]:
    x = list(cells)
    exposures = np.asarray([c.exposure for c in x], dtype=float)
    n = len(x)
    by_stock: dict[str, int] = {}
    by_wave: dict[str, int] = {}
    by_proxy: dict[str, int] = {}
    for c in x:
        by_stock[c.permno] = by_stock.get(c.permno, 0) + 1
        by_wave[c.wave] = by_wave.get(c.wave, 0) + 1
        by_proxy[c.adviser_proxy] = by_proxy.get(c.adviser_proxy, 0) + 1
    top_proxy = max(by_proxy.values()) / n
    top_wave = max(by_wave.values()) / n
    hhi_proxy = sum((v / n) ** 2 for v in by_proxy.values())
    proxy_exposure: dict[str, float] = {}
    wave_exposure: dict[str, float] = {}
    for c in x:
        proxy_exposure[c.adviser_proxy] = proxy_exposure.get(c.adviser_proxy, 0.) + c.exposure
        wave_exposure[c.wave] = wave_exposure.get(c.wave, 0.) + c.exposure
    exposure_total = sum(proxy_exposure.values())
    return {
        "cells": n, "stocks": len(by_stock), "waves": len(by_wave),
        "repeat_stocks": sum(v > 1 for v in by_stock.values()), "max_stock_waves": max(by_stock.values()),
        "ge_0_5pct_cells": int((exposures >= 0.005).sum()),
        "ge_0_5pct_stocks": len({c.permno for c in x if c.exposure >= 0.005}),
        "ge_0_5pct_waves": len({c.wave for c in x if c.exposure >= 0.005}),
        "top_adviser_proxy_cell_share": top_proxy, "adviser_proxy_hhi": hhi_proxy,
        "top_wave_cell_share": top_wave, "adviser_proxy_count": len(by_proxy),
        "top_adviser_proxy_exposure_share": max(proxy_exposure.values()) / exposure_total,
        "adviser_proxy_exposure_hhi": sum((v / exposure_total) ** 2 for v in proxy_exposure.values()),
        "top_wave_exposure_share": max(wave_exposure.values()) / exposure_total,
    }


def measured_support_rows(arms: dict[str, list[Cell]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for arm, cells in arms.items():
        for metric, value in _counts(cells).items():
            rows.append({"record_type": "MEASURED_EXPOSURE_SUPPORT", "arm": arm, "metric": metric,
                         "value": value, "status": "MEASURED_NOW", "basis": "primary_ready positive ownership exposure",
                         "limitation": "adviser is an unsigned proxy, not an economic sponsor"})
        all_waves = sorted({c.wave for c in cells})
        all_proxy = sorted({c.adviser_proxy for c in cells})
        for w in all_waves:
            after = [c for c in cells if c.wave != w]
            q = _counts(after) if after else {"cells": 0, "stocks": 0, "waves": 0, "ge_0_5pct_cells": 0}
            for metric in ("cells", "stocks", "waves", "ge_0_5pct_cells"):
                rows.append({"record_type": "LEAVE_ONE_WAVE_MEASURED", "arm": arm, "metric": metric,
                             "value": q[metric], "excluded_unit": w, "status": "MEASURED_NOW",
                             "basis": "exposure metadata only", "limitation": "not earnings-event support"})
        for proxy in all_proxy:
            after = [c for c in cells if c.adviser_proxy != proxy]
            q = _counts(after) if after else {"cells": 0, "stocks": 0, "waves": 0, "ge_0_5pct_cells": 0}
            for metric in ("cells", "stocks", "waves", "ge_0_5pct_cells"):
                rows.append({"record_type": "LEAVE_ONE_ADVISER_PROXY_MEASURED", "arm": arm, "metric": metric,
                             "value": q[metric], "excluded_unit": proxy, "status": "MEASURED_NOW",
                             "basis": "exposure metadata only", "limitation": "NOT an economic-sponsor LOSO"})
    unavailable = [
        "actual_earnings_event_count", "actual_session_support", "actual_horizon_complete_mask",
        "actual_sue_post_interaction", "actual_nuisance_residualized_design", "actual_estimator_information",
        "actual_contrast_leverage_and_information_concentration", "actual_outcome_covariance", "empirical_mde",
    ]
    for metric in unavailable:
        rows.append({"record_type": "ACTUAL_DESIGN_REQUIREMENT", "arm": "ALL", "metric": metric, "value": "",
                     "status": "NOT_AVAILABLE", "basis": "not present in authorized metadata",
                     "limitation": "outcome-sealed: no earnings/calendar/SUE/quote/control/mask input was opened"})
    rows.append({"record_type": "INVALIDATED_LEGACY_STATISTIC", "arm": "ALL", "metric": "old_design_stats_raw_exposure_ess_mde",
                 "value": "", "status": "INVALID_ESTIMATOR_NONINVARIANT", "basis": "legacy raw x^2 / imposed variance shares",
                 "limitation": "missing SUE, Post, nuisance residualization, actual masks and covariance; not empirical power"})
    return rows


def actual_power_unavailable_rows() -> list[dict[str, object]]:
    """Keep non-executed research estimators out of generic-fixture output."""
    rows: list[dict[str, object]] = []
    for candidate in ("candidate_A_high_mid_vs_low", "candidate_B_tiers_vs_zero", "candidate_C_continuous"):
        for metric in ("complete_estimator_power", "mde80", "mde90", "timing_equivalence", "boottest_size_coverage"):
            rows.append({"record_type": "ACTUAL_CANDIDATE_POWER_REQUIREMENT", "scenario": candidate, "metric": metric,
                         "horizon": "", "estimate": "", "mc_ci_low": "", "mc_ci_high": "", "reps": "",
                         "status": "NOT_AVAILABLE", "dependence": "NOT_AVAILABLE",
                         "timing_classification": "NOT_ESTIMABLE: contract/design/covariance/margin unavailable",
                         "limitation": "No actual complete estimator, empirical MDE, equivalence, or boottest execution."})
    return rows


def require_actual_design_inputs(paths: dict[str, Path | None]) -> None:
    expected = set(REQUIRED_ACTUAL_DESIGN_COMPONENTS)
    supplied = set(paths)
    missing = sorted(expected - supplied | {name for name in expected if paths.get(name) is None})
    unexpected = sorted(supplied - expected)
    if missing or unexpected:
        raise MissingRequiredInputError("MISSING_REQUIRED_INPUT_BLOCK: missing=" + ",".join(missing) +
                                        " unexpected=" + ",".join(unexpected))
    for name in REQUIRED_ACTUAL_DESIGN_COMPONENTS:
        path = paths[name]
        assert path is not None
        expected_path = (PROTECTED_DESIGN_ROOT / f"{name}.csv").resolve()
        if path.resolve() != expected_path or not path.exists():
            raise MissingRequiredInputError(f"PROTECTED_VIEW_GUARD: {name}")


def require_signed_economic_sponsors(sponsor_crosswalk: Path | None, *, fixture_only: bool = False) -> None:
    """Validate a signed crosswalk; a path's existence is never sufficient."""
    if sponsor_crosswalk is None or not sponsor_crosswalk.exists():
        raise MissingRequiredInputError("SPONSOR_GUARD: signed economic-sponsor crosswalk is NOT_AVAILABLE")
    if not fixture_only and sponsor_crosswalk.resolve() != (PROTECTED_DESIGN_ROOT / "economic_sponsor_crosswalk.csv").resolve():
        raise MissingRequiredInputError("SPONSOR_GUARD: crosswalk is outside canonical protected view")
    required = {"adviser_proxy", "economic_sponsor_id", "signed_by", "signed_date", "status"}
    with sponsor_crosswalk.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise MissingRequiredInputError("SPONSOR_GUARD: invalid signed-crosswalk schema")
        rows = list(reader)
    if not rows or any(not all(str(r.get(k, "")).strip() for k in required) or
                       str(r["status"]).strip() != "SIGNED" for r in rows):
        raise MissingRequiredInputError("SPONSOR_GUARD: unsigned or empty crosswalk content")


def weighted_fwl(y: np.ndarray, z: np.ndarray, x0: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, FWLFit]:
    """Weighted multivariate FWL, with no n-by-n projection matrix."""
    y = np.asarray(y, float)
    z = np.asarray(z, float)
    x0 = np.asarray(x0, float)
    w = np.asarray(weights, float).reshape(-1)
    if y.ndim == 1:
        y = y[:, None]
    if np.any(w <= 0) or z.shape[0] != x0.shape[0] or y.shape[0] != z.shape[0]:
        raise ValueError("invalid weighted FWL dimensions/weights")
    q = np.sqrt(w)[:, None]
    qx, qz, qy = q * x0, q * z, q * y
    rank_x0 = np.linalg.matrix_rank(qx)
    full = np.column_stack((qx, qz))
    rank_full = np.linalg.matrix_rank(full)
    if rank_full < full.shape[1]:
        raise RankFailure(f"RANK_GUARD: rank={rank_full}, required={full.shape[1]}")
    # least-squares residualization is numerically stable and avoids M explicitly
    rz = qz - qx @ np.linalg.lstsq(qx, qz, rcond=None)[0]
    ry = qy - qx @ np.linalg.lstsq(qx, qy, rcond=None)[0]
    a = rz.T @ rz
    beta = np.linalg.solve(a, rz.T @ ry)
    # A^-1 Zr' Q maps the *unweighted* outcome into the coefficient vector.
    b = np.linalg.solve(a, rz.T) * q.reshape(1, -1)
    lev = np.sum(rz * (rz @ np.linalg.inv(a)), axis=1)
    return beta, FWLFit(b, a, rank_x0, rank_full, lev)


def _synthetic_design(cells: list[Cell], missingness: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Generic pooled continuous-oracle development fixture.

    It is not candidate A/B/C, equal-wave aggregation, stock×wave FE, or the
    proposed estimator. It deliberately does not represent observed earnings
    events, dates, SUEs, sessions, controls, or masks.
    """
    c = list(cells)
    x = np.array([u.exposure / .005 for u in c])
    waves = np.array([u.wave for u in c])
    stocks = np.array([u.permno for u in c])
    proxies = np.array([u.adviser_proxy for u in c])
    # deterministic synthetic SUE and post labels prevent accidental use of earnings data
    ix = np.arange(len(c))
    sue = ((ix * 1103515245 + 12345) % 1009) / 1009.0 * 2.0 - 1.0
    post = ((ix + np.array([sum(map(ord, w)) for w in waves])) % 2).astype(float)
    if missingness:
        keep = ~((x > np.quantile(x, .70)) & ((ix % 3) == 0))
        x, waves, stocks, proxies, sue, post = (a[keep] for a in (x, waves, stocks, proxies, sue, post))
    # A toy pooled lower-order specification, not the unresolved contract.
    base = np.column_stack((np.ones(len(x)), sue, post, x, sue * post, sue * x, post * x))
    wave_dummies = np.column_stack([(waves == w).astype(float) for w in sorted(set(waves))[1:]])
    x0 = np.column_stack((base, wave_dummies))
    z = (sue * post * x)[:, None]
    weights = np.ones(len(x))
    return z, x0, weights, {"x": x, "waves": waves, "stocks": stocks, "proxies": proxies, "sue": sue, "post": post}


def _covariance_for_operator(b: np.ndarray, groups: dict[str, np.ndarray], dependence: bool) -> np.ndarray:
    """Known synthetic covariance for a scalar coefficient across six horizons."""
    n = b.size
    rho_h = .65
    rh = rho_h ** np.abs(np.subtract.outer(np.arange(len(HORIZONS)), np.arange(len(HORIZONS))))
    if not dependence:
        return (b @ b) * rh
    # Positive semidefinite oracle covariance: iid, static stock/proxy/wave only.
    terms = [(0.35, np.arange(n).astype(str)), (0.25, groups["stocks"]), (0.25, groups["proxies"]),
             (0.15, groups["waves"])]
    scalar = 0.0
    for share, g in terms:
        sums: dict[str, float] = {}
        for gi, bi in zip(g, b):
            sums[str(gi)] = sums.get(str(gi), 0.0) + float(bi)
        scalar += share * sum(v * v for v in sums.values())
    return scalar * rh


def _draw_errors(rng: np.random.Generator, groups: dict[str, np.ndarray], reps: int, dependence: bool) -> np.ndarray:
    n = len(groups["stocks"])
    h = len(HORIZONS)
    rh = .65 ** np.abs(np.subtract.outer(np.arange(h), np.arange(h)))
    chol = np.linalg.cholesky(rh)
    result = np.zeros((reps, n, h))
    if not dependence:
        return rng.standard_normal((reps, n, h)) @ chol.T
    components = [(0.35, np.arange(n).astype(str)), (0.25, groups["stocks"]), (0.25, groups["proxies"]),
                  (0.15, groups["waves"])]
    for share, group in components:
        labels, inverse = np.unique(group.astype(str), return_inverse=True)
        draw = rng.standard_normal((reps, len(labels), h)) @ chol.T
        result += math.sqrt(share) * draw[:, inverse, :]
    return result


def _operator_estimates_in_batches(rng: np.random.Generator, b: np.ndarray, groups: dict[str, np.ndarray],
                                   beta_true: np.ndarray, reps: int, dependence: bool, batch_size: int = 32):
    """Yield batched oracle coefficient draws; no event-reuse/calendar claim."""
    n, h = len(b), len(HORIZONS)
    rh = .65 ** np.abs(np.subtract.outer(np.arange(h), np.arange(h)))
    chol = np.linalg.cholesky(rh)
    components = ([(1.0, np.arange(n).astype(str))] if not dependence else
                  [(0.35, np.arange(n).astype(str)), (0.25, groups["stocks"]),
                   (0.25, groups["proxies"]), (0.15, groups["waves"])])
    for start in range(0, reps, batch_size):
        m = min(batch_size, reps - start)
        event_error = np.zeros((m, n, h))
        for share, group in components:
            labels, inverse = np.unique(group.astype(str), return_inverse=True)
            group_error = rng.standard_normal((m, len(labels), h)) @ chol.T
            event_error += math.sqrt(share) * group_error[:, inverse, :]
        yield beta_true[None, :] + np.einsum("n,rnh->rh", b, event_error, optimize=True)


def _mc_interval(k: int, n: int) -> tuple[float, float]:
    p = k / n
    d = 1.96 * math.sqrt(max(p * (1 - p), 1e-12) / n)
    return max(0., p - d), min(1., p + d)


def generic_pooled_continuous_oracle_fixture(cells: list[Cell], reps: int = 2000, seed: int = SEED) -> list[dict[str, object]]:
    """Generic pooled continuous oracle fixture, never empirical/candidate power."""
    f = np.array([.25, .50, .70, .85, .95, 1.0])
    g = np.array([.20, .20, .15, .10, .05, 0.0])
    scenarios = (
        ("null_iid", np.zeros(6), False, False),
        ("null_dependence_few_sponsor", np.zeros(6), True, False),
        ("timing_shift", .55 * g, True, False),
        ("slower_shift", -.55 * g, True, False),
        ("amplitude_only", .30 * f, True, False),
        ("mixed_amplitude_timing", .30 * f + .55 * g, True, False),
        ("timing_shift_missingness_dependence_few_sponsor", .55 * g, True, True),
    )
    rows: list[dict[str, object]] = []
    for j, (name, beta_true, dependence, missingness) in enumerate(scenarios):
        z, x0, w, group = _synthetic_design(cells, missingness=missingness)
        # Few-proxy fixture deliberately coarsens labels; it is not cluster inference.
        if "few_sponsor" in name:
            group["proxies"] = np.where(np.arange(len(group["proxies"])) % 2, "SYNTH_PROXY_A", "SYNTH_PROXY_B")
        _, fit = weighted_fwl(np.zeros((len(w), len(HORIZONS))), z, x0, w)
        b = fit.beta_operator[0]
        v = _covariance_for_operator(b, group, dependence)
        se = np.sqrt(np.diag(v))
        # Reset common stream. Matched geometry/dependence scenarios share draws;
        # missingness/few-proxy fixtures necessarily map that stream differently.
        rng = np.random.default_rng(seed)
        zcrit = 1.959963984540054
        cover_count = np.zeros(len(HORIZONS), dtype=int)
        success_count = 0
        # horizon family amplitude restriction q_h=beta_h-f_h beta_T, h<T
        lq = np.column_stack((np.eye(5), -f[:5, None]))
        vq = lq @ v @ lq.T
        iq = np.linalg.inv(vq)
        for estimates in _operator_estimates_in_batches(rng, b, group, beta_true, reps, dependence):
            cover_count += ((beta_true >= estimates - zcrit * se) & (beta_true <= estimates + zcrit * se)).sum(axis=0)
            q = estimates @ lq.T
            wald = np.einsum("ri,ij,rj->r", q, iq, q)
            success_count += int((wald > 11.0704976935).sum())
        if np.allclose(beta_true, 0):
            target = "size_amplitude_restriction"
            success = success_count
        elif name == "amplitude_only":
            target = "size_under_amplitude_only"
            success = success_count
        else:
            target = "power_against_amplitude_only"
            success = success_count
        rate = float(success / reps)
        lo, hi = _mc_interval(int(success), reps)
        for h, count in zip(HORIZONS, cover_count):
            cov = float(count / reps)
            cov_lo, cov_hi = _mc_interval(int(count), reps)
            rows.append({"record_type": "GENERIC_POOLED_CONTINUOUS_ORACLE_FIXTURE", "scenario": name, "metric": "ci_coverage_95",
                         "horizon": h, "estimate": float(cov), "mc_ci_low": cov_lo, "mc_ci_high": cov_hi, "reps": reps,
                         "status": "DEVELOPMENT_FIXTURE/ASSUMED_SCENARIO/CONDITIONAL", "dependence": "oracle synthetic covariance" if dependence else "oracle iid synthetic covariance",
                         "timing_classification": "NOT_ESTIMABLE: no signed equivalence margin",
                         "limitation": "Not candidate A/B/C, equal-wave, stock×wave FE, full estimator, or empirical power."})
        rows.append({"record_type": "GENERIC_POOLED_CONTINUOUS_ORACLE_FIXTURE", "scenario": name, "metric": target,
                     "horizon": "joint_early_vs_terminal", "estimate": rate, "mc_ci_low": lo, "mc_ci_high": hi, "reps": reps,
                     "status": "DEVELOPMENT_FIXTURE/ASSUMED_SCENARIO/CONDITIONAL", "dependence": "oracle synthetic covariance; not boottest certification",
                     "timing_classification": "NOT_ESTIMABLE: no signed terminal equivalence margin",
                     "limitation": "Not candidate A/B/C, equal-wave, stock×wave FE, full estimator, or empirical power."})
        rows.append({"record_type": "GENERIC_POOLED_CONTINUOUS_ORACLE_FIXTURE", "scenario": name, "metric": "contrast_se_terminal",
                     "horizon": "+1d", "estimate": float(se[-1]), "mc_ci_low": "", "mc_ci_high": "", "reps": reps,
                     "status": "DEVELOPMENT_FIXTURE/ASSUMED_SCENARIO/CONDITIONAL", "dependence": "oracle synthetic covariance",
                     "timing_classification": "NOT_ESTIMABLE: no signed equivalence margin",
                     "limitation": "Not candidate A/B/C, equal-wave, stock×wave FE, full estimator, or empirical power."})
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readonly-exposure-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reps", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    if args.reps < 2000:
        raise ValueError("Final cells require >=2000 fixed-seed repetitions")
    arms = {
        "all_sponsors": load_cells(args.readonly_exposure_dir / "exposure_stock_wave_all.csv"),
        "dimensional_only": load_cells(args.readonly_exposure_dir / "exposure_stock_wave_dimensional_only.csv"),
        "excluding_dimensional": load_cells(args.readonly_exposure_dir / "exposure_stock_wave_ex_dimensional.csv"),
    }
    write_csv(args.output_dir / "support_diagnostics.csv", measured_support_rows(arms))
    write_csv(args.output_dir / "power_results.csv", actual_power_unavailable_rows() +
              generic_pooled_continuous_oracle_fixture(arms["all_sponsors"], args.reps, args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

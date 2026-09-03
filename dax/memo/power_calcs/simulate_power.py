"""SECONDARY design engine after D1 — discrete stacked event study.

D1 (dax/memo/PI_DECISION_D1_2026-08-18.md) demoted this design to corroboration
only; the confirmatory analysis is simulate_power_continuous.py. This engine
also still gives every event a full [-6,+6] window and does NOT implement the
memo section 3.2 adjacency rule (see dax/tests/test_window_survival.py), so its
event set is wider than the stack rule permits. Its cell-level output has no
proved ordering relative to person-level power and is not Gate-1 evidence.
Pre-event-only power simulation for the DAX stacked dose design."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib
from dataclasses import dataclass

import numpy as np


EARLIEST_EVENT = dt.date(2023, 3, 1)
Z_ALPHA_TWO_SIDED = 1.96
Z_POWER_80 = 0.84
REQUIRED_CELL_FIELDS = {
    "cps_occ", "month", "industry", "education_group", "n_unweighted",
    "weight_sum", "weight_sq_sum", "employment_rate",
    "hours_mean_unconditional", "hours_variance_unconditional",
    "employment_hours_covariance", "dose_sd_within_cps",
    "max_crosswalk_weight",
}
REQUIRED_DOSE_FIELDS = {
    "event_id", "event_month", "cps_occ", "dose_increment", "prior_dax"
}


@dataclass(frozen=True)
class Cell:
    cps_occ: str
    month: dt.date
    industry: str
    education_group: str
    n_unweighted: int
    weight_sum: float
    weight_sq_sum: float
    employment_rate: float
    hours_mean: float
    hours_variance: float
    employment_hours_covariance: float
    dose_sd: float
    max_crosswalk_weight: float

    @property
    def n_effective(self) -> float:
        return self.weight_sum ** 2 / self.weight_sq_sum


@dataclass(frozen=True)
class Dose:
    event_id: str
    event_month: dt.date
    cps_occ: str
    increment: float
    prior_dax: float


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path: pathlib.Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = required - fields
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def load_cells(path: pathlib.Path) -> list[Cell]:
    rows = _read_csv(path, REQUIRED_CELL_FIELDS)
    cells = []
    for line, row in enumerate(rows, start=2):
        month = dt.date.fromisoformat(row["month"])
        if month >= EARLIEST_EVENT:
            raise ValueError(f"{path}:{line}: post-event month prohibited: {month}")
        education = row["education_group"]
        if education not in {"college", "noncollege"}:
            raise ValueError(f"{path}:{line}: invalid education_group={education!r}")
        cell = Cell(
            cps_occ=row["cps_occ"], month=month, industry=row["industry"],
            education_group=education, n_unweighted=int(row["n_unweighted"]),
            weight_sum=float(row["weight_sum"]),
            weight_sq_sum=float(row["weight_sq_sum"]),
            employment_rate=float(row["employment_rate"]),
            hours_mean=float(row["hours_mean_unconditional"]),
            hours_variance=float(row["hours_variance_unconditional"]),
            employment_hours_covariance=float(row["employment_hours_covariance"]),
            dose_sd=float(row["dose_sd_within_cps"]),
            max_crosswalk_weight=float(row["max_crosswalk_weight"]),
        )
        if cell.n_unweighted <= 0 or cell.weight_sum <= 0 or cell.weight_sq_sum <= 0:
            raise ValueError(f"{path}:{line}: nonpositive count or weight moment")
        if not 0 <= cell.employment_rate <= 1:
            raise ValueError(f"{path}:{line}: employment_rate outside [0,1]")
        if cell.hours_variance <= 0 or cell.n_effective <= 1:
            raise ValueError(f"{path}:{line}: invalid variance or effective sample size")
        cells.append(cell)
    return cells


def load_doses(path: pathlib.Path) -> list[Dose]:
    rows = _read_csv(path, REQUIRED_DOSE_FIELDS)
    doses = []
    seen = set()
    for line, row in enumerate(rows, start=2):
        key = (row["event_id"], row["cps_occ"])
        if key in seen:
            raise ValueError(f"{path}:{line}: duplicate event-occupation dose {key}")
        seen.add(key)
        dose = Dose(
            event_id=row["event_id"],
            event_month=dt.date.fromisoformat(row["event_month"]),
            cps_occ=row["cps_occ"],
            increment=float(row["dose_increment"]),
            prior_dax=float(row["prior_dax"]),
        )
        if not 0 <= dose.increment <= 1 or not 0 <= dose.prior_dax <= 1:
            raise ValueError(f"{path}:{line}: dose outside [0,1]")
        doses.append(dose)
    return doses


def add_months(value: dt.date, offset: int) -> dt.date:
    index = value.year * 12 + value.month - 1 + offset
    return dt.date(index // 12, index % 12 + 1, 1)


def serial_rho(cells: list[Cell], attribute: str) -> float:
    grouped: dict[tuple[str, str], list[Cell]] = {}
    for cell in cells:
        grouped.setdefault((cell.cps_occ, cell.education_group), []).append(cell)
    x_values, y_values = [], []
    for values in grouped.values():
        values.sort(key=lambda item: item.month)
        series = np.array([getattr(item, attribute) for item in values], dtype=float)
        series -= series.mean()
        x_values.extend(series[:-1])
        y_values.extend(series[1:])
    if not x_values or np.std(x_values) == 0 or np.std(y_values) == 0:
        return 0.0
    return float(np.clip(np.corrcoef(x_values, y_values)[0, 1], 0.0, 0.8))


def categorical_dummies(values: list[str]) -> np.ndarray:
    levels = sorted(set(values))
    if len(levels) <= 1:
        return np.empty((len(values), 0))
    index = {level: position for position, level in enumerate(levels[1:])}
    result = np.zeros((len(values), len(levels) - 1), dtype=float)
    for row, value in enumerate(values):
        if value in index:
            result[row, index[value]] = 1.0
    return result


def build_stack(cells: list[Cell], doses: list[Dose], education: str | None = None) -> dict[str, object]:
    by_key: dict[tuple[str, str], list[Cell]] = {}
    for cell in cells:
        if education is None or cell.education_group == education:
            by_key.setdefault((cell.cps_occ, cell.education_group), []).append(cell)
    for values in by_key.values():
        values.sort(key=lambda item: item.month)
    occupations = sorted({dose.cps_occ for dose in doses})
    groups = [education] if education else ["college", "noncollege"]
    records = []
    events = sorted({dose.event_id for dose in doses})
    event_index = {event: position for position, event in enumerate(events)}
    for dose in doses:
        for group in groups:
            moments = by_key.get((dose.cps_occ, group))
            if not moments:
                continue
            for event_time in range(-6, 7):
                moment = moments[(event_index[dose.event_id] * 3 + event_time + 6) % len(moments)]
                calendar_month = add_months(dose.event_month, event_time)
                records.append((dose, moment, event_time, calendar_month))
    if not records:
        raise ValueError("stack has no cells")

    event_weight_totals: dict[str, float] = {}
    for dose, moment, _, _ in records:
        event_weight_totals[dose.event_id] = event_weight_totals.get(dose.event_id, 0.0) + moment.weight_sum
    weights = np.array([
        moment.weight_sum / event_weight_totals[dose.event_id]
        for dose, moment, _, _ in records
    ])
    x = np.array([
        (dose.increment / 0.10) * (event_time >= 0)
        for dose, _, event_time, _ in records
    ])
    prior = np.array([dose.prior_dax for dose, _, _, _ in records])
    occ_values = [dose.cps_occ for dose, _, _, _ in records]
    event_time_values = [f"{dose.event_id}:{event_time:+d}" for dose, _, event_time, _ in records]
    industry_month_values = [f"{moment.industry}:{month.isoformat()}" for _, moment, _, month in records]
    nuisance = np.column_stack([
        np.ones(len(records)),
        prior,
        categorical_dummies(occ_values),
        categorical_dummies(event_time_values),
        categorical_dummies(industry_month_values),
    ])
    return {
        "records": records,
        "weights": weights,
        "x": x,
        "nuisance": nuisance,
        "clusters": np.array([occupations.index(value) for value in occ_values], dtype=int),
        "occupations": occupations,
    }


class FWLClusterEstimator:
    def __init__(self, x: np.ndarray, nuisance: np.ndarray, weights: np.ndarray, clusters: np.ndarray):
        self.x = x
        self.z = nuisance
        self.w = weights
        self.clusters = clusters
        ztwz = nuisance.T @ (weights[:, None] * nuisance)
        self.z_projection = np.linalg.pinv(ztwz, rcond=1e-10) @ (nuisance.T * weights)
        self.x_residual = x - nuisance @ (self.z_projection @ x)
        self.denominator = float(np.dot(weights * self.x_residual, self.x_residual))
        if self.denominator <= 1e-12:
            raise ValueError("dose-post regressor has no residual identifying variation")
        self.unique_clusters = np.unique(clusters)
        self.k = nuisance.shape[1] + 1

    def fit(self, y: np.ndarray) -> tuple[float, float]:
        y_residual = y - self.z @ (self.z_projection @ y)
        beta = float(np.dot(self.w * self.x_residual, y_residual) / self.denominator)
        residual = y_residual - beta * self.x_residual
        scores = []
        for cluster in self.unique_clusters:
            mask = self.clusters == cluster
            scores.append(float(np.dot(self.w[mask] * self.x_residual[mask], residual[mask])))
        n = len(y)
        g = len(self.unique_clusters)
        correction = (g / (g - 1)) * ((n - 1) / max(1, n - self.k)) if g > 1 else 1.0
        variance = correction * float(np.dot(scores, scores)) / self.denominator ** 2
        return beta, float(np.sqrt(max(variance, 0.0)))


def outcome_arrays(stack: dict[str, object]) -> dict[str, np.ndarray]:
    records = stack["records"]
    employment = np.array([moment.employment_rate for _, moment, _, _ in records])
    hours = np.array([moment.hours_mean for _, moment, _, _ in records])
    n_eff = np.array([moment.n_effective for _, moment, _, _ in records])
    emp_sd = np.sqrt(np.maximum(employment * (1 - employment) / n_eff, 1e-10))
    hours_sd = np.sqrt(np.array([moment.hours_variance for _, moment, _, _ in records]) / n_eff)
    covariance = np.array([moment.employment_hours_covariance for _, moment, _, _ in records]) / n_eff
    correlation = float(np.clip(np.median(covariance / np.maximum(emp_sd * hours_sd, 1e-10)), -0.95, 0.95))
    return {"employment": employment, "hours": hours, "emp_sd": emp_sd, "hours_sd": hours_sd, "correlation": correlation}


def correlated_normals(rng: np.random.Generator, n: int, correlation: float) -> tuple[np.ndarray, np.ndarray]:
    first = rng.normal(size=n)
    second = correlation * first + np.sqrt(max(0.0, 1 - correlation ** 2)) * rng.normal(size=n)
    return first, second


def run_sample(cells: list[Cell], doses: list[Dose], education: str | None, reps: int, seed: int) -> dict[str, object]:
    sample_cells = [cell for cell in cells if education is None or cell.education_group == education]
    stack = build_stack(cells, doses, education)
    arrays = outcome_arrays(stack)
    estimator = FWLClusterEstimator(stack["x"], stack["nuisance"], stack["weights"], stack["clusters"])
    rho_emp = serial_rho(sample_cells, "employment_rate")
    rho_hours = serial_rho(sample_cells, "hours_mean")
    rng = np.random.default_rng(seed)
    clusters = stack["clusters"]
    n_clusters = len(np.unique(clusters))
    beta_null_emp, se_emp, beta_null_hours, se_hours = [], [], [], []
    for _ in range(reps):
        cluster_emp, cluster_hours = correlated_normals(rng, n_clusters, arrays["correlation"])
        cell_emp, cell_hours = correlated_normals(rng, len(clusters), arrays["correlation"])
        emp_error = arrays["emp_sd"] * (
            np.sqrt(rho_emp) * cluster_emp[clusters] + np.sqrt(1 - rho_emp) * cell_emp
        )
        hours_error = arrays["hours_sd"] * (
            np.sqrt(rho_hours) * cluster_hours[clusters] + np.sqrt(1 - rho_hours) * cell_hours
        )
        beta, se = estimator.fit(arrays["employment"] + emp_error)
        beta_null_emp.append(beta); se_emp.append(se)
        beta, se = estimator.fit(arrays["hours"] + hours_error)
        beta_null_hours.append(beta); se_hours.append(se)

    beta_null_emp = np.array(beta_null_emp); se_emp = np.array(se_emp)
    beta_null_hours = np.array(beta_null_hours); se_hours = np.array(se_hours)
    employment_grid = [-0.13, -0.10, -0.065, -0.04, -0.02, 0.0, 0.02, 0.04, 0.065, 0.10, 0.13]
    hours_grid = [-4.0, -3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0, 4.0]

    def power(beta_null: np.ndarray, se: np.ndarray, effects: list[float]) -> dict[str, float]:
        return {
            f"{effect:g}": round(float(np.mean(np.abs((beta_null + effect) / np.maximum(se, 1e-12)) > Z_ALPHA_TWO_SIDED)), 4)
            for effect in effects
        }

    records = stack["records"]
    weights = stack["weights"]
    increments = np.array([dose.increment for dose, _, _, _ in records])
    baseline = arrays["employment"]
    baseline_hours = arrays["hours"]
    high = increments >= 0.01
    zero = increments == 0
    if high.any() and zero.any():
        high_mean = float(np.average(baseline[high], weights=weights[high]))
        zero_mean = float(np.average(baseline[zero], weights=weights[zero]))
        baseline_gap = abs(high_mean - zero_mean)
        high_hours = float(np.average(baseline_hours[high], weights=weights[high]))
        zero_hours = float(np.average(baseline_hours[zero], weights=weights[zero]))
        baseline_hours_gap = abs(high_hours - zero_hours)
    else:
        baseline_gap = None
        baseline_hours_gap = None
    employment_mde = float((Z_ALPHA_TWO_SIDED + Z_POWER_80) * np.median(se_emp))
    # D3 (PI_DECISION_D3_2026-08-18): the pass bar is a frozen constant, never
    # a statistic of the sample being judged. The old rule was
    # min(0.065, 0.5 * baseline_gap), which moved with the event set — dropping
    # one event loosened it by 185%. baseline_gap is still REPORTED as a
    # descriptive diagnostic; it no longer sets the threshold.
    import json as _json
    _standard = _json.loads((pathlib.Path(__file__).with_name("power_standard.json")).read_text())
    _frozen = _standard["status"] == "FROZEN"
    threshold = _standard["standard"]["employment_mde_ceiling"]
    hours_mde = float((Z_ALPHA_TWO_SIDED + Z_POWER_80) * np.median(se_hours))
    hours_threshold = _standard["standard"]["hours_mde_ceiling"]

    low_quality = sorted({
        moment.cps_occ for _, moment, _, _ in records
        if moment.dose_sd > 0.10 or moment.max_crosswalk_weight < 0.50
    })
    event_counts: dict[str, int] = {}
    for dose, _, _, _ in records:
        if dose.increment >= 0.01:
            event_counts[dose.event_id] = event_counts.get(dose.event_id, 0) + 1
    return {
        "education_group": education or "pooled",
        "n_stack_cells": len(records),
        "n_occupation_clusters": n_clusters,
        "n_nuisance_parameters": int(stack["nuisance"].shape[1]),
        "serial_rho_employment": round(rho_emp, 6),
        "serial_rho_hours": round(rho_hours, 6),
        "employment_hours_noise_correlation": round(arrays["correlation"], 6),
        "treated_cells_by_event": event_counts,
        "low_quality_cps_codes": low_quality,
        "employment": {
            "median_cluster_se_per_0.10_dax": round(float(np.median(se_emp)), 8),
            "mde80_per_0.10_dax": round(employment_mde, 8),
            "baseline_employment_gap": None if baseline_gap is None else round(baseline_gap, 8),
            "approved_mde_ceiling": threshold,
            "standard_status": _standard["status"],
            "adequately_powered": (employment_mde <= threshold) if (_frozen and threshold is not None) else None,
            "rejection_rate_by_effect": power(beta_null_emp, se_emp, employment_grid),
        },
        "hours_unconditional": {
            "median_cluster_se_per_0.10_dax": round(float(np.median(se_hours)), 8),
            "mde80_per_0.10_dax": round(hours_mde, 8),
            "baseline_hours_gap": None if baseline_hours_gap is None else round(baseline_hours_gap, 8),
            "approved_mde_ceiling": hours_threshold,
            "standard_status": _standard["status"],
            "adequately_powered": (hours_mde <= hours_threshold) if (_frozen and hours_threshold is not None) else None,
            "rejection_rate_by_effect": power(beta_null_hours, se_hours, hours_grid),
        },
    }


def run(cells_path: pathlib.Path, doses_path: pathlib.Path, output: pathlib.Path, reps: int, seed: int, synthetic: bool) -> dict[str, object]:
    cells = load_cells(cells_path)
    doses = load_doses(doses_path)
    cell_occupations = {cell.cps_occ for cell in cells}
    dose_occupations = {dose.cps_occ for dose in doses}
    if not dose_occupations <= cell_occupations:
        raise ValueError(f"event doses contain occupations absent from pre-period cells: {sorted(dose_occupations-cell_occupations)}")
    events = sorted({dose.event_id for dose in doses})
    if len(events) < 3:
        raise ValueError("approved minimum estimability requires at least three events")
    report = {
        "status": "NOT_EVIDENCE_SYNTHETIC_SMOKE_TEST" if synthetic else "EMPIRICAL_PRE_EVENT_POWER",
        "seed": seed,
        "reps": reps,
        "alpha_two_sided": 0.05,
        "target_power": 0.80,
        "effect_scale": "coefficient per 0.10 DAX increment",
        "inputs": {
            "preperiod_cells": str(cells_path),
            "preperiod_cells_sha256": sha256(cells_path),
            "event_doses": str(doses_path),
            "event_doses_sha256": sha256(doses_path),
        },
        "events": events,
        "samples": [
            run_sample(cells, doses, None, reps, seed),
            run_sample(cells, doses, "college", reps, seed + 1),
            run_sample(cells, doses, "noncollege", reps, seed + 2),
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cells", type=pathlib.Path, required=True)
    parser.add_argument("--doses", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--reps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.reps < 20:
        raise ValueError("at least 20 repetitions required")
    report = run(args.cells, args.doses, args.output, args.reps, args.seed, args.synthetic)
    print(json.dumps({
        "status": report["status"],
        "output": str(args.output),
        "samples": [
            {
                "education_group": sample["education_group"],
                "employment_mde80": sample["employment"]["mde80_per_0.10_dax"],
                "employment_adequately_powered": sample["employment"]["adequately_powered"],
                "hours_mde80": sample["hours_unconditional"]["mde80_per_0.10_dax"],
                "hours_adequately_powered": sample["hours_unconditional"]["adequately_powered"],
            }
            for sample in report["samples"]
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

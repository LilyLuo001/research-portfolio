"""Create deterministic, non-evidentiary inputs for the DAX power engine."""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

import numpy as np


HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "synthetic"
SEED = 20260806


def months() -> list[dt.date]:
    result = []
    value = dt.date(2022, 3, 1)
    while value < dt.date(2023, 3, 1):
        result.append(value)
        value = dt.date(value.year + (value.month == 12), value.month % 12 + 1, 1)
    return result


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    occupations = [f"OCC{number:03d}" for number in range(1, 61)]
    events = [
        ("GPT4_LAUNCH", "2023-03-01"),
        ("GPT4O_LAUNCH", "2024-05-01"),
        ("GPT41_LAUNCH", "2025-04-01"),
        ("GPT5_LAUNCH", "2025-08-01"),
    ]

    cell_path = OUT / "preperiod_cells.csv"
    cell_fields = [
        "cps_occ", "month", "industry", "education_group", "n_unweighted",
        "weight_sum", "weight_sq_sum", "employment_rate",
        "hours_mean_unconditional", "hours_variance_unconditional",
        "employment_hours_covariance", "dose_sd_within_cps",
        "max_crosswalk_weight",
    ]
    with cell_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=cell_fields, lineterminator="\n")
        writer.writeheader()
        for occ_index, occupation in enumerate(occupations):
            industry = f"IND{occ_index % 6 + 1}"
            occ_emp = 0.72 + 0.08 * np.sin(occ_index / 8)
            occ_hours = 26.0 + 3.0 * np.cos(occ_index / 9)
            dose_sd = float(np.clip(rng.beta(2, 8) * 0.22, 0.01, 0.18))
            max_weight = float(np.clip(rng.beta(7, 2), 0.25, 0.98))
            for month_index, month in enumerate(months()):
                season = 0.012 * np.sin(2 * np.pi * month_index / 12)
                for education in ("college", "noncollege"):
                    education_shift = 0.045 if education == "college" else -0.02
                    n = int(rng.integers(24, 76))
                    raw_weights = rng.lognormal(0.0, 0.35, n)
                    employment = float(np.clip(occ_emp + education_shift + season, 0.45, 0.95))
                    hours = float(np.clip(occ_hours + 2.5 * (education == "college") + 20 * season, 12, 40))
                    hours_variance = 150.0 + 20.0 * (education == "noncollege")
                    covariance = employment * (1 - employment) * 23.0
                    writer.writerow({
                        "cps_occ": occupation,
                        "month": month.isoformat(),
                        "industry": industry,
                        "education_group": education,
                        "n_unweighted": n,
                        "weight_sum": f"{raw_weights.sum():.8f}",
                        "weight_sq_sum": f"{np.square(raw_weights).sum():.8f}",
                        "employment_rate": f"{employment:.8f}",
                        "hours_mean_unconditional": f"{hours:.8f}",
                        "hours_variance_unconditional": f"{hours_variance:.8f}",
                        "employment_hours_covariance": f"{covariance:.8f}",
                        "dose_sd_within_cps": f"{dose_sd:.8f}",
                        "max_crosswalk_weight": f"{max_weight:.8f}",
                    })

    dose_path = OUT / "event_doses.csv"
    dose_fields = ["event_id", "event_month", "cps_occ", "dose_increment", "prior_dax"]
    cumulative = {occupation: 0.0 for occupation in occupations}
    with dose_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=dose_fields, lineterminator="\n")
        writer.writeheader()
        for event_index, (event_id, event_month) in enumerate(events):
            for occ_index, occupation in enumerate(occupations):
                latent = max(0.0, 0.018 + 0.035 * np.sin((occ_index + 4 * event_index) / 7) + rng.normal(0, 0.012))
                dose = float(np.clip(latent, 0, 0.12))
                writer.writerow({
                    "event_id": event_id,
                    "event_month": event_month,
                    "cps_occ": occupation,
                    "dose_increment": f"{dose:.8f}",
                    "prior_dax": f"{cumulative[occupation]:.8f}",
                })
                cumulative[occupation] = min(1.0, cumulative[occupation] + dose)

    print(cell_path)
    print(dose_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Power simulation for the D1 primary: continuous cumulative-dose design.

WHAT CHANGED AND WHY
--------------------
`simulate_power.py` models the discrete stacked event study. D1
(`dax/memo/PI_DECISION_D1_2026-08-18.md`) demoted that design to secondary
corroboration: with 21 events across 41 months the treatment is effectively
continuous, and every discrete option either collapsed to one estimable event
or manufactured clean windows by ignoring events that actually happened.

This engine implements the replacement. There is no event selection, no
stacking, and no window rule. The regressor is the monthly DAX level itself —
the index the memo already constructs in section 2 and which the stacked
design was discarding most of.

    occupation-month panel, Nov 2021 -> latest frozen month
    y_ot = beta * (DAX_ot / 0.10) + occ FE + month FE + industry x month FE + e
    clustered on the original CPS occupation code

Identification comes from occupations accumulating dose on different profiles
across the same calendar dates. Occupation effects absorb level differences,
month effects absorb the common time path, so what identifies beta is the
interaction of occupation-specific dose magnitude with time. If every
occupation's dose path were proportional to one common path this would reduce
to a single exposure-times-post contrast; `dose_profile_rank` in the report is
the diagnostic for how far from that degenerate case the real doses sit.

TWO PROPERTIES THIS ENGINE ENFORCES
-----------------------------------
1. **The seal.** Only pre-event moments are read. Post-event months exist in
   the panel as *design structure* — dose paths and fixed effects — and their
   outcomes are simulated under the null plus an injected effect. No post-event
   outcome is ever read. The engine refuses to run if the cell file contains a
   month at or after the first event.
2. **The frozen bar (D3).** `adequately_powered` is null unless
   `power_standard.json` is FROZEN. The engine never derives its own pass
   threshold from the sample it is judging — that defect is what D3 resolved.

    python dax/memo/power_calcs/simulate_power_continuous.py \\
        --cells synthetic/preperiod_cells.csv \\
        --doses synthetic/event_doses.csv \\
        --output synthetic/power_results_continuous.json --synthetic
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from simulate_power import (  # noqa: E402  reuse the audited primitives
    Cell, Dose, FWLClusterEstimator, Z_ALPHA_TWO_SIDED, Z_POWER_80,
    add_months, categorical_dummies, correlated_normals, load_cells,
    load_doses, serial_rho, sha256,
)

STANDARD = HERE / "power_standard.json"
DOSE_SCALE = 0.10          # coefficients are per 0.10 DAX, as registered
PANEL_START = dt.date(2021, 11, 1)


def load_standard() -> dict[str, object]:
    return json.loads(STANDARD.read_text(encoding="utf-8"))


def month_sequence(start: dt.date, end: dt.date) -> list[dt.date]:
    months, cursor = [], start
    while cursor <= end:
        months.append(cursor)
        cursor = add_months(cursor, 1)
    return months


def dax_paths(doses: list[Dose], months: list[dt.date]) -> dict[str, np.ndarray]:
    """Cumulative DAX level per occupation over the panel months.

    DAX_ot = prior_dax + sum of increments for events effective on or before t.
    This is the memo's section 2 index, not an event-window construction.
    """
    by_occupation: dict[str, list[Dose]] = {}
    for dose in doses:
        by_occupation.setdefault(dose.cps_occ, []).append(dose)

    paths: dict[str, np.ndarray] = {}
    for occupation, occupation_doses in by_occupation.items():
        occupation_doses.sort(key=lambda d: d.event_month)
        prior = min(d.prior_dax for d in occupation_doses)
        level, path = prior, []
        for month in months:
            level = prior + sum(d.increment for d in occupation_doses
                                if d.event_month <= month)
            path.append(level)
        paths[occupation] = np.array(path, dtype=float)
    return paths


def placebo_lead_design(doses: list[Dose], pre_months: list[dt.date],
                        horizon: dt.date) -> dict[str, object]:
    """Decision 14's re-specified pre-trend test, as an estimable regressor.

    The superseded form tested pre-event dose coefficients. Cumulative dose is
    identically zero before the first event, so that regressor had no variance
    and no coefficient — the test could never have run. The replacement uses
    EVENTUAL exposure `D_o` (cumulative dose at a frozen horizon), a fixed
    occupation characteristic that does vary in the pre-period, interacted with
    time. It asks whether occupations destined for high exposure were already
    trending differently before any exposure existed.

    Returns the regressor and its variance so the caller can prove estimability
    instead of asserting it.
    """
    eventual = {occupation: path[-1]
                for occupation, path in dax_paths(doses, [horizon]).items()}
    origin = pre_months[0]
    rows = [(occupation, month,
             eventual[occupation] * ((month.year - origin.year) * 12
                                     + (month.month - origin.month)))
            for occupation in sorted(eventual) for month in pre_months]
    values = np.array([r[2] for r in rows], dtype=float)
    return {
        "horizon": horizon.isoformat(),
        "n_rows": len(rows),
        "regressor_variance": float(values.var()),
        "estimable": bool(values.var() > 0),
        "eventual_dose_variance": float(np.var(list(eventual.values()))),
    }


# Red-team M1 (2026-08-18, DeepSeek v4-pro, gate BLOCK): the raw dose matrix is
# the wrong object to test for degeneracy. Occupation and calendar-month effects
# are absorbed by the design, so what identifies beta is only what SURVIVES that
# absorption. A dose matrix can look full-rank and still leave near-nothing after
# residualization. The gate below therefore tests the residualized matrix.
DEGENERACY_LEADING_SHARE = 0.95
DEGENERACY_MIN_RETAINED = 0.01   # residual/raw weighted variance ratio


def residualized_dose_profile(panel: dict[str, object]) -> dict[str, object]:
    """Rank and concentration of the dose matrix AFTER the nuisance design.

    Uses the same weighted projection as the estimator, so this reports the
    variation beta is actually identified from — not the variation that exists
    before occupation, month, industry-by-month and decile-by-month effects
    take their share.
    """
    x = np.asarray(panel["x"], dtype=float)
    nuisance = np.asarray(panel["nuisance"], dtype=float)
    weights = np.asarray(panel["weights"], dtype=float)

    ztwz = nuisance.T @ (weights[:, None] * nuisance)
    projection = np.linalg.pinv(ztwz, rcond=1e-10) @ (nuisance.T * weights)
    residual = x - nuisance @ (projection @ x)

    raw_variance = float(np.average((x - np.average(x, weights=weights)) ** 2, weights=weights))
    residual_variance = float(np.average(residual ** 2, weights=weights))
    retained = residual_variance / raw_variance if raw_variance > 0 else 0.0

    # Reshape the residual back to occupation x month to inspect its structure.
    records = panel["records"]
    occupations = {o: i for i, o in enumerate(panel["occupations"])}
    months = {m: i for i, m in enumerate(panel["months"])}
    matrix = np.zeros((len(occupations), len(months)))
    counts = np.zeros_like(matrix)
    for value, record in zip(residual, records):
        row, column = occupations[record[0]], months[record[2]]
        matrix[row, column] += value
        counts[row, column] += 1
    matrix = np.divide(matrix, np.maximum(counts, 1))

    if not np.any(matrix):
        return {"effective_rank": 0, "leading_share": None,
                "residual_variance_retained": round(retained, 8),
                "degenerate": True,
                "reason": "no identifying variation survives the nuisance design"}

    singular = np.linalg.svd(matrix, compute_uv=False)
    total = float((singular ** 2).sum())
    leading = float(singular[0] ** 2 / total) if total > 0 else None
    rank = int((singular > singular.max() * 1e-6).sum())

    degenerate = bool(
        retained < DEGENERACY_MIN_RETAINED
        or rank <= 1
        or (leading is not None and leading > DEGENERACY_LEADING_SHARE)
    )
    return {
        "effective_rank": rank,
        "leading_share": None if leading is None else round(leading, 6),
        "residual_variance_retained": round(retained, 8),
        "degenerate": degenerate,
        "reason": ("identification collapses to one contrast after absorption"
                   if degenerate else "multi-dimensional identifying variation survives"),
        "thresholds": {"leading_share_max": DEGENERACY_LEADING_SHARE,
                       "min_variance_retained": DEGENERACY_MIN_RETAINED},
    }


def assert_seal(cells: list[Cell], first_event: dt.date) -> None:
    """Refuse to proceed if the moment file reaches into the post-event period."""
    intruding = sorted({c.month for c in cells if c.month >= first_event})
    if intruding:
        raise SystemExit(
            "REFUSED: the cell file contains months at or after the first event "
            f"({first_event.isoformat()}): {[m.isoformat() for m in intruding[:5]]}. "
            "Power must be computed from pre-event moments only. This engine "
            "does not read post-event outcomes before the preregistration tag."
        )


def build_panel(cells: list[Cell], doses: list[Dose], education: str | None,
                months: list[dt.date]) -> dict[str, object]:
    """Occupation-month panel with a continuous dose regressor."""
    groups = [education] if education else ["college", "noncollege"]
    moments_by_key: dict[tuple[str, str], list[Cell]] = {}
    for cell in cells:
        if education is None or cell.education_group == education:
            moments_by_key.setdefault((cell.cps_occ, cell.education_group), []).append(cell)
    for values in moments_by_key.values():
        values.sort(key=lambda item: item.month)

    paths = dax_paths(doses, months)
    records: list[tuple[str, str, dt.date, Cell, float]] = []
    for occupation in sorted(paths):
        for group in groups:
            moments = moments_by_key.get((occupation, group))
            if not moments:
                continue
            for position, month in enumerate(months):
                # Pre-event moments describe the noise process; they are cycled
                # across the panel because post-event moments do not exist and
                # must not be read. Dose and fixed effects carry the design.
                moment = moments[position % len(moments)]
                records.append((occupation, group, month, moment, paths[occupation][position]))

    if not records:
        raise ValueError("continuous panel has no cells")

    weight_total = sum(record[3].weight_sum for record in records)
    weights = np.array([record[3].weight_sum / weight_total for record in records])
    x = np.array([record[4] / DOSE_SCALE for record in records])

    occupations = sorted(paths)
    nuisance = np.column_stack([
        np.ones(len(records)),
        categorical_dummies([r[0] for r in records]),                       # occupation
        categorical_dummies([r[2].isoformat() for r in records]),           # calendar month
        categorical_dummies([f"{r[3].industry}:{r[2].isoformat()}" for r in records]),
    ])
    return {
        "records": records,
        "weights": weights,
        "x": x,
        "nuisance": nuisance,
        "clusters": np.array([occupations.index(r[0]) for r in records], dtype=int),
        "occupations": occupations,
        "months": months,
        "paths": paths,
    }


def dose_profile_rank(paths: dict[str, np.ndarray]) -> dict[str, object]:
    """How far the dose paths are from one common path scaled per occupation.

    Rank 1 means every occupation moves proportionally and the design collapses
    to a single exposure-times-post contrast; higher rank means genuine timing
    variation is contributing identification.
    """
    matrix = np.array([paths[o] for o in sorted(paths)])
    centred = matrix - matrix.mean(axis=0, keepdims=True)
    if centred.size == 0 or not np.any(centred):
        return {"effective_rank": 0, "leading_share": None}
    singular = np.linalg.svd(centred, compute_uv=False)
    total = float((singular ** 2).sum())
    return {
        "effective_rank": int((singular > singular.max() * 1e-6).sum()),
        "leading_share": round(float(singular[0] ** 2 / total), 6) if total > 0 else None,
    }


def run_sample(cells: list[Cell], doses: list[Dose], education: str | None,
               months: list[dt.date], reps: int, seed: int) -> dict[str, object]:
    sample_cells = [c for c in cells if education is None or c.education_group == education]
    panel = build_panel(cells, doses, education, months)
    records = panel["records"]
    estimator = FWLClusterEstimator(panel["x"], panel["nuisance"],
                                    panel["weights"], panel["clusters"])

    employment = np.array([r[3].employment_rate for r in records])
    hours = np.array([r[3].hours_mean for r in records])
    n_effective = np.array([r[3].n_effective for r in records])
    employment_sd = np.sqrt(np.maximum(employment * (1 - employment) / n_effective, 1e-10))
    hours_sd = np.sqrt(np.array([r[3].hours_variance for r in records]) / n_effective)
    covariance = np.array([r[3].employment_hours_covariance for r in records]) / n_effective
    correlation = float(np.clip(
        np.median(covariance / np.maximum(employment_sd * hours_sd, 1e-10)), -0.95, 0.95))

    rho_employment = serial_rho(sample_cells, "employment_rate")
    rho_hours = serial_rho(sample_cells, "hours_mean")
    rng = np.random.default_rng(seed)

    se_employment, se_hours = [], []
    for _ in range(reps):
        shock_employment, shock_hours = correlated_normals(rng, len(records), correlation)
        carry_e, carry_h = 0.0, 0.0
        noise_e, noise_h = np.empty(len(records)), np.empty(len(records))
        for index in range(len(records)):
            # AR(1) within the panel, matching the pre-period serial correlation.
            carry_e = rho_employment * carry_e + np.sqrt(max(0.0, 1 - rho_employment ** 2)) * shock_employment[index]
            carry_h = rho_hours * carry_h + np.sqrt(max(0.0, 1 - rho_hours ** 2)) * shock_hours[index]
            noise_e[index], noise_h[index] = carry_e, carry_h
        _, se = estimator.fit(employment + employment_sd * noise_e)
        se_employment.append(se)
        _, se_h = estimator.fit(hours + hours_sd * noise_h)
        se_hours.append(se_h)

    def mde(values: list[float]) -> float:
        return float((Z_ALPHA_TWO_SIDED + Z_POWER_80) * np.median(values))

    return {
        "education_group": education or "pooled",
        "n_panel_cells": len(records),
        "n_occupation_clusters": int(len(np.unique(panel["clusters"]))),
        "n_nuisance_parameters": int(panel["nuisance"].shape[1]),
        "n_months": len(months),
        "serial_rho_employment": round(rho_employment, 6),
        "serial_rho_hours": round(rho_hours, 6),
        "employment_hours_noise_correlation": round(correlation, 6),
        "dose_profile": dose_profile_rank(panel["paths"]),
        "dose_profile_residualized": residualized_dose_profile(panel),
        "employment": {
            "median_cluster_se_per_0.10_dax": round(float(np.median(se_employment)), 8),
            "mde80_per_0.10_dax": round(mde(se_employment), 8),
        },
        "hours": {
            "median_cluster_se_per_0.10_dax": round(float(np.median(se_hours)), 8),
            "mde80_per_0.10_dax": round(mde(se_hours), 8),
        },
    }


def judge(sample: dict[str, object], standard: dict[str, object]) -> None:
    """Apply the D3 frozen bar, or refuse to judge at all."""
    frozen = standard["status"] == "FROZEN"
    for outcome, ceiling_key in (("employment", "employment_mde_ceiling"),
                                 ("hours", "hours_mde_ceiling")):
        ceiling = standard["standard"][ceiling_key]
        block = sample[outcome]
        block["approved_mde_ceiling"] = ceiling
        if frozen and ceiling is not None:
            block["adequately_powered"] = bool(block["mde80_per_0.10_dax"] <= ceiling)
        else:
            block["adequately_powered"] = None
            block["reason"] = (
                "power standard is not FROZEN — see PI_DECISION_D3_2026-08-18.md; "
                "run freeze_power_standard.py on the real pre-event CPS extract"
            )
            # Report what the frozen constant would have to be for this design
            # to pass. This keeps the unfrozen state informative without
            # inventing the baseline, which no model may supply from memory.
            fraction = standard["standard"]["max_mde_fraction_of_benchmark"]
            decline = standard["benchmark"]["relative_decline"]
            divisor = fraction * decline
            block["break_even_baseline"] = (
                round(float(block["mde80_per_0.10_dax"]) / divisor, 6)
                if divisor > 0 else None
            )
            block["break_even_note"] = (
                f"passes iff the frozen pre-event baseline {outcome} level "
                f"exceeds this value, since ceiling = {fraction} x {decline} x baseline"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cells", type=pathlib.Path, required=True)
    parser.add_argument("--doses", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--reps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260818)
    parser.add_argument("--panel-end", default=None,
                        help="last panel month YYYY-MM (default: last event month + 6)")
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.reps < 20:
        raise ValueError("at least 20 repetitions required")

    cells = load_cells(args.cells)
    doses = load_doses(args.doses)
    first_event = min(d.event_month for d in doses)
    assert_seal(cells, first_event)

    last_event = max(d.event_month for d in doses)
    end = (dt.date(int(args.panel_end[:4]), int(args.panel_end[5:7]), 1)
           if args.panel_end else add_months(last_event, 6))
    months = month_sequence(PANEL_START, end)

    standard = load_standard()
    samples = [run_sample(cells, doses, group, months, args.reps, args.seed + offset)
               for offset, group in enumerate([None, "college", "noncollege"])]
    for sample in samples:
        judge(sample, standard)

    report = {
        "status": ("NOT_EVIDENCE_SYNTHETIC_SMOKE_TEST" if args.synthetic
                   else "CONTINUOUS_DOSE_POWER"),
        "design": "D1 primary — continuous cumulative dose, no event selection",
        "decision_refs": ["dax/memo/PI_DECISION_D1_2026-08-18.md",
                          "dax/memo/PI_DECISION_D3_2026-08-18.md"],
        "seed": args.seed,
        "reps": args.reps,
        "effect_scale": "coefficient per 0.10 DAX increment",
        "panel": {"start": PANEL_START.isoformat(), "end": end.isoformat(),
                  "n_months": len(months), "first_event": first_event.isoformat()},
        "standard_status": standard["status"],
        "inputs": {
            "preperiod_cells": str(args.cells),
            "preperiod_cells_sha256": sha256(args.cells),
            "event_doses": str(args.doses),
            "event_doses_sha256": sha256(args.doses),
            "power_standard_sha256": sha256(STANDARD),
        },
        "n_events_in_dose_path": len({d.event_id for d in doses}),
        "pretrend_placebo_lead": [
            placebo_lead_design(doses,
                                [m for m in months if m < first_event],
                                dt.date(year, 12, 1))
            for year in (2023, 2024, 2025)
        ],
        "samples": samples,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    pooled = samples[0]
    print(json.dumps({
        "status": report["status"],
        "standard_status": standard["status"],
        "panel_cells": pooled["n_panel_cells"],
        "months": len(months),
        "dose_profile": pooled["dose_profile"],
        "employment_mde80": pooled["employment"]["mde80_per_0.10_dax"],
        "employment_adequately_powered": pooled["employment"]["adequately_powered"],
        "hours_mde80": pooled["hours"]["mde80_per_0.10_dax"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

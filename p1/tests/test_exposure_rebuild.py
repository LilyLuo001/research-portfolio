"""Unit checks for the frozen P1 Exposure^pre construction helpers."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "exposure" / "build_exposure_from_wrds.py"
SPEC = importlib.util.spec_from_file_location("p1_exposure_rebuild", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
EXPOSURE_DIR = MODULE_PATH.parent


def test_missing_denominator_is_explicitly_safe_not_post_event() -> None:
    assert MODULE.missing_or_strictly_before(float("nan"), "2026-07-24")
    assert MODULE.missing_or_strictly_before("", "2026-07-24")


def test_denominator_must_be_strictly_pre_event() -> None:
    assert MODULE.missing_or_strictly_before("2025-06-27", "2025-06-30")
    assert not MODULE.missing_or_strictly_before("2025-06-30", "2025-06-30")
    assert not MODULE.missing_or_strictly_before("2025-07-01", "2025-06-30")
    assert not MODULE.missing_or_strictly_before("not-a-date", "2025-06-30")


def test_completed_census_excludes_future_cancelled_and_unresolved() -> None:
    events = pd.DataFrame(
        {
            "final_tier": [
                "A_explicit_completion",
                "B_structural_completion",
                "announced_future",
                "cancelled_or_not_completed",
                "unresolved",
            ]
        }
    )
    assert MODULE.completed_event_mask(events).tolist() == [True, True, False, False, False]


def test_prior_observation_respects_strict_and_gap_rules() -> None:
    daily = pd.DataFrame(
        {
            "permno": [1, 1],
            "crsp_date": pd.to_datetime(["2025-06-27", "2025-06-30"]),
            "price": [10.0, 11.0],
            "shrout": [100.0, 100.0],
            "share_factor": [1.0, 1.0],
            "source_family": ["fixture", "fixture"],
            "source_file": ["fixture", "fixture"],
        }
    )
    index = MODULE.daily_lookup(daily)
    strict = MODULE.prior_observation(index, 1, "2025-06-30", strict=True, max_gap=7)
    same_day = MODULE.prior_observation(index, 1, "2025-06-30", strict=False, max_gap=4)
    stale = MODULE.prior_observation(index, 1, "2025-07-10", strict=False, max_gap=4)

    assert strict.crsp_date == pd.Timestamp("2025-06-27")
    assert same_day.crsp_date == pd.Timestamp("2025-06-30")
    assert stale is None


def test_committed_exposure_artifacts_freeze_the_signed_gate0_sample() -> None:
    universe = pd.read_csv(EXPOSURE_DIR / "exposure_universe_gate0_pass.csv")
    pending = pd.read_csv(EXPOSURE_DIR / "exposure_pending_missing_post.csv")
    holdings = pd.read_parquet(EXPOSURE_DIR / "nport_pre_holdings_long.parquet")
    leakage = pd.read_csv(EXPOSURE_DIR / "exposure_leakage_audit.csv")

    assert (len(universe), len(pending)) == (71, 3)
    assert universe.event_id.nunique() == 71
    assert set(universe.event_id).isdisjoint(pending.event_id)
    assert set(holdings.event_id) == set(universe.event_id)
    assert pd.to_datetime(holdings.pre_report_date).lt(
        pd.to_datetime(holdings.effective_date)
    ).all()
    assert len(leakage) == 71
    assert leakage.leakage_audit_pass.all()


def test_committed_primary_exposure_formula_and_keys() -> None:
    exposure = pd.read_csv(EXPOSURE_DIR / "exposure_stock_wave_all.csv")
    assert not exposure.duplicated(["permno", "wave_id"]).any()
    ready = exposure[exposure.primary_ready].copy()
    calculated = ready.adjusted_shares_held / ready.shares_outstanding
    assert (ready.exposure_ownership - calculated).abs().max() == pytest.approx(0)
    assert ready.loc[ready.exposure_ownership.gt(0), "permno"].nunique() == 3440
    assert ready.loc[ready.exposure_ownership.ge(.005), "permno"].nunique() == 573
    forbidden = {"car", "sue", "speed", "earnings_return", "headline_beta"}
    assert forbidden.isdisjoint({c.lower() for c in exposure.columns})


def test_dimensional_robustness_numerators_reconstruct_all_sponsors() -> None:
    key = ["permno", "wave_id", "effective_date"]
    all_sponsors = pd.read_csv(EXPOSURE_DIR / "exposure_stock_wave_all.csv")
    dimensional = pd.read_csv(EXPOSURE_DIR / "exposure_stock_wave_dimensional_only.csv")
    ex_dimensional = pd.read_csv(EXPOSURE_DIR / "exposure_stock_wave_ex_dimensional.csv")
    arms = dimensional.merge(
        ex_dimensional, on=key, how="outer", suffixes=("_dim", "_ex")
    )
    reconstructed = arms.adjusted_shares_held_dim.fillna(0) + arms.adjusted_shares_held_ex.fillna(0)
    check = all_sponsors.merge(arms[key].assign(reconstructed=reconstructed), on=key, how="left")
    assert (check.adjusted_shares_held - check.reconstructed).abs().max() == pytest.approx(0)


def test_current_event_master_census_is_not_the_legacy_172_register() -> None:
    master = pd.read_csv(
        MODULE_PATH.parents[1] / "universe_v2" / "output" / "event_master_final_reconciled.csv"
    )
    assert len(master) == 247
    assert MODULE.completed_event_mask(master).sum() == 156
    assert master.timing_eligible_primary.sum() == 74

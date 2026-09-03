from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "p1/viability"


def test_required_viability_deliverables_exist():
    required = {
        "p1_effective_sample_size_audit.csv",
        "p1_wave_coverage_audit.csv",
        "p1_mde_current_design.csv",
        "p1_power_expansion_scenarios.csv",
        "p1_rescue_target.csv",
        "p1_nonexact_82_priority.csv",
        "p1_external_data_acquisition_plan.md",
        "p1_viability_report.md",
    }
    assert required <= {p.name for p in OUT.iterdir()}


def test_wave_audit_is_exhaustive_and_reconciles_47_to_30():
    waves = pd.read_csv(OUT / "p1_wave_coverage_audit.csv")
    assert len(waves) == 47
    assert waves["wave_id"].nunique() == 47
    assert int(waves["primary_ready_cells"].gt(0).sum()) == 30
    expected = {
        "fully ownership-ready": 11,
        "partially mapped": 19,
        "non-common-equity only": 9,
        "security-mapping failure": 7,
        "missing CRSP denominator": 1,
    }
    assert waves["coverage_class"].value_counts().to_dict() == expected


def test_effective_n_and_current_mde_do_not_claim_raw_outcome_rows():
    ess = pd.read_csv(OUT / "p1_effective_sample_size_audit.csv", dtype={"value": str})
    raw = ess.loc[ess["metric"].eq("raw_earnings_event_observations"), "value"].iloc[0]
    assert raw == "NOT_YET_OBSERVABLE"
    info = ess.loc[ess["metric"].eq("wave_information_ess")].set_index("sample")["value"].astype(float)
    assert 2.8 < info["all"] < 3.0
    assert 2.8 < info["exclude_dimensional"] < 3.0

    mde = pd.read_csv(OUT / "p1_mde_current_design.csv")
    primary = mde.loc[(mde["variance_model"].eq("clustered_base_primary")) & mde["horizon"].eq("5m")].set_index("sample")
    assert primary.loc["all", "mde80_residual_car_sd_at_0p5pct"] > 0.5
    assert primary.loc["exclude_dimensional", "mde80_residual_car_sd_at_0p5pct"] > 0.5
    assert pd.isna(primary.loc["dimensional_only", "mde80_residual_car_sd_at_0p5pct"])
    assert set(mde["absolute_mde_bps"]) == {"NOT_ESTIMABLE_PRE_OUTCOME_PANEL"}


def test_nonexact_pool_and_decision_are_frozen():
    priority = pd.read_csv(OUT / "p1_nonexact_82_priority.csv")
    assert len(priority) == 82
    assert priority["event_id"].nunique() == 82
    assert priority["priority_rank"].tolist() == list(range(1, 83))

    report = (OUT / "p1_viability_report.md").read_text()
    assert "C. NOT PRACTICALLY VIABLE UNDER THE CURRENT DESIGN" in report
    assert "No earnings outcome, CAR, or treatment coefficient was loaded or inspected" in report

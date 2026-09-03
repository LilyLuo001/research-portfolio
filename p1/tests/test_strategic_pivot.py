from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "p1" / "strategic_pivot"


def test_required_strategic_deliverables_exist():
    required = {
        "p1_corrected_power_audit.csv",
        "p1_treatment_dose_distribution.csv",
        "vanguard_etf_shareclass_census.csv",
        "modern_etf_shareclass_census.csv",
        "shareclass_source_audit.csv",
        "conversion_vs_shareclass_design_comparison.md",
        "fund_level_conversion_feasibility.md",
        "high_dose_stock_design_feasibility.md",
        "refraction_ltilt_killtest_plan.md",
        "fomc_two_step_identification_plan.md",
        "announcement_effective_date_architecture.md",
        "portfolio_continuity_audit_plan.md",
        "top_journal_project_comparison.md",
        "strategic_recommendation.md",
    }
    assert required <= {p.name for p in AUDIT.iterdir()}


def test_census_boundaries_and_directions_are_frozen():
    vanguard = pd.read_csv(AUDIT / "vanguard_etf_shareclass_census.csv")
    modern = pd.read_csv(AUDIT / "modern_etf_shareclass_census.csv")
    assert len(vanguard) == 70
    usable = vanguard.loc[vanguard["usable_staggered_activation"]]
    assert len(usable) == 19
    assert usable["etf_class_launch_effective_date"].nunique() == 9
    assert len(modern.query("direction == 'mutual_to_dual_class' and status == 'launched'")) == 10
    assert len(modern.query("direction == 'etf_to_dual_class' and status == 'launched'")) == 1
    assert len(modern.query("status == 'pending'")) == 10


def test_power_audit_did_not_inspect_treatment_coefficients():
    power = pd.read_csv(AUDIT / "p1_corrected_power_audit.csv")
    assert power["variance_status"].eq("CONDITIONAL_NOT_FINAL").all()
    assert (~power["treatment_coefficients_inspected"]).all()


def test_frozen_high_dose_counts():
    cells = pd.read_csv(AUDIT / "p1_treatment_dose_cells.csv")
    all_cells = cells.query("sample == 'all_sponsors'")
    high = all_cells.loc[all_cells["high_dose_ge_0p5pct"]]
    assert len(all_cells) == 8801
    assert all_cells["permno"].nunique() == 3440
    assert all_cells["wave_id"].nunique() == 30
    assert len(high) == 583
    assert high["permno"].nunique() == 573
    assert high["wave_id"].nunique() == 4
    assert len(high.loc[~high["is_dimensional"]]) == 21
    assert high.loc[~high["is_dimensional"], "wave_id"].nunique() == 2

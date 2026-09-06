import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]
M = ROOT / "yax/manuscript/v5_1"
A = ROOT / "yax/analysis/postoutcome_v51_referee_repair"


def test_all_required_v51_deliverables_exist():
    required = [
        M / "YAX_MANUSCRIPT_v5_1_CLEAN.md",
        M / "YAX_V51_REFEREE_REPAIR_MEMO.md",
        M / "YAX_V51_ARCHITECTURE_MATRIX.md",
        M / "YAX_V51_STATEMENT_ESTIMAND_LEDGER.md",
        M / "YAX_V51_PAIRED_MDE_RECONCILIATION.md",
        A / "YAX_V51_KAPPA_AGREEMENT.csv",
        A / "YAX_V51_KAPPA_NOTE.md",
        A / "YAX_V51_FG_JOINT_MODEL_PLAN.md",
        A / "YAX_V51_FG_JOINT_MODEL_RESULTS.md",
        A / "YAX_V51_TWOWAY_CLUSTER_SENSITIVITY.md",
        M / "YAX_ATTEMPTED_MECHANISMS_AND_STOPPING_RULES.md",
        M / "YAX_V51_MAIN_TABLE_FIGURE_MAP.md",
        M / "YAX_V51_OPEN_ISSUES.md",
    ]
    assert all(path.exists() for path in required)


def test_clean_manuscript_uses_repaired_terminology_and_exact_equation():
    text = (M / "YAX_MANUSCRIPT_v5_1_CLEAN.md").read_text()
    assert "family-balanced consensus component" in text
    assert "Q_{oq}Young_aPost_t" in text
    assert "W_o Young_aPost_t" in text
    assert "strict no-renormalization" in text
    assert "43 calendar months" in text and "42 observed post months" in text
    assert "94.59%" not in text.split("## Abstract", 1)[1].split("## 1.", 1)[0]
    for internal in ("Rule A", "SC-R1", "HB-C", "FLOW-M5", "PATH-G3-B"):
        assert internal not in text


def test_mde_is_r2_and_not_misstated_as_percentage_points():
    text = (M / "YAX_V51_PAIRED_MDE_RECONCILIATION.md").read_text()
    assert "MDE-R2" in text
    assert "0.0327216 log points" in text
    assert "3.17 times" in text
    assert "replacement" in text


def test_fg_results_are_exactly_one_and_both_fixed_results_reported():
    result = json.loads((A / "YAX_V51_FG_JOINT_MODEL_RESULTS.json").read_text())
    assert result["new_labor_outcome_specification_count"] == 1
    assert result["support_occupations"] == 444
    assert result["terms"][0]["coefficient"] < 0
    assert result["terms"][1]["coefficient"] > 0
    assert result["terms"][0]["wild_score_ci_upper"] < 0
    assert result["terms"][1]["wild_score_ci_lower"] > 0


def test_stop_rule_forbids_more_empirical_work():
    text = (M / "YAX_ATTEMPTED_MECHANISMS_AND_STOPPING_RULES.md").read_text()
    assert "final permitted labor-outcome specification" in text
    assert "Remaining work is editorial" in text

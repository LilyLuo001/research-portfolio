"""Gate-0 threshold integrity.

Two failure modes this pins, both of which turn a pre-registered kill-switch into
a post-hoc one:

  * a threshold DRIFTS from the number Plan v2.1 §9 pre-committed;
  * a threshold that has never been decided gets silently defaulted by whoever
    writes R3, instead of stopping.

The null thresholds here are not an oversight. Plan §9 states G4's mass line and
G6's flatness line qualitatively only, so there is nothing to transcribe, and
picking a number after seeing the diagnostic is specification search.
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = yaml.safe_load((ROOT / "refraction" / "frozen_config.yaml").read_text())
G0 = CONFIG["gate0_thresholds"]

# Transcribed from Plan v2.1 §9 / 执行手册 §R3. Changing one of these is a
# pre-registration deviation and must be disclosed, never a quiet edit.
PLAN_COMMITTED = {
    "surprise_coverage_min": 0.95,     # §9 week 1
    "sd_L_min": 0.25,                  # §9 weeks 1-2 (joint window)
    "corr_L_convexp_max": 0.30,        # §9 weeks 1-2
    "se_share_min": 0.70,              # §9 weeks 1-2
    "n_pre_median_min": 30,            # §9 weeks 1-2 / §R3 G3 — see the conflict note
    "d_b_min": 0.10,                   # §9 week 2
    "mde_sigma_max": 0.5,              # §9 weeks 2-3
    "convexp_treated_min": 0.005,      # §5 treated line, 0.5%
    "sweep_window_min_gridpoints": 2,  # §R3 G2 "宽度<网格 2 格 → FAIL"
}

# Decided 2026-08-19 under delegation. Each must stay traceable to its memo and
# to ops/decisions.md; a silent edit to one of these is a prereg deviation.
DELEGATED = {
    "d_b_mass_share_min": 0.50,
    "pretrend_joint_p_min": 0.10,
    "pretrend_individual_lead_adjust": "holm",
}
MEMO = ROOT / "refraction" / "DECISIONS-2026-08-19.md"


@pytest.mark.parametrize("key,expected", sorted(DELEGATED.items()))
def test_delegated_decision_holds_its_recorded_value(key, expected):
    assert G0[key] == expected, (
        f"{key} is {G0[key]}, the delegated decision recorded {expected}. Changing it "
        "is a pre-registration deviation requiring disclosure.")


@pytest.mark.parametrize("key", sorted(DELEGATED))
def test_delegated_decision_is_traceable_to_a_memo_and_the_decision_log(key):
    """A number nobody can trace is indistinguishable from a number somebody
    invented after seeing a diagnostic."""
    assert MEMO.exists(), "the delegated-decision memo is missing"
    assert key in MEMO.read_text(), f"{key} not explained in {MEMO.name}"
    assert key in (ROOT / "ops" / "decisions.md").read_text(), \
        f"{key} not recorded in ops/decisions.md"


def test_the_memo_still_requires_counter_signature():
    """These were made under delegation, not by the PI. Until signed they bind
    nothing — the same standing DAX's D1 memo carries."""
    text = MEMO.read_text().lower()
    assert "counter-sign" in text or "counter-signature" in text


def test_every_gate0_threshold_is_classified():
    """A new threshold must be classified, so none can appear unnoticed."""
    unclassified = set(G0) - set(PLAN_COMMITTED) - set(DELEGATED) - {"se_to_sdL_ratio_max"}
    assert not unclassified, f"unclassified Gate-0 threshold(s): {sorted(unclassified)}"


def test_the_operationalization_of_much_less_than_is_flagged_as_a_judgement():
    """Plan §9 writes SE(β̂) ≪ SD(L̂) without defining ≪. The config defines it as
    a ratio, which is a judgement the config makes explicit rather than hides."""
    assert G0["se_to_sdL_ratio_max"] == pytest.approx(0.3333, abs=1e-4)
    assert "operationalizes" in (ROOT / "refraction" / "frozen_config.yaml").read_text()


# --------------------------------------------------------------------------- #
# sample frame — the invariant that replaces a hand-set waves_end              #
# --------------------------------------------------------------------------- #

def _add_quarters(datestr, quarters):
    """Add whole quarters to an ISO date, clamping to the target month's length
    (a naive min(day, 28) would make the bound stricter than the rule)."""
    import calendar, datetime
    d = datetime.date(*map(int, str(datestr).split("-")))
    m = d.month - 1 + 3 * quarters
    year, month = d.year + m // 12, m % 12 + 1
    return datetime.date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def test_waves_end_leaves_every_wave_its_required_post_period():
    """The bug this pins: waves_end was 2025-12-31 against announcements_end
    2026-06-30, leaving the last waves ~2 post-quarters for a design that needs
    4 — and assert A2 CANNOT catch it, because A2 measures coverage against a
    calendar truncated at the same announcements_end."""
    sample, panel = CONFIG["sample"], CONFIG["panel"]
    last_wave_needs = _add_quarters(sample["waves_end"], panel["post_quarters_required"])
    assert last_wave_needs.isoformat() <= str(sample["announcements_end"]), (
        f"a wave on waves_end {sample['waves_end']} would need announcements through "
        f"{last_wave_needs}, past announcements_end {sample['announcements_end']} — "
        f"fewer than {panel['post_quarters_required']} post-quarters")


def test_wave_window_sits_inside_the_announcement_window():
    sample = CONFIG["sample"]
    assert str(sample["announcements_start"]) < str(sample["waves_start"])
    assert str(sample["waves_end"]) < str(sample["announcements_end"])


def test_pre_and_post_coverage_requirements_are_both_declared():
    panel = CONFIG["panel"]
    assert panel["pre_quarters_required"] == 8
    assert panel["post_quarters_required"] == 4      # asymmetric by decision


def test_assert_A2_reads_the_post_bound_instead_of_mirroring_the_pre_bound():
    """A2 defaulted to a symmetric ±pre_quarters window; with an asymmetric rule
    that would have silently demanded coverage the sample frame excludes."""
    import inspect, sys
    sys.path.insert(0, str(ROOT))
    from refraction.pipeline import assert_panel as ap
    sig = inspect.signature(ap.a2_treated_coverage)
    assert "post_quarters" in sig.parameters
    src = inspect.getsource(ap.run_all)
    assert "post_quarters_required" in src and "post_quarters=post_q" in src


def test_w_shrink_is_still_unfrozen_before_gate_prereg():
    """Filling it early is the one edit that silently unblocks R6+."""
    assert CONFIG["beta"]["w_shrink"] is None
    assert CONFIG["prereg"]["osf_timestamp"] is None

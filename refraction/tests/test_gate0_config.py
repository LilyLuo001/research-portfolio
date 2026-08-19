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

# Undecided by design; R3 must refuse to run while these are null.
AWAITING_OWNER = {"d_b_mass_share_min", "pretrend_joint_p_min"}


@pytest.mark.parametrize("key,expected", sorted(PLAN_COMMITTED.items()))
def test_threshold_matches_the_pre_committed_plan_value(key, expected):
    assert key in G0, f"{key} missing from gate0_thresholds"
    assert G0[key] == expected, (
        f"{key} is {G0[key]}, Plan v2.1 pre-committed {expected}. If this change is "
        "intended it is a pre-registration deviation and must be disclosed, not edited.")


@pytest.mark.parametrize("key", sorted(AWAITING_OWNER))
def test_undecided_thresholds_stay_null_until_the_owner_decides(key):
    """If one of these acquires a value, it must arrive with an owner decision in
    ops/decisions.md — not from whoever happened to be writing R3."""
    assert key in G0, f"{key} missing; it exists to make R3 stop, not to be dropped"
    if G0[key] is not None:
        decisions = (ROOT / "ops" / "decisions.md").read_text()
        assert key in decisions, (
            f"{key} was given the value {G0[key]} but ops/decisions.md does not "
            "record the owner deciding it. Gate-0 thresholds are pre-registration "
            "content; a number chosen after seeing a diagnostic is specification search.")


def test_every_gate0_threshold_is_either_committed_or_explicitly_pending():
    """A new threshold must be classified, so none can appear unnoticed."""
    unclassified = set(G0) - set(PLAN_COMMITTED) - AWAITING_OWNER - {"se_to_sdL_ratio_max"}
    assert not unclassified, f"unclassified Gate-0 threshold(s): {sorted(unclassified)}"


def test_the_operationalization_of_much_less_than_is_flagged_as_a_judgement():
    """Plan §9 writes SE(β̂) ≪ SD(L̂) without defining ≪. The config defines it as
    a ratio, which is a judgement the config makes explicit rather than hides."""
    assert G0["se_to_sdL_ratio_max"] == pytest.approx(0.3333, abs=1e-4)
    text = (ROOT / "refraction" / "frozen_config.yaml").read_text()
    assert "operationalizes" in text


def test_shrinkage_sweep_grid_can_express_the_minimum_window_width():
    grid = CONFIG["beta"]["w_shrink_sweep_grid"]
    assert len(grid) >= G0["sweep_window_min_gridpoints"] + 1
    assert grid == sorted(grid) and grid[0] >= 0.0 and grid[-1] <= 1.0


def test_w_shrink_is_still_unfrozen_before_gate_prereg():
    """Filling it early is the one edit that silently unblocks R6+."""
    assert CONFIG["beta"]["w_shrink"] is None
    assert CONFIG["prereg"]["osf_timestamp"] is None

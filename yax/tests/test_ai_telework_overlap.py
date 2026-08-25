"""The gate that decides whether AI and remote work are separable.

Emanuel, Harrington & Pallais attribute 64% of the rise in young college-grad
unemployment to remote work rather than AI. If AI exposure and telework
feasibility measure the same occupations, the attribution in that literature is
not identified from occupation-level data. These tests pin the arithmetic and,
more importantly, pin the caveats -- a receipt that overstates separability
would send the project down a road that cannot be walked.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ai_vs_telework_overlap", ROOT / "measurement" / "ai_vs_telework_overlap.py")
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)

RECEIPT = ROOT / "measurement" / "ai_telework_overlap_receipt.json"


def test_soc_truncation_handles_both_code_widths():
    """Dingel-Neiman and Eloundou publish O*NET-SOC; AIOE publishes 6-digit SOC.
    A merge that got this wrong would silently drop everything."""
    assert G.soc6("11-1011.00") == "11-1011"
    assert G.soc6("11-1011") == "11-1011"
    assert G.soc6(" 29-1141.03 ") == "29-1141"


def test_weighted_correlation_matches_unweighted_when_weights_are_equal():
    pairs = [(1.0, 2.0), (2.0, 1.0), (3.0, 4.0), (4.0, 3.0), (5.0, 6.0)]
    assert G._corr(pairs) == pytest.approx(G._corr(pairs, [1.0] * len(pairs)))


def test_weights_actually_move_the_correlation():
    """A weighted statistic that ignores its weights is the classic silent bug."""
    pairs = [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)]
    heavy_on_discordant = G._corr(pairs, [1.0, 1.0, 50.0])
    assert heavy_on_discordant < G._corr(pairs, [1.0, 1.0, 1.0])


def test_degenerate_series_returns_none_rather_than_zero():
    """A constant series has undefined correlation. Returning 0.0 would read as
    'no relationship' and would be wrong."""
    assert G._corr([(1.0, 5.0), (2.0, 5.0), (3.0, 5.0)]) is None


# --- the findings, pinned so a re-run that moves them is visible -----------

def test_the_receipt_exists_and_covers_both_index_families():
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert "AIOE_Felten" in rec["measures"]
    assert "Eloundou_dv_rating_alpha" in rec["measures"]


def test_aioe_is_heavily_confounded_with_telework():
    """Felten's AIOE shares most of its employment-weighted variance with
    remote-work feasibility. A paper using it cannot separate the channels."""
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    aioe = rec["measures"]["AIOE_Felten"]
    assert aioe["r2_employment_weighted"] > 0.5
    assert aioe["off_diagonal_employment_share"] < 0.15


def test_the_narrow_eloundou_measure_is_separable():
    """E1 alone -- tasks the model does directly -- shares little variance with
    telework and leaves a thick off-diagonal. This is the measure any
    decomposition has to be built on."""
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    alpha = rec["measures"]["Eloundou_dv_rating_alpha"]
    assert alpha["r2_employment_weighted"] < 0.15
    assert alpha["off_diagonal_employment_share"] > 0.30


def test_separability_falls_as_the_definition_widens():
    """The substantive pattern: alpha (E1) < beta (E1+.5E2) < gamma (E1+E2).
    Broadening the definition to 'software could be built to do this' makes the
    measure progressively more of a telework proxy."""
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    m = rec["measures"]
    a = m["Eloundou_dv_rating_alpha"]["r2_employment_weighted"]
    b = m["Eloundou_dv_rating_beta"]["r2_employment_weighted"]
    g = m["Eloundou_dv_rating_gamma"]["r2_employment_weighted"]
    assert a < b < g


def test_alpha_is_not_separable_merely_for_lack_of_variation():
    """The obvious rebuttal: a near-constant measure correlates with nothing.

    Alpha has real dispersion -- only ~20% zeros and a nontrivial SD -- so its
    low overlap with telework is a fact about the measures, not an artifact.
    """
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    d = rec["distributions"]["Eloundou_dv_rating_alpha"]
    assert d["zero_share"] < 0.30
    assert d["sd"] > 0.10
    assert d["p75"] > d["median"] > 0


def test_the_receipt_flags_the_degenerate_telework_cut():
    """Most employment sits in occupations with zero teleworkable detail codes,
    so the 'median' split is not a median on that side. If the receipt implied
    a symmetric comparison it would overstate what the cells show."""
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    cut = rec["measures"]["AIOE_Felten"]["cut_points"]
    assert cut["remote_cut"] == 0
    assert "degenerate" in cut["caveat"]
    assert rec["distributions"]["teleworkable_share"]["zero_share"] > 0.5

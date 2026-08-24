"""W2-D4's variants exist to answer one question; this checks the answer is honest.

Frozen before inspection means the sensitivity is a report, never a selection.
The failure worth guarding is a summary that reads as agreement when the
underlying definitions disagree -- because that summary would license treating
the W2-D3 ordinal-band defect as a footnote when it is load-bearing.
"""
import importlib.util
import pathlib

import pytest

pytest.importorskip("pandas")
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "task_weight_variant_sensitivity",
    ROOT / "w2" / "task_weight_variant_sensitivity.py")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)


def frame(rows):
    return pd.DataFrame(rows)


def occ(name, primary, importance, n=None):
    n = n or len(primary)
    return [{"onet_soc": name, "task_id": str(i),
             "task_weight_share": p, "importance_only_share": im,
             "equal_weight_share": 1.0 / n}
            for i, (p, im) in enumerate(zip(primary, importance))]


def test_identical_definitions_report_perfect_agreement_and_no_mass_moved():
    df = frame(occ("11-1011.00", [0.6, 0.3, 0.1], [0.6, 0.3, 0.1]))
    out = V.pairwise(df, "task_weight_share", "importance_only_share")
    assert out["rank_corr"]["median"] == pytest.approx(1.0)
    assert out["mass_reallocated_fraction"]["max"] == pytest.approx(0.0)


def test_a_reversed_ordering_is_reported_as_disagreement():
    """The case that must never average away into a reassuring headline."""
    df = frame(occ("11-1011.00", [0.6, 0.3, 0.1], [0.1, 0.3, 0.6]))
    out = V.pairwise(df, "task_weight_share", "importance_only_share")
    assert out["rank_corr"]["median"] == pytest.approx(-1.0)
    assert out["mass_reallocated_fraction"]["max"] == pytest.approx(0.5)


def test_single_task_occupations_are_excluded_not_counted_as_agreement():
    """Their share is 1.0 under every definition and their rank correlation is
    undefined, not perfect. Counting them would inflate every headline here --
    and O*NET has occupations with very few rated tasks."""
    df = frame(occ("11-1011.00", [1.0], [1.0])
               + occ("29-1141.00", [0.6, 0.4], [0.4, 0.6]))
    out = V.pairwise(df, "task_weight_share", "importance_only_share")
    assert out["occupations_compared"] == 1
    assert "11-1011.00" not in [r["onet_soc"] for r in out["per_occupation"]]


def test_mass_reallocated_is_half_the_summed_absolute_gap():
    """Total variation distance: the fraction of mass that must move to turn
    one weighting into the other. Using the unhalved sum would double it."""
    df = frame(occ("11-1011.00", [0.7, 0.3], [0.5, 0.5]))
    out = V.pairwise(df, "task_weight_share", "importance_only_share")
    assert out["mass_reallocated_fraction"]["max"] == pytest.approx(0.2)


def test_a_missing_variant_stops_rather_than_comparing_a_subset():
    df = frame(occ("11-1011.00", [0.6, 0.4], [0.5, 0.5])).drop(
        columns=["equal_weight_share"])
    with pytest.raises(SystemExit):
        V.build(df)


def test_all_three_pairs_are_reported():
    df = frame(occ("11-1011.00", [0.6, 0.4], [0.5, 0.5]))
    rec = V.build(df)
    assert len(rec["pairs"]) == 3
    assert {tuple(p["pair"]) for p in rec["pairs"]} == {
        ("task_weight_share", "importance_only_share"),
        ("task_weight_share", "equal_weight_share"),
        ("importance_only_share", "equal_weight_share")}


def test_the_record_refuses_to_be_a_selection_rule():
    """W2-D1 fixes the primary. A sensitivity that could change it would break
    the reconciliation with Mapping A's coverage and the DWA bound."""
    rec = V.build(frame(occ("11-1011.00", [0.6, 0.4], [0.5, 0.5])))
    assert "never picks a weight" in rec["not_a_selection_rule"]
    assert "W2-D1" in rec["not_a_selection_rule"]


def test_the_unverified_literature_claim_is_carried_as_unverified():
    """W2-D2 recorded 0.999 as reported-not-verified because the source was
    unreachable. It must not silently become a verified fact here."""
    df = frame(occ("11-1011.00", [0.6, 0.3, 0.1], [0.5, 0.3, 0.2]))
    claim = V.build(df)["reported_literature_claim"]
    assert "not verified" in claim["status_in_W2_D2"]
    assert claim["measured_here_median_rank_corr_primary_vs_importance_only"] == \
        pytest.approx(1.0)


def test_equal_weight_reports_why_rank_correlation_is_undefined(): 
    """equal_weight_share is constant within every occupation by construction,
    so the correlation is undefined for ALL of them, not for a few odd ones.

    Without a stated reason the block would come back empty and a reader would
    read the silence as missing data rather than as a structural fact.
    """
    df = frame(occ("11-1011.00", [0.6, 0.3, 0.1], [0.5, 0.3, 0.2]))
    out = V.pairwise(df, "task_weight_share", "equal_weight_share")
    assert out["rank_corr"]["median"] is None
    assert "constant within occupation" in out["rank_corr_undefined_reason"]
    assert "mass_reallocated_fraction" in out["rank_corr_undefined_reason"]
    # The metric that still works there must still be populated.
    assert out["mass_reallocated_fraction"]["max"] > 0


def test_a_defined_pair_carries_no_undefined_reason():
    df = frame(occ("11-1011.00", [0.6, 0.3, 0.1], [0.5, 0.3, 0.2]))
    out = V.pairwise(df, "task_weight_share", "importance_only_share")
    assert out["rank_corr_undefined_reason"] is None

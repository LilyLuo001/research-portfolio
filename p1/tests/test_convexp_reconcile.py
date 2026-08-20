"""p1/reconcile — the two-construction comparison, exercised on synthetic data.

The real comparison cannot run until the CRSP pull lands. These tests build the
cases by hand so the harness's JUDGEMENT is verified before then: it must call
agreement agreement, call a one-sided construction difference what it is, and
refuse to let a moving treated set pass quietly. A harness that only gets tested
the day the data arrives is a harness that gets believed on that day.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "p1" / "reconcile"))

pytest.importorskip("pandas")
import pandas as pd  # noqa: E402

import convexp_reconcile as rc  # noqa: E402


def _free(rows):
    return pd.DataFrame(rows, columns=["cusip", "wave_id", "conv_exp"])


def _crsp(rows):
    return pd.DataFrame(rows, columns=["permno", "wave_id", "conv_exp"])


MAP = {"00036020": "10001", "00036110": "10002", "00081T10": "10003"}


# --------------------------------------------------------------------------- #
# agreement                                                                    #
# --------------------------------------------------------------------------- #
def test_clean_agreement_is_called_agreement():
    free = _free([("000360206", "W002", 0.0100), ("000361105", "W002", 0.0050),
                  ("00081T108", "W002", 0.0020)])
    crsp = _crsp([("10001", "W002", 0.01002), ("10002", "W002", 0.00499),
                  ("10003", "W002", 0.00200)])
    rep = rc.reconcile(free, crsp, MAP)
    rep["verdict"] = rc.verdict(rep)
    assert rep["cells"]["matched_both"] == 3
    assert rep["agreement"]["share_within_1pct"] == 1.0
    assert any("AGREE" in v for v in rep["verdict"])


def test_material_disagreement_refuses_to_average():
    free = _free([("000360206", "W002", 0.010), ("000361105", "W002", 0.020),
                  ("00081T108", "W002", 0.030)])
    crsp = _crsp([("10001", "W002", 0.004), ("10002", "W002", 0.009),
                  ("10003", "W002", 0.011)])
    rep = rc.reconcile(free, crsp, MAP)
    v = " ".join(rc.verdict(rep))
    assert "DISAGREE" in v
    assert "do not average" in v.lower()


# --------------------------------------------------------------------------- #
# the bug signature: a one-sided gap is not noise                              #
# --------------------------------------------------------------------------- #
def _paired(n, gaps):
    """n synthetic cells with a given signed gap per cell (free = crsp + gap)."""
    cus = [f"{i:08d}0" for i in range(n)]
    m = {c[:8]: str(20000 + i) for i, c in enumerate(cus)}
    base = [0.004 + 0.0001 * i for i in range(n)]
    free = _free([(c, "W002", b + g) for c, b, g in zip(cus, base, gaps)])
    crsp = _crsp([(m[c[:8]], "W002", b) for c, b in zip(cus, base)])
    return free, crsp, m


def test_one_sided_gap_is_flagged_as_a_construction_difference():
    """Every free value above CRSP, over enough cells to rule out chance — the
    signature of a denominator-date or share-class mismatch."""
    n = 12
    free, crsp, m = _paired(n, [0.00005] * n)
    rep = rc.reconcile(free, crsp, m)
    assert rep["systematic"]["free_higher_share"] == 1.0
    assert rep["systematic"]["sign_test_p"] < 0.01
    assert any("ONE-SIDED" in v for v in rc.verdict(rep))


def test_symmetric_noise_is_not_flagged_as_one_sided():
    n = 12
    gaps = [0.00005 if i % 2 else -0.00005 for i in range(n)]
    free, crsp, m = _paired(n, gaps)
    rep = rc.reconcile(free, crsp, m)
    assert rep["systematic"]["sign_test_p"] > 0.01
    assert not any("ONE-SIDED" in v for v in rc.verdict(rep))


def test_too_few_cells_cannot_establish_one_sidedness():
    """Three all-higher cells is p=0.25 — the harness must stay quiet rather than
    manufacture a finding from a sample that cannot support one."""
    n = 3
    free, crsp, m = _paired(n, [0.00005] * n)
    rep = rc.reconcile(free, crsp, m)
    assert rep["systematic"]["free_higher_share"] == 1.0
    assert rep["systematic"]["sign_test_p"] > 0.01
    assert not any("ONE-SIDED" in v for v in rc.verdict(rep))


def test_sign_test_matches_hand_computed_values():
    assert rc.sign_test_p(3, 3) == pytest.approx(0.25)      # 2 * 1/8
    assert rc.sign_test_p(12, 12) == pytest.approx(2 / 4096)
    assert rc.sign_test_p(6, 12) == pytest.approx(1.0)
    assert rc.sign_test_p(0, 0) == 1.0


# --------------------------------------------------------------------------- #
# the sample the paper keys on                                                 #
# --------------------------------------------------------------------------- #
def test_moving_treated_set_is_surfaced_not_buried():
    """Cells can agree loosely while the >=0.5% treated set changes membership —
    that is a sample-definition fact, not a rounding detail."""
    free = _free([("000360206", "W002", 0.0060), ("000361105", "W002", 0.0045),
                  ("00081T108", "W002", 0.0055)])
    crsp = _crsp([("10001", "W002", 0.0045), ("10002", "W002", 0.0060),
                  ("10003", "W002", 0.0040)])
    rep = rc.reconcile(free, crsp, MAP)
    j = rep["treated_sets"]["ge_0.005"]
    assert j["jaccard"] < 0.8
    assert any("TREATED SET MOVES" in v for v in rc.verdict(rep))


# --------------------------------------------------------------------------- #
# coverage bookkeeping                                                         #
# --------------------------------------------------------------------------- #
def test_unmapped_and_one_sided_cells_are_counted_not_dropped_silently():
    free = _free([("000360206", "W002", 0.01), ("999999999", "W002", 0.02)])
    crsp = _crsp([("10001", "W002", 0.01), ("10009", "W002", 0.03)])
    rep = rc.reconcile(free, crsp, MAP)
    c = rep["cells"]
    assert c["free_unmapped"] == 1        # no permno for 999999999
    assert c["crsp_only"] == 1            # permno 10009 has no free counterpart
    assert c["matched_both"] == 1


def test_no_overlap_says_so_rather_than_reporting_a_vacuous_pass():
    free = _free([("000360206", "W002", 0.01)])
    crsp = _crsp([("10009", "W055", 0.01)])
    rep = rc.reconcile(free, crsp, MAP)
    assert rep["cells"]["matched_both"] == 0
    assert any("NO OVERLAP" in v for v in rc.verdict(rep))


def test_crosswalk_loads_only_rows_that_carry_a_permno():
    """The committed crosswalk has permno blank everywhere (no CRSP yet) — the
    loader must yield nothing rather than mapping CUSIPs to empty strings."""
    m = rc.load_crosswalk()
    assert all(v for v in m.values())

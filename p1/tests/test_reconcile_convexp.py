"""Reconciliation of the two independent ConvExp constructions.

Runs entirely offline — this comparison never needs WRDS once both builds exist,
which is the point: the check has to be reproducible by anyone holding the two
outputs. Bands are pre-committed in the module; these tests pin the arithmetic
and the identifier handling, not the verdict.
"""
import csv
import pathlib

import pandas as pd
import pytest

import holdings_pipeline as hp
import reconcile_convexp as rc

S_NAMES = hp.SCHEMA["security_names"]


class FakeDB:
    def __init__(self, names):
        self.names = names
        self.seen = []

    def raw_sql(self, sql):
        self.seen.append(" ".join(sql.split()))
        return self.names.copy()


def names_df(rows):
    return pd.DataFrame(rows, columns=[S_NAMES["permno"], S_NAMES["ncusip"]])


def free(cusip, wave, exp):
    return {"cusip": cusip, "wave_id": wave, "conv_exp": exp}


def wrds(permno, wave, exp):
    return {"permno": permno, "wave_id": wave, "conv_exp": exp}


MAP = [(101, "03783310")]          # 8-char historical CUSIP, as CRSP stores it
CUSIP9 = "037833100"               # 9-char with check digit, as N-PORT reports it


# --------------------------------------------------------------------------- #
# the identifier trap                                                          #
# --------------------------------------------------------------------------- #

def test_check_digit_does_not_silently_destroy_every_match():
    """CRSP ncusip is 8 characters, N-PORT's CUSIP is 9. Comparing them raw
    matches nothing — and 'the two paths share no stocks' would look like a
    finding rather than an artefact of a check digit."""
    assert rc.normalize_cusip(CUSIP9) == rc.normalize_cusip("03783310") == "03783310"
    cells = rc.reconcile([free(CUSIP9, "W001", 0.010)], [wrds(101, "W001", 0.010)], MAP)
    assert len(cells) == 1 and cells[0]["status"] == "agree"


@pytest.mark.parametrize("bad", [None, "", "  ", "123"])
def test_unusable_cusips_are_dropped_not_padded(bad):
    assert rc.normalize_cusip(bad) == ""


def test_a_permno_with_several_historical_cusips_still_matches():
    """A security that was renamed carries more than one ncusip; the free path
    recorded whichever the fund reported at the time."""
    cells = rc.reconcile([free("11111111", "W001", 0.01)],
                         [wrds(101, "W001", 0.01)],
                         [(101, "99999999"), (101, "11111111")])
    assert cells[0]["status"] == "agree"


# --------------------------------------------------------------------------- #
# classification                                                               #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("f,w,expected", [
    (0.01000, 0.01000, "agree"),
    (0.01000, 0.01005, "agree"),        # 0.5% relative gap
    (0.01000, 0.01080, "close"),        # 8%
    (0.01000, 0.01500, "investigate"),  # 50%
    (0.0, 0.0, "agree"),
])
def test_bands(f, w, expected):
    assert rc.classify(f, w) == expected


def test_bands_are_frozen_at_the_values_committed_before_any_data_existed():
    """If these change, it is a disclosed deviation — not a tweak."""
    assert (rc.AGREE_BAND, rc.CLOSE_BAND, rc.TREATED_LINE) == (0.01, 0.10, 0.005)
    assert rc.TREATED_AGREEMENT_FLOOR == 0.95


# --------------------------------------------------------------------------- #
# coverage asymmetry is an output, not an error                                #
# --------------------------------------------------------------------------- #

def test_one_sided_cells_are_labelled_by_which_path_had_them():
    cells = rc.reconcile([free(CUSIP9, "W001", 0.01), free("22222222", "W001", 0.02)],
                         [wrds(101, "W001", 0.01), wrds(303, "W001", 0.03)],
                         MAP)
    by_status = {c["status"] for c in cells}
    assert by_status == {"agree", "free_only", "wrds_only"}
    s = rc.summarize(cells)
    assert s["cells_both_paths"] == 1 and s["cells_total"] == 3


def test_same_stock_in_a_different_wave_is_not_matched_across_waves():
    cells = rc.reconcile([free(CUSIP9, "W001", 0.01)], [wrds(101, "W002", 0.01)], MAP)
    assert {c["status"] for c in cells} == {"free_only", "wrds_only"}


# --------------------------------------------------------------------------- #
# the headline test                                                            #
# --------------------------------------------------------------------------- #

def test_treated_call_agreement_is_what_the_verdict_keys_on():
    """Both paths can differ on the third decimal and still agree on the only
    question the study asks of ConvExp: is this stock treated?"""
    cells = rc.reconcile([free(CUSIP9, "W001", 0.0060)], [wrds(101, "W001", 0.0075)], MAP)
    assert cells[0]["status"] == "investigate"        # 20% apart
    s = rc.summarize(cells)
    assert s["treated_call_agreement"] == 1.0 and s["verdict"] == "PASS"


def test_disagreement_across_the_treated_line_flags():
    cells = rc.reconcile([free(CUSIP9, "W001", 0.0049)], [wrds(101, "W001", 0.0051)], MAP)
    s = rc.summarize(cells)
    assert s["treated_call_agreement"] == 0.0 and s["verdict"] == "FLAG"


def test_no_overlap_is_its_own_verdict_not_a_pass():
    """Zero comparable cells must never read as success."""
    s = rc.summarize(rc.reconcile([free("22222222", "W001", 0.01)], [], MAP))
    assert s["verdict"] == "NO_OVERLAP" and s["treated_call_agreement"] is None


# --------------------------------------------------------------------------- #
# map building + outputs                                                       #
# --------------------------------------------------------------------------- #

def test_build_map_normalizes_and_drops_unusable_rows(tmp_path):
    db = FakeDB(names_df([[101, "037833100"], [202, None], [303, "88160R10"]]))
    rows, _ = rc.build_map(db, path=tmp_path / "map.csv")
    assert {r["permno"] for r in rows} == {101, 303}
    written = list(csv.DictReader((tmp_path / "map.csv").open()))
    assert written[0]["ncusip"] == "03783310"


def test_map_query_filters_nulls_and_is_valid_sql_shape():
    sql = " ".join(rc.sql_permno_cusip_map().split())
    assert sql.count(" where ") == 1
    assert f"{S_NAMES['ncusip']} is not null" in sql
    scoped = " ".join(rc.sql_permno_cusip_map([101, 202]).split())
    assert scoped.count(" where ") == 1 and " and " in scoped
    assert "101, 202" in scoped


def test_report_states_the_bands_and_the_verdict(tmp_path):
    cells = rc.reconcile([free(CUSIP9, "W001", 0.01)], [wrds(101, "W001", 0.01)], MAP)
    summary = rc.summarize(cells)
    md, csvp = tmp_path / "r.md", tmp_path / "r.csv"
    rc.write_report(cells, summary, report=md, cells_csv=csvp)
    body = md.read_text()
    assert "verdict: PASS" in body
    assert "fixed before any number existed" in body
    assert len(list(csv.DictReader(csvp.open()))) == 1

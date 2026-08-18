"""P1-T2 wave construction: the file defines ONE program, and it produces the
four-column waves.csv the rest of the pipeline reads.

Background (coverage-audit caveat 2): waves.csv was committed corrupt — two
concatenated schemas in one file — because build_waves.py itself held two
complete programs, and the second `def main()` (a 7-column scaffold that never
wrote waves_members.csv and skipped the sanity asserts) shadowed the real one.
The audit regenerated the CSV by hand but flagged that the pipeline would
re-corrupt it. These tests pin the fix.
"""
import ast
import csv
import logging
import pathlib

import pytest

import build_waves as bw

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "p1" / "t2_wrds" / "build_waves.py"

EVENT_FIELDS = ["fund_name", "family", "effective_date", "effective_date_approx",
                "mutual_fund_ticker", "etf_ticker", "source_accession", "source_url"]


def write_events(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in EVENT_FIELDS})


def event(name, eff, **kw):
    r = {"fund_name": name, "effective_date": eff, "family": "Fam",
         "etf_ticker": "ETF", "source_accession": "0001-24-000001"}
    r.update(kw)
    return r


@pytest.fixture
def run(tmp_path, monkeypatch):
    def _run(rows):
        ev, waves, members = (tmp_path / "events.csv", tmp_path / "waves.csv",
                              tmp_path / "members.csv")
        write_events(ev, rows)
        monkeypatch.setattr(bw, "EVENTS", ev)
        monkeypatch.setattr(bw, "WAVES", waves)
        monkeypatch.setattr(bw, "MEMBERS", members)
        monkeypatch.setattr(bw, "LOGFILE", tmp_path / "build_waves.log")
        monkeypatch.setattr(bw, "_setup_run", lambda: None)
        bw.main()
        with open(waves, newline="") as f:
            wv = list(csv.reader(f))
        with open(members, newline="") as f:
            mb = list(csv.DictReader(f))
        return wv, mb
    return _run


# --------------------------------------------------------------------------- #
# the corruption itself                                                        #
# --------------------------------------------------------------------------- #

def test_source_file_defines_exactly_one_main():
    tree = ast.parse(SRC.read_text())
    mains = [n for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name == "main"]
    assert len(mains) == 1, "a second main() shadows the real one — see caveat 2"


def test_source_file_has_no_stray_second_module_docstring():
    """A bare string expression after the imports is the fingerprint of two
    concatenated programs (the same defect fixed in build_nport_convexp.py)."""
    tree = ast.parse(SRC.read_text())
    stray = [n for n in tree.body[1:]
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
             and isinstance(n.value.value, str)]
    assert stray == []


def test_importing_the_module_does_not_open_the_committed_run_log():
    attached = [h for h in logging.getLogger().handlers
                if isinstance(h, logging.FileHandler)
                and pathlib.Path(getattr(h, "baseFilename", "")) == bw.LOGFILE]
    assert attached == []


# --------------------------------------------------------------------------- #
# behaviour                                                                    #
# --------------------------------------------------------------------------- #

def test_waves_csv_has_the_four_column_schema(run):
    wv, _ = run([event("A Fund", "2021-06-11")])
    assert wv[0] == ["wave_id", "effective_date", "n_funds", "is_anchor"]


def test_same_date_funds_share_one_wave_and_ids_run_in_date_order(run):
    wv, mb = run([event("B Fund", "2021-09-10"),
                  event("A Fund", "2021-06-11"),
                  event("C Fund", "2021-06-11")])
    assert [r[0] for r in wv[1:]] == ["W001", "W002"]
    assert wv[1][:3] == ["W001", "2021-06-11", "2"]
    assert wv[2][:3] == ["W002", "2021-09-10", "1"]
    assert len(mb) == 3


def test_anchor_wave_is_flagged(run):
    wv, _ = run([event("A Fund", "2021-06-11"), event("B Fund", "2022-01-03")])
    flags = {r[1]: r[3] for r in wv[1:]}
    assert flags["2021-06-11"] == "1" and flags["2022-01-03"] == "0"


@pytest.mark.parametrize("bad", ["NA", "", "2021-06", "June 2021", "  "])
def test_rows_without_an_iso_date_are_held_back_not_guessed(run, bad):
    """No interpolation of timing (Project_1.md §113) — an approximate date must
    never place a fund in a wave."""
    wv, mb = run([event("Good", "2021-06-11"),
                  event("Vague", bad, effective_date_approx="mid-2021")])
    assert len(wv) == 2                       # header + one wave
    assert [r["fund_name"] for r in mb] == ["Good"]


def test_members_carry_the_provenance_columns(run):
    _, mb = run([event("A Fund", "2021-06-11", source_url="https://sec.gov/x",
                       mutual_fund_ticker="AAAAX")])
    m = mb[0]
    assert m["source_accession"] == "0001-24-000001"
    assert m["source_url"] == "https://sec.gov/x"
    assert m["mutual_fund_ticker"] == "AAAAX"


# --------------------------------------------------------------------------- #
# the committed artifact                                                       #
# --------------------------------------------------------------------------- #

def test_committed_waves_csv_matches_the_pipeline_schema():
    with open(ROOT / "p1" / "t2_wrds" / "waves.csv", newline="") as f:
        header = next(csv.reader(f))
    assert header == ["wave_id", "effective_date", "n_funds", "is_anchor"]


def test_committed_waves_and_members_agree_on_wave_ids_and_counts():
    base = ROOT / "p1" / "t2_wrds"
    with open(base / "waves.csv", newline="") as f:
        waves = {r["wave_id"]: r for r in csv.DictReader(f)}
    with open(base / "waves_members.csv", newline="") as f:
        members = list(csv.DictReader(f))
    counts = {}
    for m in members:
        counts[m["wave_id"]] = counts.get(m["wave_id"], 0) + 1
    assert set(counts) == set(waves)
    assert all(int(waves[w]["n_funds"]) == counts[w] for w in waves)

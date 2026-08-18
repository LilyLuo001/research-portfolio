"""P1-T2 free path — offline guards for the drop path and the wave builder.

The ConvExp pipeline itself only runs on the box (it needs outbound HTTPS to
EDGAR). These tests exercise the parts that must be right BEFORE that run, with
synthetic inputs and no network, so the box run is not the first execution of
the drop-path patch.

What is guarded here:
  1. every dropped (cusip, wave) cell keeps shares_held / valUSD / n_funds —
     a drop is a missing DENOMINATOR, never a missing holding, and
     recover_denominators.py --online needs those to recompute ConvExp;
  2. NEED_HUMAN_stocks.csv keeps its frozen 4-column schema (the coverage audit
     and recover_denominators.py both read it) — schema contract, CLAUDE.md #3;
  3. build_waves.py defines exactly one main() and round-trips waves.csv +
     waves_members.csv (it was merge-corrupted into two modules once already).
"""
import ast
import csv
import importlib.util
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "p1" / "t2_free" / "build_nport_convexp.py"
BUILD_WAVES = ROOT / "p1" / "t2_wrds" / "build_waves.py"


@pytest.fixture(scope="module")
def mod(tmp_path_factory):
    """Import the pipeline with its run log redirected.

    The module configures logging at import with FileHandler(mode="w"), and the
    committed run log is an audit input (the coverage audit parses CONVEXP_GT1
    lines out of it) — importing without T2FREE_LOG would truncate it.
    """
    pytest.importorskip("pandas")
    pytest.importorskip("requests")
    tmp = tmp_path_factory.mktemp("t2free")
    import os
    os.environ["T2FREE_LOG"] = str(tmp / "run.log")
    spec = importlib.util.spec_from_file_location("t2free_pipeline", PIPELINE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _cell(shares=1_000.0, valusd=25_000.0, funds=("Fund A", "Fund B")):
    return {"cusip": "037833100", "wave_id": "W002", "effective_date": "2021-06-11",
            "ticker": "AAPL", "name": "APPLE INC", "shares_held": shares,
            "valusd": valusd, "funds": set(funds), "accs": {"0001-21-000001"}}


# --------------------------------------------------------------------------- #
# 1. the drop path retains the quantities                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("reason", [
    "no_ticker", "ticker_not_in_sec_map", "no_xbrl_shares_outstanding"])
def test_dropped_cell_keeps_shares_and_value(mod, reason):
    a = _cell()
    row = mod._dropped(a, a["cusip"], a["ticker"], a["wave_id"],
                       a["effective_date"], reason)
    assert row["shares_held"] == 1_000.0
    assert row["valusd"] == 25_000.0
    assert row["n_funds"] == 2
    assert row["effective_date"] == "2021-06-11"
    assert row["reason"] == reason
    # not a conv_exp>1 drop, so no denominator to report
    assert row["shares_out_bad"] == ""


def test_dropped_gt1_cell_reports_the_rejected_denominator(mod):
    a = _cell(shares=2_000.0)
    row = mod._dropped(a, a["cusip"], a["ticker"], a["wave_id"],
                       a["effective_date"], "conv_exp>1 (2.000); shares_out date 2021-05-01",
                       shares_out_bad=1_000.0, shares_out_date="2021-05-01")
    assert row["shares_out_bad"] == 1_000.0
    assert row["shares_out_date"] == "2021-05-01"
    # the whole point: ConvExp is recomputable once a real denominator arrives
    assert row["shares_held"] / row["shares_out_bad"] == 2.0


def test_sidecar_and_need_human_schemas(mod, tmp_path, monkeypatch):
    """Sidecar carries the quantities; NEED_HUMAN_stocks.csv stays 4 columns."""
    nh = tmp_path / "NEED_HUMAN_stocks.csv"
    side = tmp_path / "dropped_cells_shares_held.csv"
    monkeypatch.setattr(mod, "NH_STOCKS", nh)
    monkeypatch.setattr(mod, "DROPPED_CELLS", side)

    a = _cell()
    rows = [mod._dropped(a, a["cusip"], a["ticker"], "W002", "2021-06-11",
                         "ticker_not_in_sec_map"),
            mod._dropped(_cell(shares=7.0, valusd=91.0, funds=("Solo Fund",)),
                         "88160R101", "TSLA", "W008", "2022-05-20",
                         "no_xbrl_shares_outstanding")]
    mod._write_need_human([], rows)

    with open(nh, newline="") as f:
        nh_rows = list(csv.DictReader(f))
    assert list(nh_rows[0]) == ["cusip", "ticker", "wave_id", "reason"], \
        "NEED_HUMAN_stocks.csv schema is frozen — downstream readers key on it"
    assert len(nh_rows) == 2

    with open(side, newline="") as f:
        side_rows = list(csv.DictReader(f))
    assert len(side_rows) == 2
    assert float(side_rows[0]["shares_held"]) == 1_000.0
    assert float(side_rows[0]["valusd"]) == 25_000.0
    assert float(side_rows[1]["shares_held"]) == 7.0
    assert side_rows[1]["n_funds"] == "1"
    # recover_denominators.py --shares-held reads exactly these three keys
    for k in ("cusip", "wave_id", "shares_held"):
        assert k in side_rows[0]


def test_computed_rows_carry_valusd(mod):
    """valUSD must reach the parquet or value-weighted coverage stays impossible."""
    src = PIPELINE.read_text()
    assert '"valusd": a["valusd"],' in src, \
        "computed ConvExp rows must retain valUSD (coverage audit caveat 1)"


# --------------------------------------------------------------------------- #
# 2. neither script may be merge-corrupted into two modules again              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", [PIPELINE, BUILD_WAVES])
def test_single_main_definition(path):
    tree = ast.parse(path.read_text())
    mains = [n for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name == "main"]
    assert len(mains) == 1, f"{path.name} has {len(mains)} module-level main() defs"
    # a stray docstring-shaped expression mid-module is the corruption signature
    strays = [n for n in tree.body[1:]
              if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
              and isinstance(n.value.value, str)]
    assert not strays, f"{path.name} has {len(strays)} orphan string literal(s)"


# --------------------------------------------------------------------------- #
# 3. build_waves.py round-trips its committed outputs                          #
# --------------------------------------------------------------------------- #
def test_build_waves_reproduces_committed_artifacts(tmp_path):
    waves = ROOT / "p1" / "t2_wrds" / "waves.csv"
    members = ROOT / "p1" / "t2_wrds" / "waves_members.csv"
    before = (waves.read_bytes(), members.read_bytes())
    subprocess.run([sys.executable, str(BUILD_WAVES)], check=True,
                   capture_output=True, cwd=ROOT)
    assert waves.read_bytes() == before[0], "waves.csv is not reproducible"
    assert members.read_bytes() == before[1], "waves_members.csv is not reproducible"

    with open(waves, newline="") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == ["wave_id", "effective_date", "n_funds", "is_anchor"]
    anchors = [r for r in rows if r["is_anchor"] == "1"]
    assert len(anchors) == 1 and anchors[0]["effective_date"] == "2021-06-11", \
        "the DFA anchor wave must be present and unique"

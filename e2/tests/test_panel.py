"""E2-T6a: the 15-assertion battery passes on a well-formed panel, catches
corruption, and the panel satisfies the frozen panel_daily contract."""
import importlib.util
import pathlib
import pandas as pd

from build_panel import build_panel
from assert_panel import run_assertions

ROOT = pathlib.Path(__file__).resolve().parents[2]   # project root (= repo root)


def _load_contracts():
    spec = importlib.util.spec_from_file_location(
        "contracts", ROOT / "ops" / "runner" / "contracts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_all_15_assertions_pass_with_full_context():
    panel, ctx = build_panel(seed=0)
    results = run_assertions(panel, ctx)
    assert len(results) == 15
    fails = [r.aid for r in results if r.status == "FAIL"]
    skips = [r.aid for r in results if r.status == "SKIP"]
    assert not fails, f"unexpected failures: {fails}"
    assert not skips, f"context incomplete, skipped: {skips}"


def test_negative_control_spread_identity():
    panel, ctx = build_panel(seed=0)
    panel.loc[panel.index[0], "spread"] += 1.0      # break A11 (and A15 trace)
    status = {r.aid: r.status for r in run_assertions(panel, ctx)}
    assert status["A11"] == "FAIL"


def test_negative_control_pk_uniqueness():
    panel, ctx = build_panel(seed=0)
    panel = pd.concat([panel, panel.iloc[[0]]], ignore_index=True)
    status = {r.aid: r.status for r in run_assertions(panel, ctx)}
    assert status["A1"] == "FAIL"


def test_negative_control_leverage_ordering():
    panel, ctx = build_panel(seed=0)
    i = panel.index[panel.net_usd > 0][0]
    panel.loc[i, "net_usd"] = panel.loc[i, "gross_usd"] * 2   # net > gross
    status = {r.aid: r.status for r in run_assertions(panel, ctx)}
    assert status["A3"] == "FAIL"


def test_panel_satisfies_frozen_contract(tmp_path):
    panel, _ = build_panel(seed=0)
    out = tmp_path / "panel_daily.parquet"
    panel.to_parquet(out, index=False)
    contracts = _load_contracts()
    assert contracts.check("panel_daily", str(out)) == 0

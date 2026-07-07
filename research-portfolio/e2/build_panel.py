"""build_panel.py — E2-T6a: construct panel_daily (market_id × UTC day).

Real inputs (produced upstream by E2-T4b holders, E2-T6b NAV, plus flows /
decomposition / rates / registry / oracle_updates) are merged into one daily
panel. Those upstream files don't exist yet, so this module also ships a
`synth_inputs()` generator that emits an *internally consistent* set of upstream
frames — consistent enough that all 15 assertions in assert_panel.py actually
run and pass. That makes the whole T6a pipeline runnable and testable today; when
the real extractions land, point `build_panel(...)` at them instead.

The frozen handshake schema is ops/contracts/panel_daily.yaml (a subset); the
full column list and the A1–A15 battery come from the E2 manual (T6a).
"""
import numpy as np
import pandas as pd

PANEL_COLUMNS = [
    "market_id", "date", "gross_usd", "net_usd", "lambda", "utilization",
    "borrow_apy", "supply_apy", "rwa_apy", "spread", "hhi", "top10_share",
    "contract_share", "nav", "nav_source", "oracle_staleness_hours",
    "lambda_k", "is_active",
]

# markets: (id, nav regime, launch, #active days before an inactive tail)
_SPECS = [
    ("mF-ONE", "accrual",  "2025-01-01", 0),
    ("USTB",   "accrual",  "2025-01-15", 0),
    ("JAAA",   "rebasing", "2025-02-01", 5),   # last 5 interval days redeemed -> inactive
]
_SAMPLE_END = "2025-03-31"


def synth_inputs(seed=0):
    """Return (panel, ctx) where ctx = {flows, registry, decomposition, manifest}.

    Everything is constructed so the A1–A15 assertions hold by construction:
    flows equal the exact day-over-day gross change (A10), net = gross/lambda so
    lambda = gross/net (A3), spread = rwa_apy - borrow_apy (A11), accrual NAV is
    monotone / rebasing NAV sits in [0.98,1.02] (A7), lambda_k matches the
    decomposition config (A12), and the manifest row count matches (A13).
    """
    rng = np.random.default_rng(seed)
    end = pd.Timestamp(_SAMPLE_END)
    panel_rows, flows_rows, registry_rows, decomp_rows = [], [], [], []
    manifest = {"markets": {}, "total_rows": 0}

    for mid, regime, launch, inactive_tail in _SPECS:
        dates = pd.date_range(pd.Timestamp(launch), end, freq="D")
        n = len(dates)
        k = float(rng.integers(2, 5))                      # decomposition k param
        decomp_rows.append({"market_id": mid, "k": k})
        registry_rows.append({"market_id": mid, "accrual": regime == "accrual"})

        prev_gross = 0.0
        nav = 1.0
        active_cut = n - inactive_tail
        for i, d in enumerate(dates):
            active = i < active_cut
            if active:
                target = 5e7 * (1 + 0.02 * np.sin(i / 7)) + rng.normal(0, 3e5)
                gross = max(1e6, target)
                lam = float(np.round(rng.uniform(1.4, 3.2), 4))
                net = gross / lam
                util = float(np.clip(rng.uniform(0.4, 0.9), 0, 1))
                borrow = float(rng.uniform(0.03, 0.12))
                rwa = float(rng.uniform(0.045, 0.09))
                supply = borrow * util * 0.9
                hhi = float(rng.uniform(0.05, 0.35))
                top10 = float(rng.uniform(0.55, 0.95))
                contract = float(rng.uniform(0.0, 0.3))
            else:                                          # redeemed / inactive day
                gross = net = lam = util = borrow = rwa = supply = 0.0
                hhi = top10 = contract = np.nan
                lam = np.nan

            net_flow = gross - prev_gross                  # A10 reconciles exactly
            prev_gross = gross

            if regime == "accrual":
                nav = nav + abs(rng.normal(2e-4, 5e-5))    # monotone non-decreasing
            else:
                nav = float(np.clip(1.0 + rng.normal(0, 0.004), 0.985, 1.015))

            panel_rows.append({
                "market_id": mid, "date": d,
                "gross_usd": gross, "net_usd": net,
                "lambda": (gross / net) if net > 0 else np.nan,
                "utilization": util if active else 0.0,
                "borrow_apy": borrow, "supply_apy": supply, "rwa_apy": rwa,
                "spread": rwa - borrow,
                "hhi": hhi, "top10_share": top10, "contract_share": contract,
                "nav": nav, "nav_source": "issuer_doc",
                "oracle_staleness_hours": float(rng.uniform(0, 20)),
                "lambda_k": k,
                "is_active": bool(active),
            })
            flows_rows.append({"market_id": mid, "date": d, "net_flow_usd": net_flow})

        manifest["markets"][mid] = {"interval_days": n, "accrual": regime == "accrual"}
        manifest["total_rows"] += n

    panel = pd.DataFrame(panel_rows)[PANEL_COLUMNS]
    ctx = {
        "flows": pd.DataFrame(flows_rows),
        "registry": pd.DataFrame(registry_rows),
        "decomposition": pd.DataFrame(decomp_rows),
        "manifest": manifest,
    }
    return panel, ctx


def build_panel(inputs=None, seed=0):
    """Construct the panel. With no `inputs` dict, uses synth_inputs() so the
    pipeline is runnable end-to-end today. With real upstream frames, merge them
    here (holders->hhi/top10, flows->gross, nav_daily->nav, rates->apys, ...).

    Returns (panel_df, ctx) so assert_panel.py can reconcile against upstream.
    """
    if inputs is None:
        return synth_inputs(seed)
    raise NotImplementedError(
        "wire the real merge once E2-T4b (holders) and E2-T6b (nav_daily) land")


if __name__ == "__main__":
    import argparse, pathlib
    from assert_panel import run_assertions, format_results
    ap = argparse.ArgumentParser(description="build panel_daily + run the 15 assertions")
    ap.add_argument("--demo", metavar="OUT", help="write a synthetic demo panel to OUT (.parquet/.csv)")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    panel, ctx = build_panel(seed=a.seed)
    results = run_assertions(panel, ctx)
    print(format_results(results))
    if any(r.status == "FAIL" for r in results):
        raise SystemExit("assertions FAILED — panel not written")
    if a.demo:
        out = pathlib.Path(a.demo)
        if out.suffix == ".parquet":
            panel.to_parquet(out, index=False)
        else:
            panel.to_csv(out, index=False)
        print(f"wrote {out} ({len(panel)} rows) — all 15 assertions passed")

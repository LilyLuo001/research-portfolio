#!/usr/bin/env python3
"""Rebuild aggregate intervals from saved daily losses with common date draws."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("futures_models", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--roster", required=True, type=Path)
    ap.add_argument("--model-code", required=True, type=Path)
    args = ap.parse_args()

    daily = pd.read_csv(args.root / "DAILY_LOSS_DIFFERENCES.csv", dtype={"date": str})
    roster = pd.read_csv(args.roster)
    weights = roster.set_index("symbol").report_weight.astype(float).to_dict()
    model = load_module(args.model_code)
    aggregate, sensitivity = model.aggregate_daily(daily, weights)
    aggregate.to_csv(args.root / "AGGREGATE_COMPARISON.csv", index=False)
    sensitivity.to_csv(args.root / "DATE_SENSITIVITY.csv", index=False)
    receipt_path = args.root / "MODEL_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["output_hashes"]["AGGREGATE_COMPARISON.csv"] = sha256(args.root / "AGGREGATE_COMPARISON.csv")
    receipt["output_hashes"]["DATE_SENSITIVITY.csv"] = sha256(args.root / "DATE_SENSITIVITY.csv")
    receipt["bootstrap"] = {
        "repetitions": 2000,
        "seed": model.BOOTSTRAP_SEED,
        "unit": "whole test date",
        "common_draws_across_venue_grid_family_cutoff_support": True,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print({"aggregate_rows": len(aggregate), "date_sensitivity_rows": len(sensitivity),
           "bootstrap_seed": model.BOOTSTRAP_SEED, "common_date_draws": True})


if __name__ == "__main__":
    main()

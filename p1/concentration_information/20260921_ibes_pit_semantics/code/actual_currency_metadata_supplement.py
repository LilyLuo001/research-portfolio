#!/usr/bin/env python3
"""Actuals-only verified currency-metadata supplement; reads no values or Detail."""
import argparse
import json
from pathlib import Path
import pandas as pd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--actual", type=Path, required=True)
    p.add_argument("--private-projection", type=Path, required=True)
    p.add_argument("--aggregate", type=Path, required=True)
    a = p.parse_args()
    x = pd.read_parquet(a.actual, columns=["curr_act", "measure", "pdicity"])
    x["measure"] = x["measure"].astype("string").str.strip().str.upper()
    x["pdicity"] = x["pdicity"].astype("string").str.strip().str.upper()
    q = x[x["measure"].eq("EPS") & x["pdicity"].eq("QTR")].copy()
    counts = q["curr_act"].astype("string").str.strip().str.upper().fillna("<MISSING>").value_counts(dropna=False).sort_index()
    a.private_projection.parent.mkdir(parents=True, exist_ok=True)
    q.to_parquet(a.private_projection, index=False)
    a.aggregate.write_text(json.dumps({"source": "ibes.actu_epsus 2023 actuals only", "fields_read": ["curr_act", "measure", "pdicity"], "financial_values_read": False, "detail_reread": False, "filtered_rows": int(len(q)), "curr_act_categories": {str(k): int(v) for k, v in counts.items()}}, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

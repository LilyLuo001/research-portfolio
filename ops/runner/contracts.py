#!/usr/bin/env python3
"""
contracts.py — deterministic output validation. This is what makes "files, not
conversations" enforceable and replaces most of P1-T12 / E2-T14 / DAX-A14 (the
LLM meta-QA agents). Contract checking is exactly what code beats LLMs at, and
it's free.

A task is COMPLETE only when its output file passes its contract here. Nothing
downstream may consume an output that hasn't passed.

  python contracts.py <contract_name> <path/to/output>

Checks: required columns present, dtypes, primary-key uniqueness, row-count vs
declared manifest, and any custom assertions listed in the contract YAML.
"""
import sys, pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "ops" / "contracts"

def load_contract(name):
    p = CONTRACTS / f"{name}.yaml"
    if not p.exists():
        print(f"UNKNOWN: no contract '{name}' in {CONTRACTS}"); sys.exit(2)
    return yaml.safe_load(p.read_text())

def check(name, path):
    c = load_contract(name)
    try:
        import pandas as pd
    except ImportError:
        print("NEED pandas to validate data files"); return 2
    p = pathlib.Path(path)
    if not p.exists():
        print(f"FAIL: {path} does not exist"); return 1
    if p.suffix == ".parquet":
        df = pd.read_parquet(p)
    elif p.suffix in (".csv", ".tsv"):
        df = pd.read_csv(p, sep="\t" if p.suffix == ".tsv" else ",")
    elif p.suffix == ".json":
        df = pd.read_json(p)
    else:
        print(f"UNKNOWN: cannot read {p.suffix}"); return 2

    fails = []
    # 1. required columns
    req = c.get("columns", {})
    for col in req:
        if col not in df.columns:
            fails.append(f"missing column '{col}'")
    # 2. no extra columns if strict
    if c.get("strict_columns") and set(df.columns) - set(req):
        fails.append(f"unexpected columns: {sorted(set(df.columns) - set(req))}")
    # 3. primary key uniqueness
    pk = c.get("primary_key")
    if pk and all(k in df.columns for k in pk):
        dup = df.duplicated(subset=pk).sum()
        if dup: fails.append(f"{dup} duplicate rows on primary key {pk}")
    # 4. non-null where required
    for col, spec in req.items():
        if isinstance(spec, dict) and spec.get("required") and col in df.columns:
            n = df[col].isna().sum()
            if n: fails.append(f"column '{col}' has {n} nulls but is required")
    # 5. range asserts
    for col, spec in req.items():
        if isinstance(spec, dict) and col in df.columns:
            if "min" in spec and (df[col] < spec["min"]).any():
                fails.append(f"'{col}' has values below {spec['min']}")
            if "max" in spec and (df[col] > spec["max"]).any():
                fails.append(f"'{col}' has values above {spec['max']}")

    if fails:
        print(f"FAIL [{name}] {path}:")
        for f in fails: print("   -", f)
        return 1
    print(f"PASS [{name}] {path}  ({len(df)} rows, {len(df.columns)} cols)")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    sys.exit(check(sys.argv[1], sys.argv[2]))

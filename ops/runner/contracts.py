#!/usr/bin/env python3
"""
contracts.py — deterministic output validation. This is what makes "files, not
conversations" enforceable and replaces most of P1-T12 / E2-T14 / DAX-A14 (the
LLM meta-QA agents). Contract checking is exactly what code beats LLMs at, and
it's free.

A task is COMPLETE only when its output file passes its contract here. Nothing
downstream may consume an output that hasn't passed.

  python contracts.py <contract_name> <path/to/output>

Four contract formats (the YAML's `format:` key; default is tabular):
  tabular   — required columns, primary-key uniqueness, non-null, min/max ranges
  markdown  — file exists and contains every `required_sections` heading text
  directory — directory exists and contains every `required_files` entry
  pytest    — `must_pass` test files exist under the path and pytest exits 0
  flat_kv   — JSON object whose keys cover every `required_keys_prefix`
"""
import sys, pathlib, subprocess, yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "ops" / "contracts"

def load_contract(name):
    p = CONTRACTS / f"{name}.yaml"
    if not p.exists():
        print(f"UNKNOWN: no contract '{name}' in {CONTRACTS}"); sys.exit(2)
    return yaml.safe_load(p.read_text())

def _fail(name, path, fails):
    print(f"FAIL [{name}] {path}:")
    for f in fails: print("   -", f)
    return 1


def check_markdown(c, name, p):
    text = p.read_text()
    fails = [f"missing required section '{s}'"
             for s in c.get("required_sections", []) if s not in text]
    if fails:
        return _fail(name, p, fails)
    print(f"PASS [{name}] {p}  (markdown, {len(c.get('required_sections', []))} sections present)")
    return 0


def check_directory(c, name, p):
    if not p.is_dir():
        return _fail(name, p, ["path is not a directory"])
    fails = [f"missing required file '{f}'"
             for f in c.get("required_files", []) if not (p / f).exists()]
    if fails:
        return _fail(name, p, fails)
    print(f"PASS [{name}] {p}  (directory, {len(c.get('required_files', []))} required files present)")
    return 0


def check_pytest(c, name, p):
    p = p.resolve()
    must = c.get("must_pass", [])
    missing = [t for t in must if not (p / t).exists()]
    if missing:
        return _fail(name, p, [f"missing test file '{t}'" for t in missing])
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *(str(p / t) for t in must)],
                       cwd=str(p), capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stdout or r.stderr).splitlines()[-15:]
        return _fail(name, p, ["pytest failed:"] + tail)
    print(f"PASS [{name}] {p}  (pytest, {len(must)} test files green)")
    return 0


def check_flat_kv(c, name, p):
    import json
    try:
        obj = json.loads(p.read_text())
    except ValueError as e:
        return _fail(name, p, [f"not valid JSON: {e}"])
    if not isinstance(obj, dict):
        return _fail(name, p, ["top level is not a JSON object"])
    fails = []
    for pref in c.get("required_keys_prefix", []):
        if not any(k.startswith(pref) for k in obj):
            fails.append(f"no key with required prefix '{pref}'")
    nested = [k for k, v in obj.items() if isinstance(v, (dict, list))]
    if nested:
        fails.append(f"keys must be flat scalars, found nested values under: {nested[:5]}")
    if fails:
        return _fail(name, p, fails)
    print(f"PASS [{name}] {p}  (flat_kv, {len(obj)} keys)")
    return 0


def check(name, path):
    c = load_contract(name)
    p = pathlib.Path(path)
    if not p.exists():
        print(f"FAIL: {path} does not exist"); return 1
    fmt = c.get("format", "tabular")
    if fmt == "markdown":
        return check_markdown(c, name, p)
    if fmt == "directory":
        return check_directory(c, name, p)
    if fmt == "pytest":
        return check_pytest(c, name, p)
    if fmt == "flat_kv":
        return check_flat_kv(c, name, p)

    try:
        import pandas as pd
    except ImportError:
        print("NEED pandas to validate data files"); return 2
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
        return _fail(name, path, fails)
    print(f"PASS [{name}] {path}  ({len(df)} rows, {len(df.columns)} cols)")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    sys.exit(check(sys.argv[1], sys.argv[2]))

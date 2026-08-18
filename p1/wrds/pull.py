#!/usr/bin/env python3
"""p1/wrds/pull.py — the five WRDS pulls, written offline, executed in one sprint.

ops/briefs/WRDS-access-assessment.md's recommendation: pre-write everything, then
borrow an account for one concentrated window (~3-5 days instead of 3-6 weeks
on/off) and run pure execution. This is that pre-written half. It needs no
network to develop or test; it needs a connection only for `discover` and `pull`.

Subcommands
  status     what is resolved, what is missing, what still needs a human (offline)
  discover   read the server's OWN table/column inventory -> discovered_schema.json
  resolve    match tables.yaml's logical fields to that inventory; anything
             ambiguous is reported NEED_HUMAN rather than picked
  pull       run one or all pulls; refuses on any unconfirmed name

Why the ceremony: meta-rule 1. A WRDS column name written from memory does not
raise, it returns a different number. Nothing here builds SQL from a name that
has not been seen in the live inventory — see p1/wrds/schema.py.

Raw landing: every pull writes an immutable parquet under p1/wrds/raw/ plus a
lineage JSON, and refuses to overwrite an existing file (pass --force only if
you mean to discard a landed pull).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "wrds"
RAW = HERE / "raw"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "ops" / "runner"))
from schema import DISCOVERED, Inventory, Resolver, SchemaRefusal, format_status  # noqa: E402

CUSIP_OK = re.compile(r"^[A-Z0-9]{6,9}$")
PULL_ORDER = ["mf_holdings", "stock_names", "msf", "dsf", "taq_iid", "ibes"]


# --------------------------------------------------------------------------- #
# connection                                                                   #
# --------------------------------------------------------------------------- #
def connect():
    try:
        import wrds
    except ImportError:
        sys.exit("NEED_HUMAN: the `wrds` package is not installed. This subcommand "
                 "only runs on a connected node (WRDS cloud or the box). "
                 "`status` works offline.")
    import os
    try:
        return wrds.Connection(wrds_username=os.getenv("WRDS_USER"))
    except Exception as e:  # noqa: BLE001
        sys.exit(f"NEED_HUMAN: WRDS auth failed ({e}). Check ~/.pgpass or WRDS_USER "
                 "(the username is case-sensitive).")


# --------------------------------------------------------------------------- #
# discover — the server tells us its schema; we never tell it ours             #
# --------------------------------------------------------------------------- #
def cmd_discover(args) -> None:
    spec = Resolver().spec
    db = connect()
    tables: dict[str, list[str]] = {}
    for lib in spec["libraries"]:
        try:
            names = db.list_tables(library=lib)
        except Exception as e:  # noqa: BLE001
            print(f"  {lib}: NOT AVAILABLE ({e}) — skipping", file=sys.stderr)
            continue
        print(f"  {lib}: {len(names)} tables")
        for t in names:
            full = f"{lib}.{t}"
            try:
                desc = db.describe_table(library=lib, table=t)
                tables[full] = [str(c) for c in desc["name"].tolist()]
            except Exception as e:  # noqa: BLE001
                print(f"    {full}: describe failed ({e})", file=sys.stderr)
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "libraries": spec["libraries"],
        "note": "Read off the live server. This is the ONLY authority on names.",
        "tables": tables,
    }
    DISCOVERED.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nwrote {DISCOVERED.relative_to(ROOT)}: {len(tables)} tables described.")
    print("next: python p1/wrds/pull.py resolve")


# --------------------------------------------------------------------------- #
# resolve — match logical fields to real names, refuse to guess                #
# --------------------------------------------------------------------------- #
def _resolve_one(candidates, present) -> tuple[str | None, str]:
    """Exactly one candidate present -> resolved. Zero or many -> NEED_HUMAN.

    Deliberately not clever. A 'best match' heuristic here would reintroduce
    precisely the guessing this module exists to prevent.
    """
    hits = [c for c in (candidates or []) if c in present]
    if len(hits) == 1:
        return hits[0], "unique candidate confirmed in inventory"
    if not hits:
        return None, "no candidate exists on the server — owner must supply the real name"
    return None, f"ambiguous: {hits} all exist — owner must pick"


def cmd_resolve(args) -> None:
    import yaml
    r = Resolver()
    if r.inv.empty:
        sys.exit(f"NEED_HUMAN: {DISCOVERED.relative_to(ROOT)} is missing. Run "
                 "`python p1/wrds/pull.py discover` on a connected node first.")
    spec = r.spec
    all_tables = set(r.inv.tables)
    unresolved: list[str] = []

    for pull, cfg in spec["pulls"].items():
        for logical, entry in cfg.get("tables", {}).items():
            if entry.get("resolved"):
                continue
            name, why = _resolve_one(entry.get("candidates"), all_tables)
            entry["resolved"] = name
            if not name:
                unresolved.append(f"{pull}.table.{logical}: {why} "
                                  f"(want: {' '.join(str(entry.get('want','')).split())})")
        # columns are confirmed against THIS pull's resolved tables only
        cols_present: set[str] = set()
        for e in cfg.get("tables", {}).values():
            if e.get("resolved"):
                cols_present |= set(r.inv.tables.get(e["resolved"], []))
        for logical, entry in cfg.get("columns", {}).items():
            if entry.get("resolved"):
                continue
            name, why = _resolve_one(entry.get("candidates"), cols_present)
            entry["resolved"] = name
            if not name:
                unresolved.append(f"{pull}.column.{logical}: {why} "
                                  f"(want: {' '.join(str(entry.get('want','')).split())})")

    if not args.dry_run:
        (HERE / "tables.yaml").write_text(yaml.safe_dump(spec, sort_keys=False,
                                                         allow_unicode=True))
        print(f"updated {(HERE / 'tables.yaml').relative_to(ROOT)}")
    print(f"\n{len(unresolved)} field(s) still need a human:")
    for u in unresolved:
        print(f"  NEED_HUMAN {u}")
    if unresolved:
        print("\nSettle these at the WRDS web query tool and paste the real names into\n"
              "tables.yaml's `resolved:` fields. Do not fill them from memory.")


# --------------------------------------------------------------------------- #
# pull — build SQL only from confirmed names                                   #
# --------------------------------------------------------------------------- #
def _cusip_list(cusips) -> str:
    """Inline a CUSIP list, validating each. WRDS's raw_sql takes params, but the
    lists here are thousands long; validating against a strict pattern and
    inlining is safer than trusting a driver to bind 6,747 params efficiently."""
    clean = sorted({c.strip().upper() for c in cusips if c and CUSIP_OK.match(c.strip().upper())})
    if not clean:
        raise SchemaRefusal("refusing to run: empty CUSIP universe")
    return ",".join(f"'{c}'" for c in clean)


def _landed_permnos(resolver: Resolver) -> list[int]:
    """Our permno universe, from the ALREADY-LANDED stock_names pull.

    This is why pull order matters. The universe is endogenous — it is whatever
    the converting funds held — so msf/dsf cannot be scoped until CUSIP->PERMNO
    has actually been fetched. Unscoped, the daily pull is the entire CRSP
    universe over six years (the 5-10GB case ops/briefs/WRDS-access-assessment.md
    warns against) instead of ~1-3GB.
    """
    import pandas as pd
    from universe import build_scope as _bs   # noqa: F401  (kept for symmetry)
    src = RAW / "stock_names__stocknames.parquet"
    if not src.exists():
        raise SchemaRefusal(
            "PULL ORDER: msf/dsf must be scoped to our permnos, which come from the\n"
            "  stock_names pull. Run `pull.py pull --pull stock_names` first, then\n"
            "  re-run this. (Unscoped, this would fetch the whole CRSP universe.)")
    df = pd.read_parquet(src)
    pcol = resolver.spec["pulls"]["stock_names"]["columns"]["security_id"]["resolved"]
    ccol = resolver.spec["pulls"]["stock_names"]["columns"]["cusip"]["resolved"]
    want = _universe_cusips()
    hit = df[df[ccol].astype(str).str.upper().str[:8].isin({c[:8] for c in want})]
    permnos = sorted({int(v) for v in hit[pcol].dropna().unique()})
    if not permnos:
        raise SchemaRefusal("stock_names landed but matched ZERO of our CUSIPs — check "
                            "the cusip column (CRSP carries a historical 8-char ncusip "
                            "as well as a current cusip) before pulling anything large.")
    return permnos


def _universe_cusips() -> set[str]:
    from universe import _read_convexp_cusips, _read_dropped_cusips
    computed, _ = _read_convexp_cusips()
    return {c.strip().upper() for c in (computed | _read_dropped_cusips()) if c}


def _int_list(values) -> str:
    return ",".join(str(int(v)) for v in values)


def build_queries(pull: str, resolver: Resolver, scope: dict) -> dict[str, str]:
    """The SQL for one pull. Every identifier comes through the resolver, so an
    unconfirmed name raises SchemaRefusal here rather than returning bad data."""
    R = resolver
    win = scope["windows"]

    if pull == "stock_names":
        t = R.table(pull, "stocknames")
        c = R.column(pull, "cusip", of_table=t)
        # scoped to our endogenous universe — CRSP's cusip fields are 8-char, so
        # match on the first 8 of the 9-char CUSIPs the N-PORT path carries
        return {"stocknames": (
            f"select {R.column(pull,'security_id',of_table=t)}, {c}, "
            f"{R.column(pull,'name_start',of_table=t)}, "
            f"{R.column(pull,'name_end',of_table=t)} from {t} "
            f"where substr({c}, 1, 8) in ({_cusip_list(_universe_cusips())})")}

    if pull == "msf":
        t = R.table(pull, "monthly_stock")
        d = R.column(pull, "date", of_table=t)
        sid = R.column(pull, "security_id", of_table=t)
        return {"msf": (
            f"select {sid}, {d}, "
            f"{R.column(pull,'price',of_table=t)}, "
            f"{R.column(pull,'shares_out',of_table=t)} from {t} "
            f"where {d} between date '{win['monthly_start']}' "
            f"and date '{win['monthly_end']}' "
            f"and {sid} in ({_int_list(_landed_permnos(R))})")}

    if pull == "dsf":
        t = R.table(pull, "daily_stock")
        d = R.column(pull, "date", of_table=t)
        sid = R.column(pull, "security_id", of_table=t)
        idx = R.table(pull, "daily_index")
        return {
            "dsf": (f"select {sid}, {d}, "
                    f"{R.column(pull,'ret',of_table=t)}, "
                    f"{R.column(pull,'price',of_table=t)}, "
                    f"{R.column(pull,'volume',of_table=t)}, "
                    f"{R.column(pull,'open_price',of_table=t)} from {t} "
                    f"where {d} between date '{win['daily_start']}' "
                    f"and date '{win['daily_end']}' "
                    f"and {sid} in ({_int_list(_landed_permnos(R))})"),
            "dsi": (f"select {R.column(pull,'date',of_table=idx)}, "
                    f"{R.column(pull,'mkt_ret',of_table=idx)} from {idx} "
                    f"where {R.column(pull,'date',of_table=idx)} between "
                    f"date '{win['daily_start']}' and date '{win['daily_end']}'"),
        }

    if pull == "mf_holdings":
        t = R.table(pull, "holdings")
        h = R.table(pull, "fund_header")
        return {
            "fund_header": (f"select {R.column(pull,'fund_id',of_table=h)}, "
                            f"{R.column(pull,'fund_ticker',of_table=h)} from {h}"),
            "holdings": (f"select {R.column(pull,'fund_id',of_table=t)}, "
                         f"{R.column(pull,'report_date',of_table=t)}, "
                         f"{R.column(pull,'security_id',of_table=t)}, "
                         f"{R.column(pull,'shares_held',of_table=t)} from {t} "
                         f"where {R.column(pull,'report_date',of_table=t)} <= "
                         f"date '{scope['waves']['last_effective_date']}'"),
        }

    if pull == "taq_iid":
        t = R.table(pull, "intraday_indicators")
        d = R.column(pull, "date", of_table=t)
        return {"taq_iid": (
            f"select {R.column(pull,'security_id',of_table=t)}, {d}, "
            f"{R.column(pull,'eff_spread',of_table=t)}, "
            f"{R.column(pull,'price_impact',of_table=t)} from {t} "
            f"where {d} between date '{win['daily_start']}' "
            f"and date '{win['daily_end']}'")}

    if pull == "ibes":
        s, a = R.table(pull, "summary"), R.table(pull, "actuals")
        return {
            "summary": (f"select {R.column(pull,'security_id',of_table=s)}, "
                        f"{R.column(pull,'consensus',of_table=s)}, "
                        f"{R.column(pull,'dispersion',of_table=s)}, "
                        f"{R.column(pull,'n_analysts',of_table=s)} from {s}"),
            "actuals": (f"select {R.column(pull,'security_id',of_table=a)}, "
                        f"{R.column(pull,'anndate',of_table=a)}, "
                        f"{R.column(pull,'actual',of_table=a)} from {a}"),
        }

    raise SchemaRefusal(f"unknown pull '{pull}' (known: {', '.join(PULL_ORDER)})")


def cmd_pull(args) -> None:
    from universe import build_scope
    from lineage import write_lineage

    resolver = Resolver()
    scope = build_scope()
    targets = [args.pull] if args.pull else PULL_ORDER
    RAW.mkdir(parents=True, exist_ok=True)

    blocked = [p for p in targets if not resolver.ready(p)]
    if blocked:
        print("REFUSING — these pulls have unconfirmed names:\n")
        print(format_status(resolver))
        sys.exit(f"\nblocked: {', '.join(blocked)}. Run discover + resolve first.")

    for p in targets:
        outstanding = resolver.outstanding_asserts(p)
        if outstanding and not args.accept_open_questions:
            print(f"\nNEED_HUMAN before '{p}' is usable (data will pull, but the "
                  "SEMANTICS are unsettled):")
            for k, v in outstanding.items():
                print(f"  {k}: {' '.join(v.split())}")
            print("  These are conventions/units that discovery cannot answer. Re-run "
                  "with --accept-open-questions to land the raw data anyway and settle "
                  "them before any number is computed from it.")
            continue
        queries = build_queries(p, resolver, scope)
        if args.dry_run:
            print(f"\n--- {p} ---")
            for name, sql in queries.items():
                print(f"[{name}]\n{sql}\n")
            continue
        db = connect()
        for name, sql in queries.items():
            out = RAW / f"{p}__{name}.parquet"
            if out.exists() and not args.force:
                print(f"  {out.name}: already landed, skipping (--force to replace)")
                continue
            print(f"  {out.name}: running...")
            df = db.raw_sql(sql)
            df.to_parquet(out, index=False)
            write_lineage(out, [], extra={"wrds_query": sql, "rows": int(len(df)),
                                          "pull": p, "part": name})
            print(f"  {out.name}: {len(df):,} rows")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("discover")
    r = sub.add_parser("resolve"); r.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("pull")
    p.add_argument("--pull", choices=PULL_ORDER)
    p.add_argument("--dry-run", action="store_true", help="print SQL, connect to nothing")
    p.add_argument("--force", action="store_true", help="replace an already-landed file")
    p.add_argument("--accept-open-questions", action="store_true",
                   help="land raw data whose units/conventions are still NEED_HUMAN")
    a = ap.parse_args()

    if a.cmd == "status":
        print(format_status(Resolver()))
    elif a.cmd == "discover":
        cmd_discover(a)
    elif a.cmd == "resolve":
        cmd_resolve(a)
    elif a.cmd == "pull":
        cmd_pull(a)


if __name__ == "__main__":
    main()

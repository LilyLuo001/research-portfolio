#!/usr/bin/env python3
"""P1-T2 — day-one WRDS coverage census. RUN THIS BEFORE THE PIPELINE.

Two jobs, both of which have to happen before any ConvExp number is believed:

  --introspect   Confirm the SCHEMA in holdings_pipeline.py against the live
                 account. Every table and column there was written before access
                 was delivered and is UNVERIFIED; guessing schema from memory is
                 what meta-rule 1 forbids. This prints what actually exists and
                 names the entries to correct.

  (default)      Census the holdings coverage of the 131 conversion funds: which
                 map to a CRSP fund number, which have a holdings report strictly
                 before their conversion date, and how stale that report is.

Why a census rather than just running the pipeline: mutual-fund holdings coverage
has known lags and gaps, and a pipeline run that silently drops a third of the
funds looks exactly like a successful one. The free path already taught this — it
computed 6,377 cells and dropped 5,929, and the dropped half only became visible
because someone counted. Coverage is a fact to establish with code on real data,
never an assumption.

Outputs (no licensed rows — see README, DATA POLICY):
  coverage_census.md     human summary
  coverage_census.csv    per-fund: mapped, report date, staleness, n_positions
  schema_check.json      --introspect result

Run on box:  python p1/t2_wrds/coverage_census.py --introspect
             python p1/t2_wrds/coverage_census.py
"""
import argparse
import csv
import json
import pathlib
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from holdings_pipeline import (  # noqa: E402
    SCHEMA, Recorder, connect, map_funds, _q, _inlist)

EVENTS = HERE.parent / "events_merged.csv"
WAVES = HERE / "waves.csv"
CENSUS_MD = HERE / "coverage_census.md"
CENSUS_CSV = HERE / "coverage_census.csv"
SCHEMA_CHECK = HERE / "schema_check.json"

# A fund filing quarterly can legitimately be ~92 days stale at conversion; beyond
# this the holdings are old enough that the pre-conversion snapshot is worth
# flagging rather than silently using.
STALE_WARN_DAYS = 120


# --------------------------------------------------------------------------- #
# schema verification                                                          #
# --------------------------------------------------------------------------- #
def sql_introspect_columns(qualified_table):
    """Columns of one table, via information_schema (portable SQL, not a guess at
    the wrds client's helper API)."""
    schema, _, table = qualified_table.partition(".")
    return ("select column_name, data_type from information_schema.columns "
            f"where table_schema = {_q(schema)} and table_name = {_q(table)} "
            "order by column_name")


def check_schema(db):
    """Report, per SCHEMA entry, whether the table and each column exist."""
    report = {}
    for entry, spec in SCHEMA.items():
        table = spec["table"]
        wanted = {k: v for k, v in spec.items() if k != "table"}
        try:
            df = db.raw_sql(sql_introspect_columns(table), label=f"introspect::{table}")
            actual = {str(c) for c in df["column_name"]} if len(df) else set()
        except Exception as e:  # noqa: BLE001 — a missing table must not abort the sweep
            report[entry] = {"table": table, "table_exists": False, "error": str(e)}
            continue
        report[entry] = {
            "table": table,
            "table_exists": bool(actual),
            "columns_ok": {role: name for role, name in wanted.items() if name in actual},
            "columns_missing": {role: name for role, name in wanted.items()
                                if name not in actual},
            "columns_available": sorted(actual)[:60],
        }
    return report


def schema_verdict(report):
    bad = [e for e, r in report.items()
           if not r.get("table_exists") or r.get("columns_missing")]
    return ("SCHEMA OK — every table and column in holdings_pipeline.SCHEMA exists"
            if not bad else
            "SCHEMA NEEDS CORRECTION in holdings_pipeline.py: " + ", ".join(sorted(bad)))


# --------------------------------------------------------------------------- #
# holdings census                                                              #
# --------------------------------------------------------------------------- #
def sql_last_report_before_per_fund(pairs):
    """One query for every (fundno, effective_date) pair.

    A VALUES join keeps this to a single round trip instead of one query per fund
    — the shared WRDS server is not the place for an N+1.
    """
    h = SCHEMA["holdings"]
    values = ", ".join(f"({int(fundno)}, date {_q(eff)})" for fundno, eff in pairs)
    return (f"with target(fundno, eff) as (values {values}) "
            f"select t.fundno, t.eff, max(h.{h['report_date']}) as last_report, "
            f"count(*) as n_position_rows "
            f"from target t join {h['table']} h "
            f"on h.{h['fundno']} = t.fundno and h.{h['report_date']} < t.eff "
            f"group by t.fundno, t.eff")


def _days_between(later, earlier):
    fmt = "%Y-%m-%d"
    try:
        a = datetime.strptime(str(later)[:10], fmt)
        b = datetime.strptime(str(earlier)[:10], fmt)
    except ValueError:
        return None
    return (a - b).days


def census(db, events):
    """Per-fund coverage rows. Never fabricates a report date it did not see."""
    rec = db if isinstance(db, Recorder) else Recorder(db)
    mapping, unmapped = map_funds(rec, events)

    rows = [{"fund_name": u.get("fund_name", ""),
             "mutual_fund_ticker": u.get("mutual_fund_ticker", ""),
             "effective_date": u.get("effective_date", ""),
             "mapped": "no", "status": u["unmapped_reason"],
             "last_report_before_conversion": "", "staleness_days": "",
             "n_position_rows": ""} for u in unmapped]

    pairs = sorted({(m["fundno"], m["effective_date"]) for m in mapping
                    if m.get("effective_date")})
    seen = {}
    if pairs:
        df = rec.raw_sql(sql_last_report_before_per_fund(pairs), label="holdings_census")
        for r in df.itertuples():
            seen[(int(r.fundno), str(r.eff)[:10])] = (str(r.last_report)[:10],
                                                      int(r.n_position_rows))
    for m in mapping:
        key = (m["fundno"], str(m.get("effective_date", ""))[:10])
        hit = seen.get(key)
        if not hit:
            rows.append({"fund_name": m.get("fund_name", ""),
                         "mutual_fund_ticker": m.get("mutual_fund_ticker", ""),
                         "effective_date": key[1], "mapped": "yes",
                         "status": "no_holdings_report_before_conversion",
                         "last_report_before_conversion": "", "staleness_days": "",
                         "n_position_rows": ""})
            continue
        last, n = hit
        gap = _days_between(key[1], last)
        rows.append({"fund_name": m.get("fund_name", ""),
                     "mutual_fund_ticker": m.get("mutual_fund_ticker", ""),
                     "effective_date": key[1], "mapped": "yes",
                     "status": ("stale_holdings_report" if gap is not None
                                and gap > STALE_WARN_DAYS else "ok"),
                     "last_report_before_conversion": last,
                     "staleness_days": "" if gap is None else gap,
                     "n_position_rows": n})
    return rows, rec


def summarize(rows):
    n = len(rows)
    by_status = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    usable = [r for r in rows if r["status"] in ("ok", "stale_holdings_report")]
    gaps = sorted(int(r["staleness_days"]) for r in usable if r["staleness_days"] != "")
    return {
        "funds_total": n,
        "funds_usable": len(usable),
        "coverage_pct": round(100.0 * len(usable) / n, 1) if n else 0.0,
        "by_status": dict(sorted(by_status.items())),
        "staleness_days_median": gaps[len(gaps) // 2] if gaps else None,
        "staleness_days_max": gaps[-1] if gaps else None,
    }


def write_outputs(rows, summary, md_path=CENSUS_MD, csv_path=CENSUS_CSV):
    fields = ["fund_name", "mutual_fund_ticker", "effective_date", "mapped", "status",
              "last_report_before_conversion", "staleness_days", "n_position_rows"]
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    L = ["# P1-T2 WRDS holdings coverage census", "",
         f"generated: {datetime.now(timezone.utc).isoformat()}", "",
         "Run before the ConvExp pipeline. A fund with no pre-conversion holdings",
         "report contributes no treatment intensity, and that is a sample fact to",
         "state, not a number to impute.", "",
         f"- conversion funds: **{summary['funds_total']}**",
         f"- with a usable pre-conversion holdings report: **{summary['funds_usable']}** "
         f"({summary['coverage_pct']}%)",
         f"- report staleness (days before conversion): median "
         f"{summary['staleness_days_median']}, max {summary['staleness_days_max']}", "",
         "## by status", "", "| status | funds |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in summary["by_status"].items()]
    L += ["", f"Funds flagged `stale_holdings_report` are older than "
              f"{STALE_WARN_DAYS} days at conversion — usable, but the snapshot is "
              "further from the event than a quarterly filer's would normally be.",
          "", "Per-fund detail: `coverage_census.csv`. No licensed rows are "
              "committed; see README."]
    md_path.write_text("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="P1-T2 WRDS coverage census")
    ap.add_argument("--introspect", action="store_true",
                    help="verify holdings_pipeline.SCHEMA against the live account")
    a = ap.parse_args(argv)

    db = Recorder(connect())
    if a.introspect:
        report = check_schema(db)
        SCHEMA_CHECK.write_text(json.dumps(report, indent=2) + "\n")
        print(schema_verdict(report))
        print(f"detail -> {SCHEMA_CHECK}")
        return 0

    events = list(csv.DictReader(EVENTS.open()))
    rows, _ = census(db, events)
    summary = summarize(rows)
    write_outputs(rows, summary)
    print(f"census: {summary['funds_usable']}/{summary['funds_total']} funds have a "
          f"usable pre-conversion holdings report ({summary['coverage_pct']}%). "
          f"-> {CENSUS_MD.name}, {CENSUS_CSV.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

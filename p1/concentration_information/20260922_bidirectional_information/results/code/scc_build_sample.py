#!/usr/bin/env python3
"""Construct the pre-response SPY pilot roster on SCC.

Reads only the 2022-12-31 CRSP SPY holding report, an explicitly supplied
daily-stock liquidity panel, and (if supplied) a dated security identity
panel.  It deliberately refuses to substitute holdings market value or new
tick responses for the required 60-trading-day dollar-volume ranking.
"""
from __future__ import annotations

import argparse, csv, hashlib, json
from pathlib import Path
import duckdb

SEED = 20260922
PORTNO = 1021980
REPORT_DATE = "2022-12-31"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def stable_draw_key(row: dict, tier: str, liquidity_tier: str) -> tuple[str, str]:
    """A reproducible without-replacement draw key, with PERMNO as tie-breaker."""
    material = f"{SEED}|{tier}|{liquidity_tier}|{row['permno']}".encode()
    return hashlib.sha256(material).hexdigest(), str(row["permno"])

def parquet_files(root: Path) -> list[str]:
    return [str(root)] if root.is_file() else sorted(str(p) for p in root.glob("*.parquet"))

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--holdings-root", type=Path, required=True)
    p.add_argument("--daily-liquidity-root", type=Path, required=True)
    p.add_argument("--security-history-root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
    holdings = (sorted(str(p) for p in args.holdings_root.glob("crsp_holdings_etf_2022_b*/part_*.parquet"))
                if args.holdings_root.is_dir() else parquet_files(args.holdings_root))
    daily = parquet_files(args.daily_liquidity_root)
    security = parquet_files(args.security_history_root)
    missing = [name for name, paths in (("daily_liquidity", daily), ("security_history", security)) if not paths]
    receipt = {"status": "BLOCKED_MISSING_PERMITTED_METADATA" if missing else "RUNNING",
               "required": {"report_date": REPORT_DATE, "portno": PORTNO,
                            "liquidity": "prior 60 NYSE sessions of daily price*volume",
                            "security_identity": "dated CRSP identity / ordinary common-stock filter"},
               "source_counts": {"holdings": len(holdings), "daily_liquidity": len(daily), "security_history": len(security)},
               "missing": missing}
    (args.out / "sample_build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if missing:
        raise SystemExit("missing required permitted daily-liquidity and/or dated security-history parquet input")
    # Source schemas are intentionally validated rather than guessed.
    con = duckdb.connect()
    con.execute("create view h as select * from read_parquet(" + repr(holdings) + ")")
    con.execute("create view d as select * from read_parquet(" + repr(daily) + ")")
    con.execute("create view s as select * from read_parquet(" + repr(security) + ")")
    receipt["diagnostics"] = {
        "held_rows": con.execute("select count(*) from h where crsp_portno=? and cast(report_dt as date)=cast(? as date) and ticker is not null and nbr_shares>0 and permno is not null", [PORTNO, REPORT_DATE]).fetchone()[0],
        "valid_common_rows": con.execute("select count(*) from s where shrcd in (10,11) and cast(namedt as date)<=date '2022-12-31' and coalesce(cast(nameendt as date),date '9999-12-31')>=date '2022-12-31'").fetchone()[0],
        "liquid_60_rows": con.execute("with sessions as (select distinct cast(date as date) date from d where cast(date as date)<=date '2022-12-30' order by date desc limit 60) select count(*) from (select permno from d where cast(date as date) in (select date from sessions) group by permno having count(distinct cast(date as date))=60)").fetchone()[0],
    }
    (args.out / "sample_build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    # Expected canonical aliases must be supplied by a small SCC-side adapter
    # if the mirror uses another CRSP release schema.
    candidates = con.execute("""
      with held as (
        select upper(trim(ticker)) symbol, cast(cast(permno as bigint) as varchar) permno,
               sum(percent_tna)/100.0 report_weight
        from h where crsp_portno=? and cast(report_dt as date)=cast(? as date)
          and ticker is not null and nbr_shares > 0 and permno is not null
        group by 1,2), valid as (
        select * from s where shrcd in (10,11)
          and cast(namedt as date) <= date '2022-12-31' and coalesce(cast(nameendt as date), date '9999-12-31') >= date '2022-12-31'), liq as (
        with sessions as (select distinct cast(date as date) date from d where cast(date as date)<=date '2022-12-30' order by date desc limit 60)
        select cast(permno as varchar) permno, avg(abs(prc)*vol) dollar_volume
        from d where cast(date as date) in (select date from sessions)
        group by 1 having count(distinct cast(date as date))=60)
      select held.symbol,held.permno,held.report_weight,liq.dollar_volume
      from held
      join (select cast(permno as varchar) permno from valid) valid on held.permno=valid.permno
      join liq on held.permno=liq.permno
    """, [PORTNO, REPORT_DATE]).fetchall()
    # Tier on report weight (top 10%, next 40%, bottom 50%) and median dollar
    # volume within each tier; shuffled deterministically once and take four.
    candidates = [dict(symbol=x[0], permno=x[1], report_weight=float(x[2]), dollar_volume=float(x[3])) for x in candidates]
    if not candidates:
        raise RuntimeError("no candidates survived holdings/common-share/60-session liquidity joins")
    # This is the predeclared report-weight ordering used for 10/40/50 tiers.
    candidates.sort(key=lambda x: (-x["report_weight"], x["permno"]))
    n=len(candidates); cuts=(max(1, (n+9)//10), max(1, (n+4)//2))
    for i,row in enumerate(candidates): row["weight_tier"] = "high" if i < cuts[0] else ("mid" if i < cuts[1] else "low")
    selected=[]
    for tier in ("high","mid","low"):
        group=[x for x in candidates if x["weight_tier"]==tier]; med=sorted(x["dollar_volume"] for x in group)[len(group)//2]
        for liquidity_tier, cells in (("high",[x for x in group if x["dollar_volume"]>=med]),("low",[x for x in group if x["dollar_volume"]<med])):
            # Hash order documents both the fixed seed and the permanent-ID tie breaker;
            # no responses, coverage, or later identity mapping enters this draw.
            cells.sort(key=lambda row: stable_draw_key(row, tier, liquidity_tier))
            for rank,row in enumerate(cells[:4],1):
                selected.append({**row,"liquidity_tier":liquidity_tier,"draw_rank":rank,
                                 "draw_key":stable_draw_key(row,tier,liquidity_tier)[0]})
    with (args.out/"SAFE_ROSTER.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["symbol","permno","report_weight","dollar_volume","weight_tier","liquidity_tier","draw_rank","draw_key"]);w.writeheader();w.writerows(selected)
    receipt.update(status="COMPLETE",candidate_count=n,selected_count=len(selected),seed=SEED,
                   tier_order="descending report_weight, PERMNO tie-breaker",
                   draw_order="sha256(seed|weight_tier|liquidity_tier|PERMNO), PERMNO tie-breaker")
    (args.out / "sample_build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

if __name__ == "__main__": main()

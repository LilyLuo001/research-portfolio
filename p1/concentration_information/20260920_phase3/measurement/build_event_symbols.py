"""Map frozen receiver securities to date-valid public tickers on SCC."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import duckdb


def q(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected", required=True, type=Path)
    parser.add_argument("--names", required=True, type=Path)
    parser.add_argument("--clock", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    with args.clock.open(newline="") as handle:
        events = [row for row in csv.DictReader(handle) if row["supports_5m"] in {"YES", "CONDITIONAL"}]
    assert events
    event_values = ",".join(
        f"({q(row['event_id'])},DATE {q(row['event_date'])})" for row in events
    )
    con = duckdb.connect()
    con.execute(f"CREATE TEMP TABLE events(event_id,event_date) AS VALUES {event_values}")
    con.execute(
        f"CREATE TEMP TABLE selected AS SELECT * FROM read_parquet({q(args.selected)})"
    )
    con.execute(
        f"""
        CREATE TEMP TABLE mapped AS
        SELECT e.event_id,e.event_date,
          (CASE WHEN s.same_sic2_as_any_issuer THEN 'S' ELSE 'C' END) ||
            lpad(CAST(s.stratum_rank AS VARCHAR),2,'0') || '_' || s.connection_role receiver_id,
          s.connection_role,s.same_sic2_as_any_issuer,
          n.ticker symbol,count(*) OVER(PARTITION BY e.event_id,s.receiver_permco) mapping_rows
        FROM events e CROSS JOIN selected s
        JOIN read_parquet({q(args.names)}) n
          ON CAST(n.permno AS BIGINT)=s.representative_permno
         AND CAST(n.namedt AS DATE)<=e.event_date
         AND (CAST(n.nameendt AS DATE)>=e.event_date OR n.nameendt IS NULL)
        """
    )
    assert con.execute("SELECT count(*) FROM mapped").fetchone()[0] == len(events) * 20
    assert con.execute("SELECT count(*) FROM mapped WHERE mapping_rows<>1 OR symbol IS NULL").fetchone()[0] == 0
    con.execute(
        f"""COPY (SELECT event_id,event_date,receiver_id,symbol,connection_role,
                    same_sic2_as_any_issuer
             FROM mapped ORDER BY event_id,receiver_id)
             TO {q(args.out)} (HEADER,DELIMITER ',')"""
    )
    print({"events": len(events), "rows": len(events) * 20, "ambiguous_or_missing": 0})


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the 2023-01-23 S&P 500 roster and prior-close cap-weight proxy on SCC.

The script never contacts WRDS.  It uses the frozen SCC mirror described in the
P1 data manual.  CRSP index membership series 1000500 is the S&P 500 member
series: on 2024-12-31 its 503 active PERMNOs exactly match the three companion
series 1000501/1000510/1000511 and overlap all 466 still-active Compustat S&P
500 issues that can be linked on that date.  The output remains on SCC.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


DEFAULT_MIRROR = Path(
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/"
    "p1_refraction_wrds_shared"
)
SP500_INDNO = 1000500
ASOF = pd.Timestamp("2023-01-23")


def load(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    return pq.read_table(path, columns=columns).to_pandas()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mirror", type=Path, default=DEFAULT_MIRROR)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    membership = load(
        args.mirror / "raw/crsp_stkindmembership_ind_full.parquet",
        ["permno", "indno", "mbrstartdt", "mbrenddt", "mbrflg", "indfam"],
    )
    for col in ("mbrstartdt", "mbrenddt"):
        membership[col] = pd.to_datetime(membership[col], errors="coerce")
    roster = membership[
        (membership["indno"] == SP500_INDNO)
        & (membership["mbrstartdt"] <= ASOF)
        & (membership["mbrenddt"] >= ASOF)
    ].drop_duplicates("permno")

    names = load(args.mirror / "raw/crsp_dsenames_full.parquet")
    for col in ("namedt", "nameendt"):
        names[col] = pd.to_datetime(names[col], errors="coerce")
    names = (
        names[(names["namedt"] <= ASOF) & (names["nameendt"] >= ASOF)]
        .sort_values(["permno", "namedt"])
        .drop_duplicates("permno", keep="last")
    )
    roster = roster.merge(
        names[
            [
                "permno", "ticker", "tsymbol", "comnam", "exchcd", "shrcd",
                "cusip", "ncusip", "shrcls", "trdstat", "secstat",
            ]
        ],
        on="permno",
        how="left",
        validate="one_to_one",
    )

    dsf = load(
        args.mirror / "raw/crsp_dsf_2023.parquet",
        ["permno", "date", "prc", "shrout", "cfacpr", "cfacshr"],
    )
    dsf["date"] = pd.to_datetime(dsf["date"], errors="coerce")
    dsf = dsf[dsf["date"] == ASOF].drop_duplicates("permno")
    roster = roster.merge(dsf.drop(columns="date"), on="permno", how="left", validate="one_to_one")
    roster["mcap_usd_proxy"] = roster["prc"].abs() * roster["shrout"] * 1000.0
    roster["weight_proxy"] = roster["mcap_usd_proxy"] / roster["mcap_usd_proxy"].sum()
    roster["asof_date"] = ASOF.date().isoformat()
    roster["index_indno"] = SP500_INDNO
    roster = roster.sort_values("weight_proxy", ascending=False)

    if len(roster) != 503:
        raise RuntimeError(f"expected 503 member securities, got {len(roster)}")
    if roster["ticker"].isna().any() or roster["ticker"].nunique() != 503:
        raise RuntimeError("historical ticker mapping is incomplete or nonunique")
    if roster["mcap_usd_proxy"].isna().any():
        raise RuntimeError("prior-close market-cap proxy is incomplete")

    roster.to_parquet(args.out_dir / "SP500_ROSTER_20230123.parquet", index=False)
    roster.to_csv(args.out_dir / "SP500_ROSTER_20230123.csv", index=False)
    symbols = ["SPY", *roster["ticker"].tolist()]
    (args.out_dir / "DATABENTO_SYMBOLS_20230123.json").write_text(
        json.dumps(symbols, indent=2) + "\n"
    )
    receipt = {
        "status": "COMPLETE",
        "asof_date": ASOF.date().isoformat(),
        "index_indno": SP500_INDNO,
        "member_security_count": int(len(roster)),
        "unique_ticker_count": int(roster["ticker"].nunique()),
        "prior_close_mcap_count": int(roster["mcap_usd_proxy"].notna().sum()),
        "weight_sum": float(roster["weight_proxy"].sum()),
        "weight_definition": "abs(CRSP prior-close price) * CRSP shares outstanding; normalized across members",
        "not_exact_sp_index_weight": True,
        "raw_inputs_modified": False,
    }
    (args.out_dir / "ROSTER_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()

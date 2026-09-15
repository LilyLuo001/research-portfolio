#!/usr/bin/env python3
"""Cross-check 480 IBES event dates against Compustat RDQ metadata on SCC."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


ROOT = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914")
RAW = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw")
EVENTS = Path(os.environ.get("P1_EVENT_MANIFEST", ROOT / "supported_earnings_inputs/selected_event_metadata.csv"))
OUT = Path(os.environ.get("P1_RDQ_OUTPUT", ROOT / "compustat_rdq_crosscheck"))
EXPECTED_EVENTS_SHA256 = os.environ.get(
    "P1_EVENT_MANIFEST_SHA256",
    "d2f113fe770ed9efb959652f0b4aef99442138056d3a08311771e1cc408bab52",
)
EXPECTED_EVENT_ROWS = int(os.environ.get("P1_EVENT_ROWS", "480"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if sha256(EVENTS) != EXPECTED_EVENTS_SHA256:
        raise ValueError("event manifest hash mismatch")
    if OUT.exists():
        raise FileExistsError(f"preserve output: {OUT}")
    OUT.mkdir(parents=True)
    events = pd.read_csv(EVENTS)
    events["permno"] = events.permno.astype(int)
    events["pends_dt"] = pd.to_datetime(events.pends)
    events["announcement_date_dt"] = pd.to_datetime(events.announcement_date)

    link_path = RAW / "crsp_ccm_linktable_full.parquet"
    links = pd.read_parquet(
        link_path,
        columns=["gvkey", "linkprim", "liid", "linktype", "lpermno", "lpermco", "usedflag", "linkdt", "linkenddt"],
    )
    links = links[links.lpermno.isin(set(events.permno))].copy()
    links["linkdt"] = pd.to_datetime(links.linkdt)
    links["linkenddt"] = pd.to_datetime(links.linkenddt).fillna(pd.Timestamp("2099-12-31"))
    links = links[links.linktype.astype(str).str.startswith("L") & links.linkprim.isin(["P", "C"])].copy()

    fundq_parts = []
    fundq_inputs = []
    gvkeys = set(links.gvkey.astype(str))
    for year in range(2018, 2025):
        path = RAW / f"comp_fundq_{year}.parquet"
        columns = ["gvkey", "datadate", "fyearq", "fqtr", "fyr", "datacqtr", "datafqtr", "tic", "cusip", "conm", "rdq"]
        missing = [c for c in columns if c not in pq.read_schema(path).names]
        if missing:
            raise ValueError(f"missing Compustat metadata columns {path}: {missing}")
        frame = pd.read_parquet(path, columns=columns)
        frame["gvkey"] = frame.gvkey.astype(str)
        frame = frame[frame.gvkey.isin(gvkeys)].copy()
        fundq_parts.append(frame)
        fundq_inputs.append({"path": str(path), "sha256": sha256(path), "selected_rows": len(frame)})
    fundq = pd.concat(fundq_parts, ignore_index=True).drop_duplicates()
    fundq["datadate"] = pd.to_datetime(fundq.datadate)
    fundq["rdq"] = pd.to_datetime(fundq.rdq)

    rows = []
    for event in events.itertuples(index=False):
        valid_links = links[
            links.lpermno.eq(event.permno)
            & (links.linkdt <= event.pends_dt)
            & (event.pends_dt <= links.linkenddt)
        ].copy()
        candidates = fundq[
            fundq.gvkey.isin(set(valid_links.gvkey.astype(str)))
            & (fundq.datadate.sub(event.pends_dt).abs() <= pd.Timedelta(days=10))
        ].copy()
        exact = candidates[candidates.datadate.eq(event.pends_dt)].copy()
        use = exact if not exact.empty else candidates
        rdqs = sorted({d.strftime("%Y-%m-%d") for d in use.rdq.dropna()})
        rows.append({
            "association_id": event.association_id,
            "wave_id": event.wave_id,
            "permno": event.permno,
            "pends": event.pends,
            "ibes_announcement_date": event.announcement_date,
            "valid_ccm_links": len(valid_links),
            "candidate_fundq_rows": len(candidates),
            "exact_datadate_rows": len(exact),
            "rdq_dates_all": ";".join(rdqs),
            "rdq_status": "UNIQUE" if len(rdqs) == 1 else ("MISSING" if not rdqs else "AMBIGUOUS"),
            "rdq_equals_ibes_date": len(rdqs) == 1 and rdqs[0] == event.announcement_date,
        })
    crosscheck = pd.DataFrame(rows)
    crosscheck.to_csv(OUT / "event_rdq_crosscheck.csv", index=False)
    if len(crosscheck) != EXPECTED_EVENT_ROWS:
        raise ValueError(f"expected {EXPECTED_EVENT_ROWS} RDQ cross-check rows")
    receipt = {
        "status": "COMPUSTAT_RDQ_METADATA_CROSSCHECK_COMPLETE",
        "event_manifest_sha256": sha256(EVENTS),
        "events": len(crosscheck),
        "unique_rdq": int(crosscheck.rdq_status.eq("UNIQUE").sum()),
        "missing_rdq": int(crosscheck.rdq_status.eq("MISSING").sum()),
        "ambiguous_rdq": int(crosscheck.rdq_status.eq("AMBIGUOUS").sum()),
        "rdq_equals_ibes_date": int(crosscheck.rdq_equals_ibes_date.sum()),
        "output_sha256": sha256(OUT / "event_rdq_crosscheck.csv"),
        "ccm_input": {"path": str(link_path), "sha256": sha256(link_path)},
        "fundq_inputs": fundq_inputs,
        "financial_values_read": False,
        "price_return_quote_values_read": False,
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()

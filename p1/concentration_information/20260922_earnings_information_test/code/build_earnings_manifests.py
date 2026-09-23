#!/usr/bin/env python3
"""Build the fixed six-issuer earnings and Databento request manifests.

Only identity and release-date/time metadata are read from the existing SCC
I/B/E/S actuals files.  EPS values and all other outcome-bearing fields are
never projected.  The resulting public manifest labels these clocks as
candidates until a first-public issuer/filing source is attached.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
IBES_TICKER = {"AAPL": "AAPL", "LLY": "LLY", "CVS": "MES", "CMI": "CUM", "EBAY": "EBY1", "NWSA": "NWSV"}
RANK = {"AAPL": 1, "LLY": 5, "CVS": 9, "CMI": 14, "EBAY": 18, "NWSA": 23}
WEIGHT = {"AAPL": 0.0605, "LLY": 0.0090, "CVS": 0.0038, "CMI": 0.0011, "EBAY": 0.0007, "NWSA": 0.0002}
SYMBOLS = ["SPY", "GOOG", "LLY", "V", "AAPL", "ABBV", "KO", "PG", "MRK", "BDX", "CVS", "DLTR", "TJX", "CMI", "MMC", "MNST", "KHC", "KEY", "RSG", "WST", "EBAY", "NWSA", "NDSN", "XYL"]

# ICE/NYSE full-day closures. Early closes remain sessions.
CLOSED = {
    "2022-12-26",
    "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29",
    "2023-06-19", "2023-07-04", "2023-09-04", "2023-11-23", "2023-12-25",
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
    "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iso_utc(day: str, clock: str) -> str:
    stamp = datetime.combine(date.fromisoformat(day), time.fromisoformat(clock), NY)
    return stamp.astimezone(UTC).isoformat().replace("+00:00", "Z")


def shift_minutes(day: str, clock: str, minutes: int) -> str:
    stamp = datetime.combine(date.fromisoformat(day), time.fromisoformat(clock), NY) + timedelta(minutes=minutes)
    return stamp.astimezone(UTC).isoformat().replace("+00:00", "Z")


def is_session(day: date) -> bool:
    return day.weekday() < 5 and day.isoformat() not in CLOSED


def fifth_prior(day: str, prohibited: set[str]) -> tuple[str, int]:
    current = date.fromisoformat(day)
    ordinal = 0
    while True:
        current -= timedelta(days=1)
        if not is_session(current):
            continue
        ordinal += 1
        if ordinal >= 5 and current.isoformat() not in prohibited:
            return current.isoformat(), ordinal


def split(day: str) -> str:
    if day.startswith("2024"):
        return "TEST"
    month = int(day[5:7])
    return "TRAIN" if month <= 6 else ("VALID" if month <= 9 else "HISTORY")


def read_events(paths: list[Path]) -> tuple[pd.DataFrame, list[dict]]:
    audit = []
    pieces = []
    reverse = {v: k for k, v in IBES_TICKER.items()}
    for path in paths:
        frame = pd.read_parquet(path, columns=["ticker", "anndats", "anntims", "pdicity"])
        audit.append({"path": str(path), "sha256": sha256(path), "projected_columns": ["ticker", "anndats", "anntims", "pdicity"], "source_rows": int(len(frame))})
        frame = frame[frame.ticker.astype(str).isin(reverse)].copy()
        frame["issuer"] = frame.ticker.astype(str).map(reverse)
        frame["event_date"] = pd.to_datetime(frame.anndats, errors="coerce").dt.strftime("%Y-%m-%d")
        # WRDS/IBES time can arrive as an integer-like HHMM. Retain minute precision only.
        raw = frame.anntims.astype(str).str.replace(r"\.0$", "", regex=True)
        colon = raw.str.contains(":", regex=False)
        compact = raw.str.zfill(4)
        frame["clock_et"] = compact.str[:2] + ":" + compact.str[2:4] + ":00"
        frame.loc[colon, "clock_et"] = raw[colon].str[:8]
        frame = frame[frame.event_date.str[:4].isin(["2023", "2024"]) & frame.clock_et.str.match(r"^[0-2][0-9]:[0-5][0-9]:00$")].copy()
        pieces.append(frame[["issuer", "event_date", "clock_et", "pdicity"]])
    all_rows = pd.concat(pieces, ignore_index=True)
    # ANN and QTR rows can describe the same economic release. One clock is one event.
    unique = all_rows.drop_duplicates(["issuer", "event_date", "clock_et"]).sort_values(["issuer", "event_date", "clock_et"])
    unique["year"] = unique.event_date.str[:4].astype(int)
    unique["within_issuer_year_order"] = unique.groupby(["issuer", "year"]).cumcount() + 1
    chosen = unique[unique.within_issuer_year_order <= 4].copy()
    counts = chosen.groupby(["issuer", "year"]).size()
    if set(counts.index) != {(i, y) for i in IBES_TICKER for y in (2023, 2024)} or not (counts == 4).all():
        raise RuntimeError(f"requires four releases per issuer/year; got {counts.to_dict()}")
    chosen["event_id"] = chosen.apply(lambda r: f"EARN_{r.issuer}_{r.event_date.replace('-', '')}", axis=1)
    chosen["selection_rank"] = chosen.issuer.map(RANK)
    chosen["inherited_report_weight"] = chosen.issuer.map(WEIGHT)
    chosen["split"] = chosen.event_date.map(split)
    chosen["event_time_utc"] = chosen.apply(lambda r: iso_utc(r.event_date, r.clock_et), axis=1)
    chosen["session"] = chosen.clock_et.map(lambda x: "PREMARKET" if x < "09:30:00" else ("RTH" if x < "16:00:00" else "AFTER_HOURS"))
    chosen["clock_authority"] = "EXISTING_SCC_IBES_ACTUALS_METADATA_CANDIDATE"
    chosen["clock_precision"] = "MINUTE"
    chosen["primary_first_public_clock_status"] = "NOT_YET_VERIFIED"
    return chosen.sort_values(["event_date", "clock_et", "issuer"]), audit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ibes", type=Path, action="append", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    events, audit = read_events(args.ibes)
    event_days = {issuer: set(group.event_date) for issuer, group in events.groupby("issuer")}
    controls = []
    for row in events.itertuples(index=False):
        control_day, ordinal = fifth_prior(row.event_date, event_days[row.issuer])
        controls.append({
            "event_id": row.event_id, "issuer": row.issuer, "event_date": row.event_date,
            "control_date": control_day, "control_rank_previous_nyse_session": ordinal,
            "same_clock_et": row.clock_et, "control_time_utc": iso_utc(control_day, row.clock_et),
            "split": row.split, "selection_rule": "fifth prior NYSE full trading session; skip same-issuer earnings dates; no outcome selection",
        })
    controls = pd.DataFrame(controls)
    public_cols = ["event_id", "issuer", "event_date", "clock_et", "event_time_utc", "session", "year", "within_issuer_year_order", "selection_rank", "inherited_report_weight", "split", "clock_authority", "clock_precision", "primary_first_public_clock_status"]
    events[public_cols].to_csv(args.out / "EVENT_MANIFEST.csv", index=False)
    controls.to_csv(args.out / "CONTROL_MANIFEST.csv", index=False)
    analysis = []
    requests = []
    for event in events.itertuples(index=False):
        control = controls.loc[controls.event_id == event.event_id].iloc[0]
        for kind, day in (("EVENT", event.event_date), ("CONTROL", control.control_date)):
            sample_id = f"{event.event_id}_{kind}"
            anchor = event.clock_et
            analysis.append({"sample_id": sample_id, "event_id": event.event_id, "issuer": event.issuer, "date": day, "sample_kind": kind, "split": event.split, "anchor_et": anchor, "anchor_utc": iso_utc(day, anchor), "session": event.session})
            for dataset in ("XNAS.ITCH", "ARCX.PILLAR", "GLBX.MDP3"):
                tag = dataset.replace(".", "_")
                request_id = f"{sample_id}_{tag}"
                symbols = ";".join(SYMBOLS) if dataset != "GLBX.MDP3" else "ES.v.0"
                requests.append({
                    "request_id": request_id, "sample_id": sample_id, "event_id": event.event_id,
                    "issuer": event.issuer, "date": day, "sample_kind": kind, "split": event.split,
                    "anchor_et": anchor, "anchor_utc": iso_utc(day, anchor), "dataset": dataset,
                    "schema": "mbp-1", "stype_in": "raw_symbol" if dataset != "GLBX.MDP3" else "continuous",
                    "symbols": symbols, "symbol_count": len(SYMBOLS) if dataset != "GLBX.MDP3" else 1,
                    "start_utc": shift_minutes(day, anchor, -11), "end_utc": shift_minutes(day, anchor, 17),
                    "analysis_window": "anchor[-10m,+16m); request adds one-minute state/tail buffer",
                    "reuse_status": "PENDING_EXACT_SCC_CHECK", "raw_path": "PENDING",
                })
    analysis = pd.DataFrame(analysis)
    requests = pd.DataFrame(requests)
    if len(events) != 48 or len(analysis) != 96 or len(requests) != 288:
        raise RuntimeError("fixed design requires 48 events, 96 logical windows and 288 source requests")
    analysis.to_csv(args.out / "ANALYSIS_WINDOWS.csv", index=False)
    requests.to_csv(args.out / "REQUEST_MANIFEST.csv", index=False)
    payload = {
        "status": "PREPARED_UNQUOTED", "events": 48, "logical_windows": 96,
        "requests": 288, "equity_requests": 192, "futures_requests": 96,
        "symbols": SYMBOLS, "source_audit": audit,
        "clock_warning": "I/B/E/S announcement metadata supplies candidate minute anchors; primary first-public times remain explicitly unverified",
        "requests_detail": requests.to_dict("records"),
    }
    (args.out / "REQUEST_MANIFEST.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (args.out / "ROSTER_MANIFEST.json").write_text(json.dumps({"status": "FIXED_BEFORE_NEW_RESPONSES", "sampling_rule": "inherited report weight descending, stable symbol tie-break, ranks 1/5/9/14/18/23", "issuers": [{"issuer": i, "rank": RANK[i], "weight": WEIGHT[i]} for i in sorted(RANK, key=RANK.get)], "BF_excluded": "not present in actual inherited feature panel"}, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()

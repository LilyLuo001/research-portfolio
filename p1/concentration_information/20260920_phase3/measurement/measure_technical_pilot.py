#!/usr/bin/env python3
"""Measure the frozen two-event quote pilot on SCC.

Raw quote levels and row-level returns remain on SCC.  Git-safe outputs contain
coverage, aggregate high-minus-low summaries, and a 20-observation provenance
trace without price levels.  Two events from one issuer cannot support power or
identification claims.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import databento as db

from quote_state import Update, sample_endpoints, simple_midpoint_response

try:
    from databento_dbn import UNDEF_ORDER_SIZE, UNDEF_PRICE
except ImportError:
    UNDEF_PRICE, UNDEF_ORDER_SIZE = 9223372036854775807, 4294967295


NS = 1_000_000_000
HORIZONS = (5, 15, 30, 60)
NY = ZoneInfo("America/New_York")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else ["status"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def ns(value: datetime) -> int:
    return int(value.timestamp() * NS)


def iso(value: int | None) -> str:
    if value is None:
        return ""
    return datetime.fromtimestamp(value / NS, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def session_at(value: int) -> str:
    local = datetime.fromtimestamp(value / NS, NY)
    minute = local.hour * 60 + local.minute
    if minute < 9 * 60 + 30:
        return "PRE"
    if minute < 16 * 60:
        return "RTH"
    return "AFTER"


def row_values(record) -> tuple[int | None, int | None, int | None, int | None]:
    try:
        values = (record.bid_px_00, record.ask_px_00, record.bid_sz_00, record.ask_sz_00)
    except AttributeError:
        level = record.levels[0]
        values = (level.bid_px, level.ask_px, level.bid_sz, level.ask_sz)
    out = []
    for value in values:
        try:
            out.append(int(value))
        except (TypeError, ValueError):
            out.append(None)
    bid, ask, bid_size, ask_size = out
    if bid in (UNDEF_PRICE, 0) or bid is not None and bid < 0:
        bid = None
    if ask in (UNDEF_PRICE, 0) or ask is not None and ask < 0:
        ask = None
    if bid_size in (UNDEF_ORDER_SIZE, 0) or bid_size is not None and bid_size < 0:
        bid_size = None
    if ask_size in (UNDEF_ORDER_SIZE, 0) or ask_size is not None and ask_size < 0:
        ask_size = None
    return bid, ask, bid_size, ask_size


def reverse_mapping(store) -> dict[int, str]:
    reverse = {}
    for raw_symbol, intervals in store.metadata.mappings.items():
        for interval in intervals:
            instrument_id = int(interval["symbol"])
            if instrument_id in reverse and reverse[instrument_id] != raw_symbol:
                raise RuntimeError("instrument maps to more than one raw symbol inside one file")
            reverse[instrument_id] = raw_symbol
    return reverse


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--clock", required=True, type=Path)
    parser.add_argument("--event-symbols", required=True, type=Path)
    parser.add_argument("--selected", required=True, type=Path)
    parser.add_argument("--download-receipt", required=True, type=Path)
    parser.add_argument("--dbn-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    with args.proposal.open(newline="") as handle:
        proposal = list(csv.DictReader(handle))
    proposal_event_ids = {row["event_id"] for row in proposal}
    with args.clock.open(newline="") as handle:
        clocks = {row["event_id"]: row for row in csv.DictReader(handle) if row["supports_5m"] in {"YES", "CONDITIONAL"} and row["event_id"] in proposal_event_ids}
    with args.event_symbols.open(newline="") as handle:
        event_symbols = list(csv.DictReader(handle))
    with args.selected.open(newline="") as handle:
        selected = {row["receiver_id"]: row for row in csv.DictReader(handle)}
    receipt = json.loads(args.download_receipt.read_text())
    files = {row["bundle_id"]: row for row in receipt["files"]}
    assert receipt["status"] == "COMPLETE_NATIVE_DBN_UNOPENED"
    assert len(proposal) == len(files) and set(clocks) == proposal_event_ids

    event_receiver = defaultdict(dict)
    for row in event_symbols:
        event_receiver[row["event_id"]][row["symbol"]] = row["receiver_id"]
    assert all(len(rows) == 20 for rows in event_receiver.values())

    private_rows = []
    reference_rows = []
    raw_counts = Counter()
    stream_anomalies = []
    for request in proposal:
        file_row = files[request["bundle_id"]]
        path = args.dbn_root / Path(file_row["path"]).name
        if not path.is_file() or sha(path) != file_row["sha256"]:
            raise RuntimeError(f"missing or mismatched DBN: {path}")
        store = db.DBNStore.from_file(path)
        reverse = reverse_mapping(store)
        updates = defaultdict(list)
        streams = defaultdict(set)
        for record in store:
            if type(record).__name__ != "BBOMsg":
                raise RuntimeError(f"unexpected record type in bbo-1s file: {type(record).__name__}")
            symbol = reverse.get(int(record.instrument_id))
            if symbol is None:
                raise RuntimeError("record instrument absent from DBN mapping")
            timestamp = int(record.ts_recv)
            bid, ask, bid_size, ask_size = row_values(record)
            updates[symbol].append(Update(
                timestamp=timestamp, session=session_at(timestamp), bid=bid, ask=ask,
                bid_size=bid_size, ask_size=ask_size,
                withdrawn=False, halted=False,
            ))
            streams[symbol].add((str(record.publisher_id), str(record.instrument_id)))
            raw_counts[(request["event_id"], request["dataset"])] += 1
        for symbol, keys in streams.items():
            if len(keys) != 1:
                stream_anomalies.append({"event_id": request["event_id"], "dataset": request["dataset"], "symbol": symbol, "streams": len(keys)})

        clock = clocks[request["event_id"]]
        lower, upper = parse(clock["earliest_bound_et"]), parse(clock["latest_bound_et"])
        baseline_target = ns(lower - timedelta(minutes=5))
        post_targets = [ns(upper + timedelta(minutes=h)) for h in HORIZONS]
        target_times = [(baseline_target, session_at(baseline_target))]
        target_times += [(target, session_at(target)) for target in post_targets]
        for symbol in request["symbols_semicolon"].split(";"):
            endpoints = sample_endpoints(updates.get(symbol, []), target_times)
            baseline = endpoints[0]
            results = {}
            for horizon, endpoint in zip(HORIZONS, endpoints[1:]):
                response = simple_midpoint_response(baseline, endpoint)
                results[horizon] = {
                    "response_bps": None if response is None else response * 10000,
                    "status": endpoint.status,
                    "source_timestamp": endpoint.source_timestamp,
                    "age_seconds": None if endpoint.source_timestamp is None else (endpoint.target - endpoint.source_timestamp) / NS,
                }
            row = {
                "event_id": request["event_id"], "dataset": request["dataset"],
                "symbol": symbol, "baseline_status": baseline.status,
                "baseline_source_timestamp": baseline.source_timestamp,
                "baseline_age_seconds": None if baseline.source_timestamp is None else (baseline.target - baseline.source_timestamp) / NS,
                "file_sha256": file_row["sha256"],
            }
            for horizon in HORIZONS:
                for key, value in results[horizon].items():
                    row[f"h{horizon}_{key}"] = value
            receiver_id = event_receiver[request["event_id"]].get(symbol)
            if receiver_id:
                row.update({
                    "receiver_id": receiver_id,
                    "connection_role": selected[receiver_id]["connection_role"],
                    "same_sic2_as_any_issuer": selected[receiver_id]["same_sic2_as_any_issuer"],
                })
                private_rows.append(row)
            else:
                row["reference_type"] = "SOURCE" if symbol == "XOM" else symbol
                reference_rows.append(row)

    private_path = args.out / "PRIVATE_RECEIVER_RESPONSES.csv"
    write_csv(private_path, private_rows)
    write_csv(args.out / "PRIVATE_REFERENCE_RESPONSES.csv", reference_rows)

    coverage_rows = []
    for dataset in sorted({row["dataset"] for row in private_rows}):
        for horizon in HORIZONS:
            subset = [row for row in private_rows if row["dataset"] == dataset]
            valid = [row for row in subset if row[f"h{horizon}_response_bps"] is not None]
            coverage_rows.append({
                "dataset": dataset, "horizon_minutes": horizon,
                "receiver_event_rows": len(subset), "valid_response_rows": len(valid),
                "valid_fraction": len(valid) / len(subset),
                "events_with_all_20_valid": sum(all(
                    row[f"h{horizon}_response_bps"] is not None
                    for row in subset if row["event_id"] == event_id
                ) for event_id in clocks),
                "max_endpoint_age_seconds": max((row[f"h{horizon}_age_seconds"] for row in valid), default=None),
            })
    write_csv(args.out / "COVERAGE_SUMMARY.csv", coverage_rows)

    pair_rows = []
    for event_id in sorted(clocks):
        for dataset in sorted({row["dataset"] for row in private_rows}):
            rows = [row for row in private_rows if row["event_id"] == event_id and row["dataset"] == dataset]
            by_id = {row["receiver_id"]: row for row in rows}
            for prefix in ("S", "C"):
                for pair in range(1, 6):
                    high = by_id[f"{prefix}{pair:02d}_HIGH"]
                    low = by_id[f"{prefix}{pair:02d}_LOW"]
                    for horizon in HORIZONS:
                        hv, lv = high[f"h{horizon}_response_bps"], low[f"h{horizon}_response_bps"]
                        pair_rows.append({
                            "event_id": event_id, "dataset": dataset,
                            "pair_id": f"{prefix}{pair:02d}", "horizon_minutes": horizon,
                            "high_minus_low_bps": None if hv is None or lv is None else hv - lv,
                            "common_valid": hv is not None and lv is not None,
                        })
    write_csv(args.out / "PRIVATE_PAIR_DIFFERENCES.csv", pair_rows)

    aggregate_rows = []
    for dataset in sorted({row["dataset"] for row in pair_rows}):
        for prefix, stratum in (("S", "same_industry"), ("C", "cross_industry"), ("", "all")):
            for horizon in HORIZONS:
                subset = [row for row in pair_rows if row["dataset"] == dataset and row["horizon_minutes"] == horizon and (not prefix or row["pair_id"].startswith(prefix))]
                values = [float(row["high_minus_low_bps"]) for row in subset if row["high_minus_low_bps"] is not None]
                aggregate_rows.append({
                    "dataset": dataset, "stratum": stratum, "horizon_minutes": horizon,
                    "pair_event_rows": len(subset), "common_valid_rows": len(values),
                    "mean_high_minus_low_bps": mean(values),
                    "positive_fraction": sum(value > 0 for value in values) / len(values) if values else None,
                    "unique_event_dates": len(clocks),
                    "independence_status": "NOT_ESTABLISHED",
                    "inference_status": "DESCRIPTIVE_ONLY_NO_SE_OR_P_VALUE",
                })
    write_csv(args.out / "AGGREGATE_PAIR_SUMMARY.csv", aggregate_rows)

    # Trace exactly 20 receiver observations privately (first event, first
    # venue, 15-minute endpoint). Git receives aggregate status counts only;
    # row timestamps remain on SCC pending explicit redistribution clearance.
    trace_dataset = sorted({row["dataset"] for row in private_rows})[0]
    trace_source = [row for row in private_rows if row["event_id"] == sorted(clocks)[0] and row["dataset"] == trace_dataset]
    assert len(trace_source) == 20
    trace_rows = []
    for row in sorted(trace_source, key=lambda x: x["receiver_id"]):
        trace_rows.append({
            "event_id": row["event_id"], "dataset": row["dataset"],
            "receiver_id": row["receiver_id"], "symbol": row["symbol"],
            "baseline_status": row["baseline_status"],
            "baseline_source_timestamp_utc": iso(row["baseline_source_timestamp"]),
            "h15_status": row["h15_status"],
            "h15_source_timestamp_utc": iso(row["h15_source_timestamp"]),
            "h15_response_available": row["h15_response_bps"] is not None,
            "raw_file_sha256": row["file_sha256"],
        })
    write_csv(args.out / "PRIVATE_TRACE20.csv", trace_rows)
    trace_counts = Counter((row["baseline_status"], row["h15_status"], str(row["h15_response_available"])) for row in trace_rows)
    trace_audit = [{
        "event_id": trace_rows[0]["event_id"], "dataset": trace_rows[0]["dataset"],
        "baseline_status": key[0], "h15_status": key[1],
        "h15_response_available": key[2], "observation_count": count,
        "raw_file_sha256": trace_rows[0]["raw_file_sha256"],
        "validation_scope": "AGGREGATE_MISSINGNESS_PROVENANCE_NOT_20_VALID_ENDPOINTS",
    } for key, count in sorted(trace_counts.items())]
    write_csv(args.out / "TRACE_AUDIT.csv", trace_audit)

    summary = {
        "status": "PARTIAL_TECHNICAL_COVERAGE_DIAGNOSTIC",
        "events": len(clocks), "issuers": 1, "receivers": 20,
        "venues": len({row["dataset"] for row in proposal}),
        "raw_bbo_records": {"|".join(key): value for key, value in sorted(raw_counts.items())},
        "receiver_event_venue_rows": len(private_rows),
        "reference_event_venue_rows": len(reference_rows),
        "stream_anomalies": stream_anomalies,
        "private_trace_observations": len(trace_rows),
        "trace_validation_status": "MISSINGNESS_PROVENANCE_ONLY_NOT_20_VALID_ENDPOINTS",
        "private_outputs_stay_on_scc": [private_path.name, "PRIVATE_REFERENCE_RESPONSES.csv", "PRIVATE_PAIR_DIFFERENCES.csv", "PRIVATE_TRACE20.csv"],
        "git_safe_outputs": ["COVERAGE_SUMMARY.csv", "AGGREGATE_PAIR_SUMMARY.csv", "TRACE_AUDIT.csv", "PILOT_SUMMARY.json"],
        "scientific_decision": "HOLD_DATA",
        "reason": f"This diagnostic contains {len(clocks)} conditional PRE_OPEN technical anchor date(s) from one issuer; first-public status is not certified, live-state status data are absent, and identification/power are not estimable.",
        "adapter_limits": "BBO snapshots are validated from sides/sizes. No halt or withdrawal state is inferred from stringified flags; non-BBOMsg records are a hard error. Session is derived from America/New_York timestamp. No separate status feed was acquired, so carried-state liveness remains unverified.",
        "no_claims": ["causal identification", "empirical power", "price-discovery share", "SIP NBBO", "research GO"],
        "inputs": {
            "proposal_sha256": sha(args.proposal), "clock_sha256": sha(args.clock),
            "event_symbols_sha256": sha(args.event_symbols), "selected_sha256": sha(args.selected),
            "download_receipt_sha256": sha(args.download_receipt),
        },
    }
    write_json(args.out / "PILOT_SUMMARY.json", summary)
    print(json.dumps({"status": summary["status"], "receiver_rows": len(private_rows), "trace": len(trace_rows), "decision": summary["scientific_decision"]}))


if __name__ == "__main__":
    main()

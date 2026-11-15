"""Read-only VM-side aggregate of benchmark20's timing/token ledger, not raw output.

No API/model/cloud-control calls, no input advertisement or response files, no writes.
ATTEMPTS stores request forwarding time but not response end time: this script
therefore does not invent per-request latency or separate limiter sleep durations.
"""
import collections
import datetime
import hashlib
import json
import math
import statistics
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def distribution(values):
    values = sorted(values)
    if not values:
        return {"n": 0}
    return {
        "n": len(values), "sum": sum(values), "mean": statistics.mean(values),
        "min": values[0], "p50": statistics.median(values),
        "p90_nearest_rank": values[math.ceil(.9 * len(values)) - 1],
        "max": values[-1],
    }


def aggregate(events, state, config):
    assert state["status"] == "finite_benchmark_completed", "run_not_completed"
    assert state["completed"] == 20 and config["max_records"] == 20, "scope_changed"
    latest = {}
    for event in events:
        key = (event["ordinal"], event["attempt"])
        assert 0 <= key[0] < 20 and 1 <= key[1] <= 2, "ledger_key_out_of_scope"
        latest[key] = event
    assert len(latest) == state["physical_attempts"], "physical_attempt_count_mismatch"
    attempts = sorted(latest.values(), key=lambda e: e["forwarded_epoch"])
    forwarded = [e["forwarded_epoch"] for e in attempts]
    assert all(isinstance(t, (int, float)) and math.isfinite(t) for t in forwarded)
    gaps = [b - a for a, b in zip(forwarded, forwarded[1:])]
    status = collections.Counter(str(e.get("http_status", "unreported")) for e in attempts)
    terminal = collections.Counter(str(e.get("status", "unreported")) for e in attempts)
    usage = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        usage[key] = distribution([e["usage"][key] for e in attempts if key in e.get("usage", {})])
    assert usage["prompt_tokens"].get("sum", 0) == state["input_tokens"]
    assert usage["completion_tokens"].get("sum", 0) == state["output_tokens"]
    header_summary = {}
    # Intentionally excludes opaque request IDs and does not echo arbitrary headers.
    for name in ("x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens", "x-ratelimit-limit-requests", "retry-after-ms", "retry-after"):
        values = []
        nonnumeric = 0
        for event in attempts:
            headers = event.get("rate_headers", {})
            if name not in headers:
                continue
            try:
                value = float(headers[name])
                assert math.isfinite(value) and value >= 0
                values.append(value)
            except (ValueError, TypeError, AssertionError):
                nonnumeric += 1
        header_summary[name] = {"numeric": distribution(values), "nonnumeric_omitted": nonnumeric}
    token_windows = []
    request_windows = []
    for i, event in enumerate(attempts):
        members = [other for other in attempts[:i + 1] if event["forwarded_epoch"] - other["forwarded_epoch"] < 60]
        token_windows.append(sum(member["token_reservation"] for member in members))
        request_windows.append(len(members))
    start = datetime.datetime.fromisoformat(state["started_at_utc"]).timestamp()
    finish = datetime.datetime.fromisoformat(state["finished_at_utc"]).timestamp()
    return {
        "status": "completed_ledger_metadata_aggregated_no_inference",
        "raw_advertisements_or_response_payloads_read": 0,
        "model_calls": 0, "cloud_or_run_policy_changes": 0, "writes": 0,
        "lifecycle_event_count": len(events), "physical_attempts": len(attempts),
        "unique_ordinals": len({e["ordinal"] for e in attempts}),
        "http_status_counts": dict(status), "terminal_status_counts": dict(terminal),
        "retry_attempts": sum(e["attempt"] > 1 for e in attempts),
        "usage": usage,
        "token_reservation": distribution([e["token_reservation"] for e in attempts]),
        "reservation_usd": distribution([e["reservation_usd"] for e in attempts]),
        "forwarded_interarrival_seconds": distribution(gaps),
        "first_to_last_forwarded_seconds": forwarded[-1] - forwarded[0] if forwarded else None,
        "start_to_first_forwarded_seconds": forwarded[0] - start if forwarded else None,
        "last_forwarded_to_finish_seconds": finish - forwarded[-1] if forwarded else None,
        "worker_elapsed_seconds": state["elapsed_seconds"],
        "trailing_60s_at_forwarding_max_reserved_tokens": max(token_windows, default=0),
        "trailing_60s_at_forwarding_max_requests": max(request_windows, default=0),
        "rate_headers": header_summary,
        "configured_concurrency": config["concurrency"],
        "configured_tpm_ceiling": config["scheduled_tpm_ceiling"],
        "configured_max_completion_tokens": config["max_completion_tokens"],
        "timing_limitations": [
            "Interarrival includes prior request service, validation, I/O, authentication and any local limiter wait; not request latency.",
            "The worker does not record response_finished_epoch or separate limiter_wait_seconds; exact decomposition is unavailable retrospectively.",
            "Last-forwarded-to-finish includes final request, validation and bookkeeping; it is not pure model service time.",
            "A single-concurrency finite benchmark does not establish saturated parallel throughput.",
        ],
    }


def main():
    directory = Path.home() / "migration/reuse_first_20261115/run01/benchmark20"
    names = ["RUN_STATUS_PUBLIC.json", "BENCHMARK_CONFIG_PUBLIC.json", "ATTEMPTS_PRIVATE.jsonl"]
    blobs = {}
    for name in names:
        path = directory / name
        assert path.is_file() and path.stat().st_size <= 64 * 1024 * 1024, "metadata_input_bound"
        blobs[name] = path.read_bytes()
    state = json.loads(blobs[names[0]])
    config = json.loads(blobs[names[1]])
    events = [json.loads(line) for line in blobs[names[2]].splitlines() if line.strip()]
    result = aggregate(events, state, config)
    result["observed_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result["source_sha256"] = {name: digest(data) for name, data in blobs.items()}
    assert all((directory / name).read_bytes() == data for name, data in blobs.items()), "source_changed"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "metadata_probe_failed", "error_type": type(error).__name__, "private_error_text_omitted": True}))
        raise SystemExit(2)

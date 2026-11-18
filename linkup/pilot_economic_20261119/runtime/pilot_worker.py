"""Explicitly launched direct Azure worker; default first-100 checkpoint only.

No OpenCode, credential files, source truncation, response repair, or auto-cap reset.
One shared ledger covers all legs and batches. Already-admitted requests may finish
after another thread trips the global stop; no further admissions are allowed.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import pilot_common as c

CLOUD_RUN = Path("/home/linkup/migration/pilot_economic_20261119/run01")
WORKFLOW_DIRECTORY = Path("/home/linkup/migration/code")
ENDPOINT = "https://rg-linkup.openai.azure.com/openai/v1/"
ARM_IDENTITY_SHA256 = "25352e137d33a6c8ab2088b0fe2f2da322764263561a95e78204bd1b55035870"
SAFE_HEADERS = {"x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens", "x-ratelimit-limit-requests",
                "retry-after-ms", "retry-after", "x-request-id", "apim-request-id"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def identity_token_function(directory):
    if Path(directory).resolve() != WORKFLOW_DIRECTORY:
        raise c.BoundaryError("unapproved_identity_helper_path")
    sys.path.insert(0, str(WORKFLOW_DIRECTORY))
    from workflow import token
    return token


def expected_model_allowed(leg, model, directory, policy):
    if model in c.MODELS[leg]["returned_models"]:
        return True
    if leg != "Kimi" or model != "Kimi-K3.1":
        return False
    pin = policy.get("kimi_arm_evidence", {})
    if pin.get("sha256") != ARM_IDENTITY_SHA256:
        return False
    arm_path = c.safe_file(directory, pin.get("path", ""))
    if c.sha(arm_path) != ARM_IDENTITY_SHA256:
        return False
    arm = c.read(arm_path)
    return (arm.get("status") == "existing_deployment_ARM_metadata_verified"
        and arm.get("account") == "rg-linkup" and arm.get("deployment") == c.MODELS["Kimi"]["deployment"]
        and arm.get("model") == {"format": "MoonshotAI", "name": "Kimi-K3.1-Pro", "version": "2026-11-04"}
        and arm.get("provisioning_state") == "Succeeded"
        and arm.get("sku") == {"name": "GlobalStandard", "capacity": 3000}
        and arm.get("endpoint") == "https://rg-linkup.cognitiveservices.azure.com/")


def visible_view(leg, response):
    usage = response.get("usage") or {}
    if leg != "Astra":
        choices = response["choices"]
        if len(choices) != 1:
            raise c.BoundaryError("unexpected_choice_count")
        choice, message = choices[0], choices[0]["message"]
        return dict(content=message.get("content") or "", refusal=bool(message.get("refusal")),
            filtered=choice.get("finish_reason") == "content_filter", complete=choice.get("finish_reason") == "stop",
            returned_model=response.get("model"), usage=usage)
    parts = [p for obj in response.get("output", []) if obj.get("type") == "message" for p in obj.get("content", [])]
    reason = (response.get("incomplete_details") or {}).get("reason")
    return dict(content="\n".join(p.get("text", "") for p in parts if p.get("type") == "output_text"),
        refusal=any(p.get("type") == "refusal" for p in parts),
        filtered=(response.get("error") or {}).get("code") in ("content_filter", "ResponsibleAIPolicyViolation") or reason == "content_filter",
        complete=response.get("status") == "completed", returned_model=response.get("model"),
        usage={"prompt_tokens": usage.get("input_tokens"), "completion_tokens": usage.get("output_tokens"), "total_tokens": usage.get("total_tokens")})


def atomic_jsonl(path, rows):
    tmp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    with tmp.open("xb") as stream:
        os.chmod(tmp, 0o600)
        stream.write(b"".join(c.encoded(row) + b"\n" for row in rows))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def run(args):
    os.umask(0o077)
    directory = Path(args.directory).resolve()
    if directory != CLOUD_RUN:
        raise c.BoundaryError("new_cloud_run_directory_required")
    if args.leg not in c.MODELS or not 1 <= args.concurrency <= 4 or not 1 <= args.max_new_logical <= c.MODELS[args.leg]["logical"]:
        raise c.BoundaryError("launch_bounds_invalid")
    if not 1 <= args.max_wall_seconds <= 604800:
        raise c.BoundaryError("wall_limit_invalid")
    policy, items, exclusions, batch = c.load_bundle(directory, args.policy, args.batch_manifest, args.batch_manifest_sha256)
    policy_sha = c.sha(args.policy)
    for name, path in (("field_validator", args.field_validator), ("frozen_validator", args.frozen_validator)):
        if policy.get("runtime_sha256", {}).get(name) != c.sha(path):
            raise c.BoundaryError("frozen_validator_pin_mismatch")
    adapter = c.import_path("pilot_field_adapter", args.field_validator)
    frozen = c.import_path("pilot_frozen_validator", args.frozen_validator)
    frozen.validate_packet([c.packet_for_validation(item, args.leg) for item in items])
    schema = c.read(directory / "SCHEMA.json")
    deadline = time.time() + args.max_wall_seconds
    stop_file = Path(args.stop_file) if args.stop_file else directory / "STOP_REQUESTED"
    stop = threading.Event()
    ledger = c.Ledger(directory, policy, policy_sha)
    token = identity_token_function(args.workflow_directory)
    counter_lock = threading.Lock()
    counters = {"cache_hits": 0, "terminal_results": 0, "unprocessed": 0}

    def base_result(item, status):
        return dict(case=str(item["case"]), record_id=item["row"]["record_id"],
            context_sha256=item["row"]["context_sha256"], leg=args.leg,
            payload=None, field_validation=None, status=status, policy_sha256=policy_sha,
            protocol_version=c.VERSION, batch_manifest_sha256=batch["manifest_sha256"])

    def cached(item):
        previous = ledger.latest(args.leg, item["row"]["context_sha256"])
        if previous and previous["result_path"]:
            path = c.safe_file(directory, previous["result_path"])
            if c.sha(path) != previous["result_sha"]:
                ledger.hold("saved_output_sha_mismatch")
                raise c.BoundaryError("saved_output_sha_mismatch")
            result = c.read(path)
            if result["context_sha256"] != item["row"]["context_sha256"] or result["policy_sha256"] != policy_sha:
                ledger.hold("saved_output_identity_mismatch")
                raise c.BoundaryError("saved_output_identity_mismatch")
            return result
        return None

    def one(item):
        context = item["row"]["context_sha256"]
        prior = cached(item)
        if prior is not None:
            with counter_lock:
                counters["cache_hits"] += 1
            return prior
        dest = directory / "results" / args.leg / context
        result_path = dest / "RESULT_PRIVATE.json"
        carrier = base_result(item, "not_forwarded")
        body = c.encoded(c.model_payload(directory, args.leg, item, exclusions))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        while not stop.is_set():
            attempt = None
            try:
                auth = token("https://cognitiveservices.azure.com/")
                if not isinstance(auth, str) or not auth:
                    ledger.hold("identity_token_unavailable")
                    raise c.BoundaryError("identity_token_unavailable")
                attempt = ledger.reserve(args.leg, item, body, deadline, args.max_new_logical, stop_file)
                request = urllib.request.Request(ENDPOINT + c.MODELS[args.leg]["api"], data=body,
                    headers={"Authorization": "Bearer " + auth, "Content-Type": "application/json"}, method="POST")
                auth = None
                try:
                    response = opener.open(request, timeout=min(300, max(1, deadline - time.time())))
                except urllib.error.HTTPError as exc:
                    response = exc
                with response:
                    status = response.status
                    headers = {k.lower(): v for k, v in response.headers.items() if k.lower() in SAFE_HEADERS}
                    raw = response.read(4_000_001)
                raw_path = dest / ("HTTP_%06d_PRIVATE.bin" % attempt)
                c.immutable(raw_path, raw)
                detail = dict(http_status=status, rate_headers=headers, raw_sha256=c.sha(raw_path))
                filtered = b"content_filter" in raw or b"ResponsibleAIPolicyViolation" in raw
                if len(raw) > 4_000_000:
                    state = "response_size_hold"
                elif status != 200:
                    last = ledger.latest(args.leg, context)
                    state = ("quarantined_provider_filter" if filtered else
                        "retryable_confirmed_http" if status in c.RETRY_HTTP and last["attempt"] < 2 else "http_error_terminal")
                    if state == "retryable_confirmed_http":
                        ledger.finish(attempt, state, detail)
                        attempt = None
                        continue
                else:
                    try:
                        view = visible_view(args.leg, c.parse_json(raw))
                    except Exception:
                        view = None
                    if view is None:
                        state = "invalid_response_envelope_hold"
                    else:
                        detail.update({k: view[k] for k in ("returned_model", "complete", "filtered", "refusal")})
                        filtered = view["filtered"] or view["refusal"]
                        usage = view["usage"]
                        usage_ok = all(type(usage.get(k)) is int and usage[k] >= 0
                            for k in ("prompt_tokens", "completion_tokens", "total_tokens"))
                        if usage_ok:
                            detail["usage"] = {k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
                            carrier["usage"] = detail["usage"]
                        c.immutable(dest / "VISIBLE_RESPONSE_PRIVATE.txt", view["content"].encode())
                        if filtered:
                            state = "quarantined_provider_filter_or_refusal"
                        elif not expected_model_allowed(args.leg, view["returned_model"], directory, policy):
                            state = "returned_model_identity_mismatch_hold"
                        elif not usage_ok:
                            state = "usage_missing_or_invalid_hold"
                        elif not view["complete"]:
                            state = "incomplete_output_preserved"
                        else:
                            try:
                                review = adapter.parse_review(view["content"])
                                validation = adapter.FieldValidator(schema, frozen).validate(
                                    c.packet_for_validation(item, args.leg), review, protected=False)
                                carrier.update(payload=review, field_validation=validation)
                                state = "field_local_validation_complete"
                            except Exception as exc:
                                state = "invalid_output_preserved"
                                carrier["error_type"] = type(exc).__name__
                carrier["status"] = state
                # Detect usage breach before writing the immutable result as well as in the ledger.
                u = detail.get("usage", {})
                if u.get("prompt_tokens", 0) > len(body) + 1024 or u.get("completion_tokens", 0) > c.MODELS[args.leg]["output"]:
                    carrier.update(payload=None, field_validation=None, status="usage_reservation_breach_stop")
                    state = carrier["status"]
                c.immutable(result_path, c.encoded(carrier) + b"\n")
                ledger.finish(attempt, state, detail, result_path, quarantined=filtered)
                attempt = None
                if ledger.summary()["admission_hold"]:
                    stop.set()
                with counter_lock:
                    counters["terminal_results"] += 1
                return carrier
            except c.BoundaryError as exc:
                carrier["status"] = str(exc)
                if attempt is not None:
                    ledger.finish(attempt, "transport_uncertain_no_retry", {"error_type": type(exc).__name__})
                    stop.set()
                else:
                    last = ledger.latest(args.leg, context)
                    if last and last["state"] == "retryable_confirmed_http":
                        c.immutable(result_path, c.encoded(carrier) + b"\n")
                        ledger.settle_retry(args.leg, context, str(exc), result_path)
                if (str(exc).startswith("global_hold_") or str(exc) in ("persistent_attempt_or_dollar_cap",
                    "phase_dollar_cap", "launch_logical_ceiling", "wall_limit_before_call", "operator_stop_file", "identity_token_unavailable")):
                    stop.set()
                return carrier
            except Exception as exc:
                carrier.update(status="transport_uncertain_no_retry" if attempt else "local_or_identity_failure_hold", error_type=type(exc).__name__)
                if attempt is not None:
                    ledger.finish(attempt, "transport_uncertain_no_retry", {"error_type": type(exc).__name__})
                else:
                    ledger.hold("local_or_identity_failure_hold")
                stop.set()
                return carrier
        return base_result(item, "unprocessed_bounded_stop")

    with c.process_lock(directory, args.leg):
        ledger.register_batch(batch)
        ledger.recover_orphans(args.leg)
        if ledger.summary()["admission_hold"]:
            stop.set()
        results = {}
        iterator = iter(items)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            pending = {}
            while True:
                while not stop.is_set() and len(pending) < args.concurrency:
                    item = next(iterator, None)
                    if item is None:
                        break
                    pending[pool.submit(one, item)] = item
                if not pending:
                    break
                completed, _ = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in completed:
                    item = pending.pop(future)
                    try:
                        results[item["row"]["context_sha256"]] = future.result()
                    except Exception as exc:
                        ledger.hold("worker_task_failure_hold")
                        stop.set()
                        results[item["row"]["context_sha256"]] = base_result(item, "worker_task_failure_hold")
                c.save(directory / "RUN_STATUS_PUBLIC.json", ledger.summary())
        outputs = []
        for item in items:
            context = item["row"]["context_sha256"]
            result = results.get(context)
            if result is None:
                try:
                    result = cached(item)
                except Exception:
                    ledger.hold("cached_output_unreadable")
            outputs.append(result or base_result(item, "unprocessed_bounded_stop"))
        output_path = directory / ("OUTPUTS_%s_%s_PRIVATE.jsonl" % (args.leg.upper(), batch["batch_id"]))
        atomic_jsonl(output_path, outputs)
        final = ledger.summary()
        final.update(leg=args.leg, policy_sha256=policy_sha, batch_manifest_sha256=batch["manifest_sha256"],
            current_batch_contexts=len(items), outputs_accounted=len(outputs), output_sha256=c.sha(output_path),
            field_validation_complete=sum(row["status"] == "field_local_validation_complete" for row in outputs),
            unprocessed=sum(row["status"] == "unprocessed_bounded_stop" for row in outputs),
            launch_logical_ceiling=args.max_new_logical, concurrency=args.concurrency, counters=counters,
            continuation_requires_explicit_launch=True)
        c.save(directory / (args.leg.upper() + "_FINAL_PUBLIC.json"), final)
        c.save(directory / "RUN_STATUS_PUBLIC.json", final)
        if args.leg == "Luna" and args.max_new_logical <= 100 and not (directory / "CHECKPOINT_FIRST_BATCH_PUBLIC.json").exists():
            c.immutable(directory / "CHECKPOINT_FIRST_BATCH_PUBLIC.json", c.encoded(final) + b"\n")
        if args.leg == "Luna" and final["legs"]["Luna"]["logical_calls"] >= 100 and not (directory / "CHECKPOINT_100_PUBLIC.json").exists():
            c.immutable(directory / "CHECKPOINT_100_PUBLIC.json", c.encoded(final) + b"\n")
        print(json.dumps(final), flush=True)
        return final


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leg", choices=list(c.MODELS), required=True)
    parser.add_argument("--directory", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--batch-manifest")
    parser.add_argument("--batch-manifest-sha256")
    parser.add_argument("--field-validator", required=True)
    parser.add_argument("--frozen-validator", required=True)
    parser.add_argument("--workflow-directory", default=str(WORKFLOW_DIRECTORY))
    parser.add_argument("--max-new-logical", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--max-wall-seconds", type=int, default=14400)
    parser.add_argument("--stop-file")
    args = parser.parse_args()
    try:
        run(args)
    except Exception as exc:
        print(json.dumps({"fatal_error_type": type(exc).__name__, "raw_exception_not_logged": True}), flush=True)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

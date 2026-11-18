"""Finite Luna or Astra MI worker. Run only after root's explicit dispatch.

No old worker/state is imported. API shape and deployment remain model-specific.
The only authentication read is migration/code/workflow.token in memory.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
from stage5_common import (BoundaryError, Ledger, MODELS, RETRY_HTTP, blocked, encoded,
    immutable, import_path, load_inputs, model_payload, packet_for_validation,
    parse_json, process_lock, read, save, sha, validate_output, verify_output_frame)

ENDPOINT = "https://rg-linkup.openai.azure.com/openai/v1/"
SAFE_HEADERS = {"x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens",
                "x-ratelimit-limit-requests", "retry-after-ms", "retry-after",
                "x-request-id", "apim-request-id"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def visible_view(leg, response):
    if leg == "Luna":
        choice = response["choices"][0]
        message = choice["message"]
        return dict(content=message.get("content") or "", refusal=bool(message.get("refusal")),
                    filtered=choice.get("finish_reason") == "content_filter",
                    complete=choice.get("finish_reason") == "stop",
                    returned_model=response.get("model"), usage=response.get("usage") or {})
    parts = [p for obj in response.get("output", []) if obj.get("type") == "message"
             for p in obj.get("content", [])]
    code = (response.get("error") or {}).get("code")
    reason = (response.get("incomplete_details") or {}).get("reason")
    usage = response.get("usage") or {}
    return dict(content="\n".join(p.get("text", "") for p in parts if p.get("type") == "output_text"),
                refusal=any(p.get("type") == "refusal" for p in parts),
                filtered=code in ("content_filter", "ResponsibleAIPolicyViolation") or reason == "content_filter",
                complete=response.get("status") == "completed",
                returned_model=response.get("model"),
                usage={"prompt_tokens": usage.get("input_tokens", 0),
                       "completion_tokens": usage.get("output_tokens", 0),
                       "total_tokens": usage.get("total_tokens", 0)})


def run(args):
    os.umask(0o077)
    directory = Path(args.directory)
    items, pins = load_inputs(directory, args.leg)
    for name, path in (("field_validator", args.field_validator), ("frozen_validator", args.frozen_validator)):
        if pins["runtime_sha256"].get(name) != sha(path):
            raise BoundaryError("frozen_validator_pin_mismatch")
    packets = [packet_for_validation(x, args.leg) for x in items if not blocked(x)]
    if packets:
        import_path("preflight_frozen_validator", args.frozen_validator).validate_packet(packets)
    # This import is restricted to the established in-VM managed-identity helper.
    workflow_dir = Path(args.workflow_directory).resolve()
    if workflow_dir != Path.home() / "migration/code":
        raise BoundaryError("unapproved_identity_helper_path")
    sys.path.insert(0, str(workflow_dir))
    from workflow import token
    ledger = Ledger(directory, args.leg, items, pins)
    opener = urllib.request.build_opener(NoRedirect())
    deadline = time.time() + min(args.max_wall_seconds, 14400)
    stop = False
    with process_lock(directory):
        for item in items:
            case = str(item["case"])
            dest = directory / "results" / case
            dest.mkdir(parents=True, exist_ok=True)
            output = dest / "RESULT_PRIVATE.json"
            if output.exists():
                verify_output_frame([item], [read(output)], pins["roster_sha256"])
                continue
            carrier = {"record_id": item["row"]["record_id"],
                       "context_sha256": item["row"]["context_sha256"],
                       "roster_sha256": pins["roster_sha256"],
                       "case": case, "leg": args.leg, "payload": None,
                       "field_validation": None, "status": "not_forwarded"}
            if blocked(item):
                carrier["status"] = "blocked_protected_metadata_only"
                save(output, carrier)
                continue
            payload = model_payload(directory, args.leg, item)
            body = encoded(payload)
            while not stop:
                attempt_id = None
                try:
                    # Get credentials before admission; no model request on identity failure.
                    auth = token("https://cognitiveservices.azure.com/")
                    if not isinstance(auth, str) or not auth:
                        raise BoundaryError("identity_token_unavailable")
                    attempt_id = ledger.reserve(case, body, deadline=deadline)
                    req = urllib.request.Request(ENDPOINT + MODELS[args.leg]["api"], data=body,
                        headers={"Authorization": "Bearer " + auth, "Content-Type": "application/json"}, method="POST")
                    auth = None
                    try:
                        response = opener.open(req, timeout=min(300, max(1, deadline - time.time())))
                    except urllib.error.HTTPError as exc:
                        response = exc
                    with response:
                        status = response.status
                        headers = {k.lower(): v for k, v in response.headers.items() if k.lower() in SAFE_HEADERS}
                        raw = response.read(4_000_001)
                    immutable(dest / ("HTTP_%04d_PRIVATE.bin" % attempt_id), raw)
                    detail = dict(http_status=status, rate_headers=headers,
                                  raw_sha256=sha(dest / ("HTTP_%04d_PRIVATE.bin" % attempt_id)))
                    if len(raw) > 4_000_000:
                        raise BoundaryError("response_bound_exceeded")
                    if status != 200:
                        filtered = b"content_filter" in raw or b"ResponsibleAIPolicyViolation" in raw
                        state = ("quarantined_provider_filter" if filtered else
                                 "retryable_confirmed_http" if status in RETRY_HTTP else "http_error_terminal")
                        ledger.finish(attempt_id, state, detail, quarantined=filtered)
                        attempt_id = None
                        if state == "retryable_confirmed_http" and ledger.latest(case)["attempt"] < 2:
                            continue
                        carrier["status"] = state
                        stop = status in (401, 403)
                        break
                    view = visible_view(args.leg, parse_json(raw))
                    detail.update({k: view[k] for k in ("returned_model", "usage", "complete", "filtered", "refusal")})
                    usage = view["usage"]
                    detail["usage"] = {k: usage.get(k, 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
                    quarantine = view["filtered"] or view["refusal"]
                    expected = ({"gpt-6-luna-2026-09-22"} if args.leg == "Luna"
                                else {"linkup-gpt-6-astra"})
                    mismatch = view["returned_model"] not in expected
                    state = ("quarantined_provider_filter_or_refusal" if quarantine else
                             "returned_model_identity_mismatch_hold" if mismatch else "response_saved")
                    ledger.finish(attempt_id, state, detail, quarantined=quarantine)
                    attempt_id = None
                    immutable(dest / "VISIBLE_RESPONSE_PRIVATE.txt", view["content"].encode())
                    carrier["usage"] = detail["usage"]
                    carrier["status"] = state
                    if quarantine:
                        break
                    if mismatch:
                        stop = True
                        break
                    if not view["complete"]:
                        carrier["status"] = "incomplete_output_preserved"
                        break
                    try:
                        review, validation = validate_output(directory, item, view["content"], args.field_validator, args.frozen_validator, args.leg)
                        carrier.update(payload=review, field_validation=validation, status="field_local_validation_complete")
                    except Exception as exc:
                        carrier.update(status="invalid_output_preserved", error_type=type(exc).__name__)
                    break
                except BoundaryError as exc:
                    carrier.update(status=str(exc))
                    if attempt_id is not None:
                        ledger.finish(attempt_id, "transport_uncertain_no_retry", {"error_type": type(exc).__name__})
                        stop = True
                    if str(exc) in ("persistent_attempt_or_dollar_cap", "wall_limit_before_call",
                                    "active_or_interrupted_request_hold", "identity_token_unavailable"):
                        stop = True
                    break
                except Exception as exc:
                    carrier.update(status="transport_or_identity_failure_preserved", error_type=type(exc).__name__)
                    if attempt_id is not None:
                        ledger.finish(attempt_id, "transport_uncertain_no_retry", {"error_type": type(exc).__name__})
                    stop = True
                    break
            save(output, carrier)
            save(directory / "RUN_STATUS_PUBLIC.json", ledger.summary())
            if stop:
                break
        # Account for the entire frozen denominator even when budget or transport stopped.
        results = []
        for item in items:
            p = directory / "results" / str(item["case"]) / "RESULT_PRIVATE.json"
            if not p.exists():
                save(p, dict(case=str(item["case"]), record_id=item["row"]["record_id"],
                    context_sha256=item["row"]["context_sha256"], leg=args.leg, payload=None,
                    roster_sha256=pins["roster_sha256"], field_validation=None,
                    status="blocked_protected_metadata_only" if blocked(item) else "unprocessed_bounded_stop"))
            results.append(read(p))
        output_roster = verify_output_frame(items, results, pins["roster_sha256"])
        immutable(directory / "OUTPUTS_PRIVATE.jsonl", b"".join(encoded(x) + b"\n" for x in results))
        exclusions = read(directory / "EXCLUSIONS_PRIVATE.json")
        with ledger.db() as db:
            exclusions["context_sha256"] = sorted(set(exclusions.get("context_sha256", [])) | {x[0] for x in db.execute("SELECT context FROM quarantine")})
        save(directory / "EXCLUSIONS_EXPORT_PRIVATE.json", exclusions)
        final = ledger.summary(terminal=True)
        final["outputs_accounted"] = len(results)
        final["field_validation_complete"] = sum(x["status"] == "field_local_validation_complete" for x in results)
        final["output_sha256"] = sha(directory / "OUTPUTS_PRIVATE.jsonl")
        final["output_roster_sha256"] = output_roster
        final["exclusions_sha256"] = sha(directory / "EXCLUSIONS_EXPORT_PRIVATE.json")
        save(directory / (args.leg.upper() + "_FINAL_PUBLIC.json"), final)
        print(json.dumps(final), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leg", choices=("Luna", "Astra"), required=True)
    parser.add_argument("--directory", required=True)
    parser.add_argument("--field-validator", required=True)
    parser.add_argument("--frozen-validator", required=True)
    parser.add_argument("--workflow-directory", default=str(Path.home() / "migration/code"))
    parser.add_argument("--max-wall-seconds", type=int, default=14400)
    args = parser.parse_args()
    try:
        run(args)
    except Exception as exc:
        print(json.dumps({"fatal_error_type": type(exc).__name__, "raw_exception_not_logged": True}), flush=True)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

"""Direct Azure MI Kimi transport with immutable v2 carry-forward; no OpenCode.

The six-file runtime layout is retained so stage5_prepare pins this worker.
The legacy-named gateway file is never imported or used by this worker.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import signal
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
from stage5_common import (BoundaryError, Ledger, MODELS, NOTICE, RETRY_HTTP, blocked,
    encoded, immutable, kimi_prompt, load_inputs, parse_json, process_lock, read, save,
    sha, verify_output_frame)

TRANSPORT_REVISION = "stage5-kimi-direct-azure-v3"
ENDPOINT = "https://rg-linkup.openai.azure.com/openai/v1/chat/completions"
SAFE_HEADERS = {"x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens",
                "x-ratelimit-limit-requests", "retry-after-ms", "retry-after",
                "x-request-id", "apim-request-id"}
HOLD_STATES = {"forwarding_uncertain", "transport_uncertain_no_retry",
               "usage_reservation_breach_stop", "returned_model_identity_mismatch_hold"}
ALLOWED_STATES = HOLD_STATES | {"response_saved", "incomplete_output_preserved",
    "retryable_confirmed_http", "http_error_terminal", "quarantined_provider_filter",
    "quarantined_provider_filter_or_refusal"}
APPROVED_PRIOR_CODE_SHA256 = {
    "stage5_common.py": "0a60b9078459c8bf711025024b36b86acec78d9bea1afcb4e8f9181bd1b1e808",
    "stage5_cloud_worker.py": "38bca82363482b8ed41dc54823aae68155ab94f5a4087d485e1b7275fe7ccaff",
    "stage5_kimi_gateway.py": "2b12dc3991091985a166e388a9c50587044838a73fe7486e6539a6f233931a3c",
    "stage5_kimi_worker.py": "a016292eb8b437a54c93e661dad9cae608c267274c63240e0b9e6c1b27118dab",
    "stage5_prepare.py": "b267b052716e3ec8064071d458e8afb2cdf0c6db96b7075fd45520c6aab00c69",
    "stage5_validate_kimi.py": "49ef1c307f72b47ada72c372e768fff0306886050def3283c9859c23ce4f7e9a",
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def direct_payload(directory, item):
    return {"model": MODELS["Kimi"]["deployment"],
            "messages": [{"role": "system", "content": NOTICE},
                         {"role": "user", "content": kimi_prompt(directory, item)}],
            "max_tokens": MODELS["Kimi"]["output"], "stream": False}


def imported_contexts(ledger):
    with ledger.db() as db:
        return {x[0] for x in db.execute("SELECT context FROM prior_contexts")}


def _source_file(prior, name):
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or "opencode.json" in path.parts:
        raise BoundaryError("unsafe_prior_manifest_path")
    target = prior / path
    if target.is_symlink() or not target.is_file() or prior not in target.resolve().parents:
        raise BoundaryError("prior_manifest_file_missing_or_unsafe")
    return target


def import_prior(directory, prior_directory, closure_path):
    """Read a stopped hash-pinned source, then atomically seed a NEW ledger.

    A prior admitted context is never retry-eligible in this transport, even if
    its previous state was a confirmed retryable HTTP error. Source originals
    are read-only. An uncertain source may be imported but holds every new call.
    """
    directory, prior = Path(directory).resolve(), Path(prior_directory).resolve()
    if directory == prior:
        raise BoundaryError("prior_and_direct_directory_must_differ")
    items, pins = load_inputs(directory, "Kimi")
    closure = read(closure_path)
    if (closure.get("status") != "stopped_prior_transport_closed"
            or closure.get("worker_stopped") is not True
            or closure.get("roster_sha256") != pins["roster_sha256"]):
        raise BoundaryError("prior_stopped_closure_required")
    manifest = closure.get("prior_files_sha256", {})
    if not isinstance(manifest, dict):
        raise BoundaryError("prior_manifest_required")
    for name in ("INPUT_PINS_PUBLIC.json", "ADMISSION_PRIVATE.sqlite3"):
        if name not in manifest:
            raise BoundaryError("prior_manifest_required")
    for name, digest in manifest.items():
        if sha(_source_file(prior, name)) != digest:
            raise BoundaryError("prior_file_pin_mismatch")
    source_pins = read(prior / "INPUT_PINS_PUBLIC.json")
    if (source_pins.get("roster_sha256") != pins["roster_sha256"]
            or source_pins.get("code_sha256") != APPROVED_PRIOR_CODE_SHA256):
        raise BoundaryError("prior_runtime_or_roster_not_approved")
    for name, digest in source_pins["sha256"].items():
        if manifest.get(name) != digest:
            raise BoundaryError("prior_scientific_file_not_pinned")
    for name in ("SCHEMA.json", "INSTRUCTIONS.md", "FRAME_ROSTER_PRIVATE.json",
                 "LUNA_FINAL_PUBLIC.json", "PREDECESSOR_EXCLUSIONS_PRIVATE.json"):
        if source_pins["sha256"].get(name) != pins["sha256"].get(name):
            raise BoundaryError("prior_scientific_frame_or_predecessor_changed")
    source_items = [parse_json(x) for x in (prior / "INPUTS_PRIVATE.jsonl").read_text().splitlines() if x.strip()]
    source_by_case = {str(x["case"]): x for x in source_items}
    by_case = {str(x["case"]): x for x in items}
    identities = lambda rows: {(str(x["case"]), x["row"]["record_id"], x["row"]["context_sha256"]) for x in rows}
    if len(source_by_case) != len(source_items) or identities(items) != identities(source_items):
        raise BoundaryError("prior_frame_identity_mismatch")
    dbpath = prior / "ADMISSION_PRIVATE.sqlite3"
    with sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True) as source:
        source.row_factory = sqlite3.Row
        if source.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise BoundaryError("prior_ledger_integrity_failure")
        attempts = [dict(x) for x in source.execute("SELECT * FROM attempts ORDER BY id")]
        claims = [tuple(x) for x in source.execute("SELECT context,case_id FROM claims")]
        quarantine = [tuple(x) for x in source.execute("SELECT context,reason FROM quarantine")]
        meta = dict(source.execute("SELECT key,value FROM meta"))
    if sha(dbpath) != manifest["ADMISSION_PRIVATE.sqlite3"]:
        raise BoundaryError("prior_ledger_changed_during_import")
    identity = parse_json(meta.get("identity", "{}"))
    if identity.get("leg") != "Kimi" or identity.get("pins") != source_pins or identity.get("policy") != MODELS["Kimi"]:
        raise BoundaryError("prior_ledger_identity_mismatch")
    contexts = {x["context"] for x in attempts}
    if set(claims) != {(x["context"], x["case_id"]) for x in attempts}:
        raise BoundaryError("prior_claim_attempt_mismatch")
    sums = dict(physical_attempts=len(attempts), logical_calls=len(contexts),
                reserved_nano=sum(x["dollars_nano"] for x in attempts))
    if any(closure.get(k) != v for k, v in sums.items()):
        raise BoundaryError("prior_closure_ledger_totals_mismatch")
    if (sums["physical_attempts"] > MODELS["Kimi"]["physical"]
            or sums["logical_calls"] > MODELS["Kimi"]["logical"]
            or sums["reserved_nano"] > MODELS["Kimi"]["cap_nano"]):
        raise BoundaryError("prior_cap_already_exceeded")
    latest = {}
    quarantined = {x[0] for x in quarantine}
    for row in attempts:
        case = row["case_id"]
        if (case not in by_case or row["context"] != by_case[case]["row"]["context_sha256"]
                or row["state"] not in ALLOWED_STATES or not 1 <= row["attempt"] <= 2
                or row["input_upper"] < 1024 or row["tokens"] != row["input_upper"] + 16000
                or row["dollars_nano"] != row["input_upper"] * 2300 + 16000 * 11500):
            raise BoundaryError("prior_attempt_contract_mismatch")
        if row["context"] not in quarantined:
            old = source_by_case[case]
            if blocked(old) or blocked(by_case[case]) or old["row"] != by_case[case]["row"]:
                raise BoundaryError("prior_nonquarantined_source_changed")
            base = direct_payload(prior, old)
            bodies = [encoded(base)]
            base["stream"] = True
            base["stream_options"] = {"include_usage": True}
            bodies.append(encoded(base))
            if not any(hashlib.sha256(body).hexdigest() == row["request_sha"]
                       and len(body) + 1024 == row["input_upper"] for body in bodies):
                raise BoundaryError("prior_request_not_frozen_scientific_contract")
        if row["state"].startswith("quarantined_") and row["context"] not in quarantined:
            raise BoundaryError("prior_filter_quarantine_missing")
        latest[case] = row
    for context in quarantined:
        match = [x for x in items if x["row"]["context_sha256"] == context]
        if len(match) != 1 or not blocked(match[0]):
            raise BoundaryError("prior_quarantine_requires_metadata_only_preparation")
    held = any(x["state"] in HOLD_STATES for x in attempts)
    if closure.get("terminal_no_active_requests") != (not held):
        raise BoundaryError("prior_terminal_claim_inconsistent")
    # Copy only scientific visible bytes; no credentials, config or session store.
    visible = {}
    for case, row in latest.items():
        if row["state"] in ("response_saved", "incomplete_output_preserved"):
            name = "results/" + case + "/VISIBLE_RESPONSE_PRIVATE.txt"
            if name not in manifest:
                raise BoundaryError("prior_visible_response_missing_no_replay")
            raw = _source_file(prior, name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != manifest[name]:
                raise BoundaryError("prior_visible_response_pin_mismatch")
            visible[case] = raw
    import_sha = sha(closure_path)
    ledger = Ledger(directory, "Kimi", items, pins)
    with process_lock(directory):
        with ledger.db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS prior_imports (digest TEXT PRIMARY KEY, details TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS prior_contexts (context TEXT PRIMARY KEY, case_id TEXT UNIQUE NOT NULL, prior_state TEXT NOT NULL)")
            existing = db.execute("SELECT digest FROM prior_imports").fetchall()
            if existing and [x[0] for x in existing] != [import_sha]:
                raise BoundaryError("prior_import_identity_changed")
            if not existing:
                if db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] or db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]:
                    raise BoundaryError("prior_import_requires_empty_direct_ledger")
                db.execute("BEGIN IMMEDIATE")
                for row in attempts:
                    keys = list(row)
                    db.execute("INSERT INTO attempts (" + ",".join(keys) + ") VALUES (" + ",".join("?" for _ in keys) + ")", [row[k] for k in keys])
                db.executemany("INSERT INTO claims VALUES (?,?)", claims)
                db.executemany("INSERT INTO quarantine VALUES (?,?)", quarantine)
                db.executemany("INSERT INTO prior_contexts VALUES (?,?,?)", [(r["context"], case, r["state"]) for case, r in latest.items()])
                db.executemany("INSERT OR REPLACE INTO meta VALUES (?,?)", [(k, v) for k, v in meta.items() if k in ("tpm", "rpm", "cooldown", "remaining", "remaining_at")])
                db.execute("INSERT INTO prior_imports VALUES (?,?)", (import_sha, encoded(sums).decode()))
        for case, raw in visible.items():
            target = directory / "results" / case / "VISIBLE_RESPONSE_PRIVATE.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            immutable(target, raw)
        receipt = dict(status="prior_Kimi_admissions_imported_no_replay", transport_revision=TRANSPORT_REVISION,
            roster_sha256=pins["roster_sha256"], new_input_pins_sha256=sha(directory / "INPUT_PINS_PUBLIC.json"),
            prior_closure_sha256=import_sha, imported_physical_attempts=sums["physical_attempts"],
            imported_logical_calls=sums["logical_calls"], imported_reserved_nano=sums["reserved_nano"],
            imported_visible_responses=len(visible), admission_hold=held, all_prior_admitted_contexts_skipped=True,
            combined_Kimi_ledger_includes_prior=True, double_count_prior_cost_again=False, new_model_calls=0,
            preserved_prior_rate_windows=True, frozen_scheduled_tpm=MODELS["Kimi"]["tpm"],
            prior_quota_headers=closure.get("verified_response_TPM_headers", []))
        immutable(directory / "PRIOR_IMPORT_PUBLIC.json", encoded(receipt) + b"\n")
        immutable(directory / "PRIOR_CLOSURE_PUBLIC.json", Path(closure_path).read_bytes())
        return receipt


def _carrier(item, pins, ledger, directory):
    case = str(item["case"])
    latest = ledger.latest(case)
    carrier = dict(case=case, record_id=item["row"]["record_id"], context_sha256=item["row"]["context_sha256"],
        roster_sha256=pins["roster_sha256"], leg="Kimi", payload=None, field_validation=None,
        status="blocked_protected_metadata_only" if blocked(item) else latest["state"] if latest else "unprocessed_bounded_stop",
        response_text=None, transport=parse_json(latest["detail"]) if latest and not blocked(item) else None)
    path = directory / "results" / case / "VISIBLE_RESPONSE_PRIVATE.txt"
    if not blocked(item) and latest and latest["state"] in ("response_saved", "incomplete_output_preserved") and path.exists():
        carrier["response_text"] = path.read_text()
    return carrier


def run_direct(args, token_provider=None, opener=None, stop_event=None):
    os.umask(0o077)
    directory = Path(args.directory).resolve()
    items, pins = load_inputs(directory, "Kimi")
    prior = read(directory / "PRIOR_IMPORT_PUBLIC.json")
    if (prior.get("transport_revision") != TRANSPORT_REVISION
            or prior.get("new_input_pins_sha256") != sha(directory / "INPUT_PINS_PUBLIC.json")
            or prior.get("prior_closure_sha256") != sha(directory / "PRIOR_CLOSURE_PUBLIC.json")):
        raise BoundaryError("direct_prior_import_required")
    if (directory / "KIMI_FINAL_PUBLIC.json").exists():
        raise BoundaryError("direct_final_already_exists_no_relaunch")
    ledger = Ledger(directory, "Kimi", items, pins)
    skipped = imported_contexts(ledger)
    if len(skipped) != prior["imported_logical_calls"]:
        raise BoundaryError("prior_context_skip_set_mismatch")
    with ledger.db() as db:
        records = db.execute("SELECT digest,details FROM prior_imports").fetchall()
        if len(records) != 1 or records[0]["digest"] != prior["prior_closure_sha256"]:
            raise BoundaryError("prior_import_database_marker_mismatch")
        recorded = parse_json(records[0]["details"])
        observed = db.execute("SELECT COUNT(*),COALESCE(SUM(dollars_nano),0),COUNT(DISTINCT context) FROM attempts WHERE context IN (SELECT context FROM prior_contexts)").fetchone()
        expected = (prior["imported_physical_attempts"], prior["imported_reserved_nano"], prior["imported_logical_calls"])
        if tuple(observed) != expected or any(recorded[k] != v for k, v in zip(
                ("physical_attempts", "reserved_nano", "logical_calls"), expected)):
            raise BoundaryError("prior_import_cost_decomposition_mismatch")
    stop_event = stop_event or threading.Event()
    if token_provider is None:
        workflow = Path(args.workflow_directory).resolve()
        if workflow != Path.home() / "migration/code":
            raise BoundaryError("unapproved_identity_helper_path")
        sys.path.insert(0, str(workflow))
        from workflow import token
        token_provider = token
    opener = opener or urllib.request.build_opener(NoRedirect())
    deadline = time.time() + min(args.max_wall_seconds, 14400)
    stop = bool(prior.get("admission_hold"))
    with process_lock(directory):
        for item in items:
            case, context = str(item["case"]), item["row"]["context_sha256"]
            # All prior admissions (success/error/uncertain/filter) are permanently
            # excluded before source prompt construction or credential access.
            if context in skipped or blocked(item):
                continue
            if stop or stop_event.is_set() or time.time() >= deadline:
                break
            latest = ledger.latest(case)
            if latest is not None:
                # No restart replay, even a previously confirmed retryable error.
                if latest["state"] in HOLD_STATES:
                    stop = True
                continue
            dest = directory / "results" / case
            dest.mkdir(parents=True, exist_ok=True)
            body = encoded(direct_payload(directory, item))
            while not stop and not stop_event.is_set():
                attempt_id = None
                try:
                    auth = token_provider("https://cognitiveservices.azure.com/")
                    if not isinstance(auth, str) or not auth:
                        raise BoundaryError("identity_token_unavailable")
                    if stop_event.is_set():
                        break
                    attempt_id = ledger.reserve(case, body, deadline=deadline)
                    if stop_event.is_set():
                        ledger.finish(attempt_id, "transport_uncertain_no_retry", {"provider_forwarded": False, "stop_after_reservation": True})
                        attempt_id = None
                        stop = True
                        break
                    request = urllib.request.Request(ENDPOINT, data=body,
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
                    detail = {"http_status": status, "rate_headers": headers, "response_bytes": len(raw),
                              "transport_revision": TRANSPORT_REVISION}
                    if len(raw) > 4_000_000:
                        raise BoundaryError("response_size_bound")
                    if status != 200:
                        # A bounded symbolic provider code is diagnostic metadata;
                        # never retain/print its free-text message or raw body.
                        try:
                            error = parse_json(raw).get("error", {})
                            code = error.get("code") if isinstance(error, dict) else None
                            if isinstance(code, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,95}", code):
                                detail["error_code"] = code
                        except Exception:
                            pass
                        filtered = b"content_filter" in raw or b"ResponsibleAIPolicyViolation" in raw
                        state = ("quarantined_provider_filter" if filtered else
                                 "retryable_confirmed_http" if status in RETRY_HTTP else "http_error_terminal")
                        ledger.finish(attempt_id, state, detail, quarantined=filtered)
                        attempt_id = None
                        if state == "retryable_confirmed_http" and ledger.latest(case)["attempt"] < 2 and not stop_event.is_set():
                            continue
                        stop = status in (401, 403, 404)
                        break
                    obj = parse_json(raw)
                    choices = obj.get("choices", [])
                    if len(choices) != 1 or not isinstance(choices[0].get("message"), dict):
                        raise BoundaryError("response_choice_shape_rejected")
                    choice, usage = choices[0], obj.get("usage")
                    content = choice["message"].get("content") or ""
                    if not isinstance(content, str):
                        raise BoundaryError("response_content_shape_rejected")
                    refused = bool(choice["message"].get("refusal"))
                    filtered = choice.get("finish_reason") == "content_filter" or refused
                    complete = choice.get("finish_reason") == "stop" and not filtered
                    returned_model = obj.get("model")
                    expected_models = {MODELS["Kimi"]["model"], MODELS["Kimi"]["deployment"], "Kimi-K3.1-Pro-2026-11-04"}
                    mismatch = returned_model not in expected_models
                    detail.update(usage={k: (usage or {}).get(k, 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
                        usage_reported=usage is not None, finish_reasons=[choice.get("finish_reason")],
                        complete=complete, filtered=filtered, returned_model=returned_model)
                    state = ("quarantined_provider_filter_or_refusal" if filtered else
                             "returned_model_identity_mismatch_hold" if mismatch else
                             "response_saved" if complete else "incomplete_output_preserved")
                    # Only visible content is preserved; no provider reasoning is saved.
                    immutable(dest / "VISIBLE_RESPONSE_PRIVATE.txt", content.encode())
                    ledger.finish(attempt_id, state, detail, quarantined=filtered)
                    attempt_id = None
                    stop = state in HOLD_STATES
                    break
                except Exception as exc:
                    if attempt_id is not None:
                        ledger.finish(attempt_id, "transport_uncertain_no_retry", {"error_type": type(exc).__name__})
                    save(dest / "EXECUTION_PRIVATE.json", {"case": case,
                        "status": str(exc) if isinstance(exc, BoundaryError) else "direct_transport_or_identity_failure",
                        "error_type": type(exc).__name__})
                    stop = True
                    break
            save(directory / "RUN_STATUS_PUBLIC.json", ledger.summary())
        outputs = [_carrier(item, pins, ledger, directory) for item in items]
        output_roster = verify_output_frame(items, outputs, pins["roster_sha256"])
        immutable(directory / "OUTPUTS_PRIVATE.jsonl", b"".join(encoded(x) + b"\n" for x in outputs))
        exclusions = read(directory / "EXCLUSIONS_PRIVATE.json")
        with ledger.db() as db:
            exclusions["context_sha256"] = sorted(set(exclusions.get("context_sha256", [])) | {x[0] for x in db.execute("SELECT context FROM quarantine")})
        save(directory / "EXCLUSIONS_EXPORT_PRIVATE.json", exclusions)
        final = ledger.summary(terminal=True)
        final.update(transport_revision=TRANSPORT_REVISION, authentication="existing_Azure_VM_managed_identity",
            no_OpenCode_used=True, outputs_accounted=len(outputs), output_roster_sha256=output_roster,
            output_sha256=sha(directory / "OUTPUTS_PRIVATE.jsonl"), exclusions_sha256=sha(directory / "EXCLUSIONS_EXPORT_PRIVATE.json"),
            combined_Kimi_totals_include_prior=True, prior_imported_physical_attempts=prior["imported_physical_attempts"],
            prior_imported_reserved_nano=prior["imported_reserved_nano"], prior_imported_logical_calls=prior["imported_logical_calls"],
            new_direct_physical_attempts=final["physical_attempts"]-prior["imported_physical_attempts"],
            prior_closure_sha256=prior["prior_closure_sha256"], requested_stop=stop_event.is_set(),
            semantic_validation_location="Azure_after_transport")
        save(directory / "KIMI_FINAL_PUBLIC.json", final)
        print(json.dumps(final), flush=True)
        return final


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--import-prior-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--prior-directory")
    parser.add_argument("--prior-closure")
    parser.add_argument("--workflow-directory", default=str(Path.home() / "migration/code"))
    parser.add_argument("--max-wall-seconds", type=int, default=14400)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.import_prior_only:
            if not args.prior_directory or not args.prior_closure:
                raise BoundaryError("prior_source_and_closure_required")
            print(json.dumps(import_prior(args.directory, args.prior_directory, args.prior_closure)), flush=True)
        else:
            stop = threading.Event()
            for signum in (signal.SIGINT, signal.SIGTERM):
                signal.signal(signum, lambda *_: stop.set())
            run_direct(args, stop_event=stop)
    except Exception as exc:
        print(json.dumps({"fatal_error_type": type(exc).__name__, "raw_exception_not_logged": True}), flush=True)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

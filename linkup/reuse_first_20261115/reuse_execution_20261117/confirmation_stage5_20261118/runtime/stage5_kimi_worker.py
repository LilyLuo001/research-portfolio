"""Strictly serial existing local OpenCode sessions; private visible transport only.

No semantic validation or model inference implementation runs locally. Kimi runs
on the existing pinned Azure deployment through the established OpenCode route.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from stage5_common import (BoundaryError, Ledger, blocked, encoded, immutable, kimi_prompt,
    load_inputs, parse_json, process_lock, read, save, sha, verify_output_frame)
from stage5_kimi_gateway import make_server

CLI = Path.home() / "Library/Application Support/ai.opencode.desktop/cli/2.2.7-arm64/opencode-cli"
PRIVATE_CONFIG = Path.home() / ".local/share/opencode/private/linkup-kimi-bulk1309-20261115/opencode.json"
MODEL = {"providerID": "azure-kimi", "id": "linkup-kimi-k3-1-pro"}
PERMISSIONS = [{"action": "*", "resource": "*", "effect": "deny"}]
AZURE_BASE_URL = "https://rg-linkup.openai.azure.com/openai/v1"
# Read-only provenance verified on 2026-11-18. This is a saved legacy loopback
# configuration, not a new approved origin. Stage 5 never connects to this port;
# it replaces only the private working copy's URL with its own bounded gateway.
LEGACY_ROUTE = {
    "url": "http://127\0560\0560\0561:60735/bulk1309/openai/v1",
    "configuration_sha256": "11f4f1177b545399a9b4c5a0818b67a06662d7b7388abde35350700156ed3b29",
    "gateway_public_sha256": "134c0d2d175f3bb31cfbc3c844e4f8a3024206caf6bc4212e775330c6f8ba00c",
    "launch_public_sha256": "43df32324f32452a42fcb96cde04a24281e34e1ede26b35bd6bd3182ab09ee95",
    "gateway_source_sha256": "6bdeed552edb42afdc9fa379fba0a08f9f26114fba15cd4c954b03dbc5970588",
    "gateway_source": Path.home() / "Documents/LinkUp_Resume_Review_20261110/opencode_bulk_20261115/quota_gateway_300k.py",
}


def verify_legacy_route(base):
    """Accept one known historical loopback configuration with exact provenance."""
    if base != LEGACY_ROUTE["url"]:
        raise BoundaryError("original_kimi_endpoint_not_approved")
    gateway_path = PRIVATE_CONFIG.parent / "GATEWAY_PUBLIC.json"
    launch_path = PRIVATE_CONFIG.parent / "ACTIVE_LAUNCH_PUBLIC.json"
    checks = {"configuration_sha256": sha(PRIVATE_CONFIG),
              "gateway_public_sha256": sha(gateway_path),
              "launch_public_sha256": sha(launch_path),
              "gateway_source_sha256": sha(LEGACY_ROUTE["gateway_source"])}
    if any(checks[key] != LEGACY_ROUTE[key] for key in checks):
        raise BoundaryError("legacy_kimi_route_provenance_mismatch")
    gateway, launch = read(gateway_path), read(launch_path)
    if (gateway.get("bind") != "127\0560\0560\0561" or gateway.get("port") != 60735
            or launch.get("gateway_pid") != gateway.get("pid")
            or launch.get("gateway_sha256") != LEGACY_ROUTE["gateway_source_sha256"]
            or Path(launch.get("gateway_file", "")) != LEGACY_ROUTE["gateway_source"]):
        raise BoundaryError("legacy_kimi_route_receipt_mismatch")
    return checks


def route_preflight():
    """Auth-program-only config read; return booleans/hashes, never credential values."""
    if not CLI.is_file() or not os.access(CLI, os.X_OK):
        raise BoundaryError("pinned_opencode_cli_unavailable")
    config = read(PRIVATE_CONFIG)
    provider = config.get("providers", {}).get("azure-kimi")
    if not isinstance(provider, dict) or not isinstance(provider.get("settings"), dict):
        raise BoundaryError("existing_azure_kimi_provider_missing")
    base = provider["settings"].get("baseURL", "")
    if not isinstance(base, str):
        raise BoundaryError("original_kimi_endpoint_not_approved")
    if base.rstrip("/") == AZURE_BASE_URL:
        route_kind, provenance = "existing_azure_direct", None
    else:
        provenance = verify_legacy_route(base)
        route_kind = "verified_legacy_loopback_to_existing_azure"
    return dict(status="local_route_metadata_preflight_pass_no_call", model=MODEL,
        cli_version_path="2.2.7-arm64", pinned_cli_exists=True,
        cli_sha256=sha(CLI), original_configuration_sha256=sha(PRIVATE_CONFIG),
        existing_azure_provider=True, original_endpoint_approved=True,
        original_endpoint_kind=route_kind, legacy_route_provenance=provenance,
        approved_upstream_base_url=AZURE_BASE_URL,
        credential_values_printed=False, new_model_calls=0, real_ports_bound=0)


def api(directory, method, path, body=None):
    args = [str(CLI), "api", method, path]
    if body is not None:
        data = encoded(body).decode()
        if len(data.encode()) > 120000:
            raise BoundaryError("cli_control_body_bound")
        args.extend(["--data", data])
    completed = subprocess.run(args, cwd=directory, capture_output=True, text=True, timeout=45)
    if completed.returncode:
        raise BoundaryError("opencode_control_failed")
    return parse_json(completed.stdout) if completed.stdout.strip() else None


def idle(session):
    clock = session.get("time", {})
    return not clock.get("busy") or clock.get("idle", 0) >= clock["busy"]


def run(args):
    os.umask(0o077)
    route_preflight()
    directory = Path(args.directory).resolve()
    items, pins = load_inputs(directory, "Kimi")
    ledger = Ledger(directory, "Kimi", items, pins)
    deadline = time.time() + min(args.max_wall_seconds, 14400)
    original_sha = sha(PRIVATE_CONFIG)
    with process_lock(directory):
        server = make_server(directory, ledger, deadline=deadline)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        # This is the only configuration credential read. It is never printed.
        config = read(PRIVATE_CONFIG)
        config["providers"]["azure-kimi"]["settings"]["baseURL"] = (
            "http://127\0560\0560\0561:%d/stage5/openai/v1" % server.server_port)
        save(directory / "opencode.json", config)
        config = None
        save(directory / "GATEWAY_PUBLIC.json", dict(port=server.server_port, bind="127\0560\0560\0561",
            pid=os.getpid(), model=MODEL, original_config_unchanged=True,
            physical_attempt_cap=180, maximum_selected=150, reservation_cap_usd=40))
        stop, all_idle = False, True
        try:
            for item in items:
                if stop or time.time() >= deadline:
                    break
                case = str(item["case"])
                dest = directory / "results" / case
                dest.mkdir(parents=True, exist_ok=True)
                path = dest / "EXECUTION_PRIVATE.json"
                state = read(path) if path.exists() else {"case": case,
                    "roster_sha256": pins["roster_sha256"], "record_id": item["row"]["record_id"],
                    "context_sha256": item["row"]["context_sha256"]}
                if any(state.get(key) != value for key, value in (
                        ("roster_sha256", pins["roster_sha256"]),
                        ("record_id", item["row"]["record_id"]),
                        ("context_sha256", item["row"]["context_sha256"]))):
                    raise BoundaryError("existing_session_not_bound_to_frame")
                if blocked(item):
                    state.update(status="blocked_protected_metadata_only", finished=True)
                    save(path, state)
                    continue
                if state.get("finished"):
                    continue
                save(directory / "ACTIVE_CASE_PRIVATE.json", {"case": case})
                try:
                    if "session_id" not in state:
                        digest = hashlib.sha256(("confirmation_stage5_20261118/" + pins["sha256"]["INPUTS_PRIVATE.jsonl"] + "/" + case).encode()).hexdigest()[:24]
                        state.update(session_id="ses_linkupstage5_" + digest, prompt_id="msg_linkupstage5_" + digest)
                        save(path, state)
                        session = api(directory, "POST", "/api/session", dict(id=state["session_id"],
                            title="LinkUp bounded Stage 5 Kimi " + case, agent="linkup-batch", model=MODEL,
                            location={"directory": str(directory)}, permissions=PERMISSIONS,
                            metadata={"scope": "bounded_stage5_independent_reference", "semantic_quality_certified": False}))["data"]
                    else:
                        session = api(directory, "GET", "/api/session/" + state["session_id"])["data"]
                    sid = state["session_id"]
                    if (session["model"].get("providerID") != MODEL["providerID"]
                            or session["model"].get("id") != MODEL["id"]
                            or session.get("parentID") or session.get("fork") or session["permissions"] != PERMISSIONS):
                        raise BoundaryError("session_isolation_or_model_mismatch")
                    if not state.get("submitted"):
                        if ledger.latest(case):
                            raise BoundaryError("prior_gateway_attempt_no_resubmission")
                        messages = api(directory, "GET", "/api/session/" + sid + "/message")["data"]
                        if any(m.get("type") in ("user", "assistant") for m in messages):
                            raise BoundaryError("existing_messages_no_resubmission")
                        state["submitted"] = True
                        save(path, state)  # Persist before POST; an ambiguous POST is never repeated.
                        try:
                            api(directory, "POST", "/api/session/" + sid + "/prompt",
                                {"id": state["prompt_id"], "text": kimi_prompt(directory, item)})
                        except Exception:
                            state["submission_uncertain"] = True
                            save(path, state)
                    case_deadline = min(deadline, time.time() + 1000)
                    while time.time() < case_deadline:
                        info = api(directory, "GET", "/api/session/" + sid)["data"]
                        messages = api(directory, "GET", "/api/session/" + sid + "/message")["data"]
                        assistants = [m for m in messages if m.get("type") == "assistant"]
                        if assistants and all(m.get("time", {}).get("completed") for m in assistants) and idle(info):
                            break
                        latest = ledger.latest(case)
                        if latest and latest["state"] in ("transport_uncertain_no_retry", "usage_reservation_breach_stop"):
                            raise BoundaryError("gateway_uncertain_hold")
                        time.sleep(5)
                    else:
                        raise BoundaryError("session_timeout_preserved")
                    if len(assistants) != 1:
                        raise BoundaryError("unexpected_assistant_count")
                    latest = ledger.latest(case)
                    for _ in range(25):
                        if latest is None or latest["state"] != "forwarding_uncertain":
                            break
                        time.sleep(.2)
                        latest = ledger.latest(case)
                    if latest is None or latest["state"] == "forwarding_uncertain":
                        raise BoundaryError("gateway_completion_not_confirmed")
                    state.update(status=latest["state"], finished=True)
                    if parse_json(latest["detail"]).get("http_status") in (401, 403, 404):
                        stop = True
                    if latest["state"] in ("transport_uncertain_no_retry", "usage_reservation_breach_stop"):
                        stop = True
                except Exception as exc:
                    state.update(status=str(exc) if isinstance(exc, BoundaryError) else "control_failure_preserved",
                                 error_type=type(exc).__name__)
                    stop = True
                    if state.get("submitted"):
                        try:
                            sid = state["session_id"]
                            if not idle(api(directory, "GET", "/api/session/" + sid)["data"]):
                                api(directory, "POST", "/api/session/" + sid + "/interrupt")
                            all_idle = idle(api(directory, "GET", "/api/session/" + sid)["data"])
                        except Exception:
                            all_idle = False
                    state["finished"] = all_idle
                save(path, state)
                save(directory / "RUN_STATUS_PUBLIC.json", ledger.summary())
        finally:
            server.shutdown()
            server.server_close()  # Wait for admitted provider handler before terminal receipt.
            thread.join(timeout=5)
            if sha(PRIVATE_CONFIG) != original_sha:
                raise BoundaryError("original_configuration_changed")
        outputs = []
        for item in items:
            dest = directory / "results" / str(item["case"])
            state = read(dest / "EXECUTION_PRIVATE.json") if (dest / "EXECUTION_PRIVATE.json").exists() else {}
            latest = ledger.latest(item["case"])
            textpath = dest / "VISIBLE_RESPONSE_PRIVATE.txt"
            outputs.append(dict(case=str(item["case"]), record_id=item["row"]["record_id"],
                context_sha256=item["row"]["context_sha256"], leg="Kimi", payload=None,
                roster_sha256=pins["roster_sha256"], field_validation=None,
                status="blocked_protected_metadata_only" if blocked(item) else state.get("status", "unprocessed_bounded_stop"),
                response_text=textpath.read_text() if textpath.exists() and not blocked(item) else None,
                transport=parse_json(latest["detail"]) if latest else None))
        output_roster = verify_output_frame(items, outputs, pins["roster_sha256"])
        immutable(directory / "OUTPUTS_PRIVATE.jsonl", b"".join(encoded(x) + b"\n" for x in outputs))
        exclusions = read(directory / "EXCLUSIONS_PRIVATE.json")
        with ledger.db() as db:
            exclusions["context_sha256"] = sorted(set(exclusions.get("context_sha256", [])) | {x[0] for x in db.execute("SELECT context FROM quarantine")})
        save(directory / "EXCLUSIONS_EXPORT_PRIVATE.json", exclusions)
        final = ledger.summary(terminal=all_idle)
        final.update(outputs_accounted=len(outputs), output_sha256=sha(directory / "OUTPUTS_PRIVATE.jsonl"),
                     output_roster_sha256=output_roster,
                     exclusions_sha256=sha(directory / "EXCLUSIONS_EXPORT_PRIVATE.json"),
                     original_configuration_unchanged=True, semantic_validation_location="Azure_after_transport")
        save(directory / "KIMI_FINAL_PUBLIC.json", final)
        print(json.dumps(final), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--max-wall-seconds", type=int, default=14400)
    args = parser.parse_args()
    try:
        if args.preflight_only:
            print(json.dumps(route_preflight()), flush=True)
        elif args.directory:
            run(args)
        else:
            raise BoundaryError("leg_directory_required")
    except Exception as exc:
        print(json.dumps({"fatal_error_type": type(exc).__name__, "raw_exception_not_logged": True}), flush=True)
        raise SystemExit(2)

"""Loopback-only existing OpenCode Kimi route with durable physical-call admission.

The gateway accepts only the active frozen case's exact full-source prompt. It
passes the existing credential in memory and never logs it or saves reasoning.
"""
from __future__ import annotations
import http.server
import json
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from stage5_common import (BoundaryError, MODELS, NOTICE, RETRY_HTTP, encoded, immutable,
    kimi_prompt, parse_json, read)


TRANSPORT_REVISION = "stage5-kimi-transport-v2"


def scientific_request(payload, expected_user):
    """Project an isolated transport envelope onto the unchanged frozen contract.

    Non-user envelope entries are never used as scientific inputs or forwarded.
    This is deliberately NOT a claim that arbitrary history is trusted/empty:
    session isolation is separately enforced by the worker. Only one exact user
    string supplies input; every outbound field is reconstructed below.
    """
    if not isinstance(payload, dict) or payload.get("model") != MODELS["Kimi"]["deployment"]:
        raise BoundaryError("model_not_pinned_kimi")
    if payload.get("tools") or payload.get("functions"):
        raise BoundaryError("tools_forbidden")
    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise BoundaryError("transport_messages_not_list")
    texts = []
    for message in messages:
        if not isinstance(message, dict) or not isinstance(message.get("role"), str):
            raise BoundaryError("transport_message_shape_rejected")
        if message["role"] != "user":
            continue
        content = message.get("content")
        if isinstance(content, list):
            if any(not isinstance(p, dict) or p.get("type") != "text"
                   or not isinstance(p.get("text"), str) for p in content):
                raise BoundaryError("non_text_content_forbidden")
            content = "".join(p["text"] for p in content)
        texts.append(content)
    if len(texts) != 1 or not isinstance(texts[0], str) or texts[0] != expected_user:
        raise BoundaryError("frozen_full_source_prompt_mismatch")
    stream = bool(payload.get("stream"))
    result = {"model": MODELS["Kimi"]["deployment"],
              "messages": [{"role": "system", "content": NOTICE},
                           {"role": "user", "content": texts[0]}],
              "max_tokens": MODELS["Kimi"]["output"], "stream": stream}
    if stream:
        result["stream_options"] = {"include_usage": True}
    return result


class GatewayActivity:
    """Tracks all handlers, including those still waiting for ledger admission."""
    def __init__(self):
        self.condition = threading.Condition()
        self.closing = False
        self.handlers = 0

    def enter(self):
        with self.condition:
            if self.closing:
                return False
            self.handlers += 1
            return True

    def leave(self):
        with self.condition:
            self.handlers -= 1
            self.condition.notify_all()

    def stop(self):
        with self.condition:
            self.closing = True

    def wait(self, timeout):
        with self.condition:
            return self.condition.wait_for(lambda: self.handlers == 0, timeout=max(0, timeout))


def shutdown_server(server, serve_thread, *, timeout=310):
    """Bound shutdown without asserting terminal success for active requests.

    Daemon handlers cannot prevent process exit after this deadline. An admitted
    unfinished handler retains its durable forwarding_uncertain ledger entry;
    the worker emits terminal=false and all later-leg admission remains blocked.
    No provider request is retried or declared complete by this helper.
    """
    end = time.monotonic() + max(0, timeout)
    server.stage5_activity.stop()
    shutdown = threading.Thread(target=server.shutdown, daemon=True)
    shutdown.start()
    shutdown.join(timeout=max(0, end - time.monotonic()))
    server.server_close()  # daemon_threads=True and block_on_close=False
    serve_thread.join(timeout=max(0, end - time.monotonic()))
    handlers_idle = server.stage5_activity.wait(max(0, end - time.monotonic()))
    stopped = not shutdown.is_alive() and not serve_thread.is_alive()
    return {"quiescent": handlers_idle and stopped, "handlers_idle": handlers_idle,
            "serve_loop_stopped": stopped, "wait_bound_seconds": timeout,
            "active_admissions_never_marked_complete": True}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def make_server(directory, ledger, *, deadline):
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))

    activity = GatewayActivity()

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def handle(self):
            if not activity.enter():
                self.close_connection = True
                return
            try:
                super().handle()
            finally:
                activity.leave()

        def end_headers(self):
            self.send_header("Connection", "close")
            self.close_connection = True
            super().end_headers()

        def log_message(self, *args):
            pass

        def reject(self, status, code):
            self.close_connection = True
            body = encoded({"error": {"type": "stage5_boundary", "code": code, "message": code}})
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.close_connection = True
            attempt_id = None
            headers_sent = False
            try:
                if self.path != "/stage5/openai/v1/chat/completions":
                    return self.reject(400, "unapproved_endpoint")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2000000:
                    return self.reject(400, "request_length_rejected")
                payload = parse_json(self.rfile.read(size))
                active = read(directory / "ACTIVE_CASE_PRIVATE.json")
                case = str(active["case"])
                if case not in ledger.items:
                    return self.reject(400, "frozen_full_source_prompt_mismatch")
                try:
                    payload = scientific_request(payload, kimi_prompt(directory, ledger.items[case]))
                except BoundaryError as exc:
                    return self.reject(400, str(exc))
                auth = self.headers.get("Authorization")
                if not auth or not auth.startswith("Bearer "):
                    return self.reject(401, "existing_route_credential_missing")
                # Only reconstructed frozen scientific content reaches admission.
                if activity.closing:
                    return self.reject(409, "gateway_shutdown_hold")
                body = encoded(payload)
                attempt_id = ledger.reserve(case, body, deadline=deadline)
                if activity.closing:
                    ledger.finish(attempt_id, "transport_uncertain_no_retry",
                                  {"shutdown_before_forward": True, "provider_forwarded": False})
                    attempt_id = None
                    return self.reject(409, "gateway_shutdown_hold")
                request = urllib.request.Request("https://rg-linkup.openai.azure.com/openai/v1/chat/completions",
                    data=body, headers={"Authorization": auth, "Content-Type": "application/json",
                                       "Accept": self.headers.get("Accept", "*/*")}, method="POST")
                auth = None
                try:
                    response = opener.open(request, timeout=min(300, max(1, deadline - time.time())))
                except urllib.error.HTTPError as exc:
                    response = exc
                with response:
                    status = response.status
                    headers = {k.lower(): v for k, v in response.headers.items()
                        if k.lower() in ("x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens",
                           "x-ratelimit-limit-requests", "retry-after-ms", "retry-after", "x-request-id", "apim-request-id")}
                    detail = {"http_status": status, "rate_headers": headers}
                    self.send_response(status)
                    self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                    for k, v in headers.items():
                        self.send_header(k, v)
                    self.end_headers()
                    self.close_connection = True
                    headers_sent = True
                    if status != 200:
                        raw = response.read(1_000_001)
                        filtered = b"content_filter" in raw or b"ResponsibleAIPolicyViolation" in raw
                        state = ("quarantined_provider_filter" if filtered else
                                 "retryable_confirmed_http" if status in RETRY_HTTP and len(raw) <= 1_000_000 else "http_error_terminal")
                        ledger.finish(attempt_id, state, detail, quarantined=filtered)
                        attempt_id = None
                        self.wfile.write(raw)
                        self.wfile.flush()
                        return
                    parts, finish, usage = [], [], None
                    done = refused = False
                    count = 0
                    if payload.get("stream"):
                        for line in response:
                            count += len(line)
                            if count > 4_000_000:
                                raise BoundaryError("response_size_bound")
                            self.wfile.write(line)
                            self.wfile.flush()
                            if not line.startswith(b"data:"):
                                continue
                            raw = line[5:].strip()
                            if raw == b"[DONE]":
                                done = True
                                continue
                            obj = parse_json(raw)
                            if obj.get("usage"):
                                usage = obj["usage"]
                            for choice in obj.get("choices", []):
                                delta = choice.get("delta", {})
                                if isinstance(delta.get("content"), str):
                                    parts.append(delta["content"])
                                refused = refused or bool(delta.get("refusal"))
                                if choice.get("finish_reason") is not None:
                                    finish.append(choice["finish_reason"])
                    else:
                        raw = response.read(4_000_001)
                        if len(raw) > 4_000_000:
                            raise BoundaryError("response_size_bound")
                        self.wfile.write(raw)
                        self.wfile.flush()
                        obj = parse_json(raw)
                        usage = obj.get("usage")
                        done = True
                        for choice in obj.get("choices", []):
                            message = choice.get("message", {})
                            parts.append(message.get("content") or "")
                            refused = refused or bool(message.get("refusal"))
                            finish.append(choice.get("finish_reason"))
                    filtered = "content_filter" in finish or refused
                    complete = done and finish == ["stop"] and not filtered
                    detail.update(usage={k: (usage or {}).get(k, 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
                                  usage_reported=usage is not None, finish_reasons=finish,
                                  complete=complete, filtered=filtered, response_bytes=count)
                    immutable(directory / "results" / case / "VISIBLE_RESPONSE_PRIVATE.txt", "".join(parts).encode())
                    state = ("quarantined_provider_filter_or_refusal" if filtered else
                             "response_saved" if complete else "incomplete_output_preserved")
                    ledger.finish(attempt_id, state, detail, quarantined=filtered)
                    attempt_id = None
            except Exception as exc:
                if attempt_id is not None:
                    ledger.finish(attempt_id, "transport_uncertain_no_retry", {"error_type": type(exc).__name__})
                if not headers_sent:
                    try:
                        self.reject(409, str(exc) if isinstance(exc, BoundaryError) else "transport_boundary_hold")
                    except Exception:
                        pass

    server = http.server.ThreadingHTTPServer(("127\0560\0560\0561", 0), Handler)
    server.daemon_threads = True
    server.block_on_close = False
    server.stage5_activity = activity
    return server

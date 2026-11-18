"""Offline synthetic transport regressions: no sockets, CLI, credentials or model calls."""
import hashlib
import io
import threading
import time
import unittest
from unittest.mock import patch

import stage5_common as c
import stage5_kimi_gateway as g
import stage5_kimi_worker as w
import test_stage5_runtime as rt


class TransportTests(unittest.TestCase):
    setUp = rt.RuntimeTests.setUp
    tearDown = rt.RuntimeTests.tearDown
    frame = rt.RuntimeTests.frame

    def payload(self, user="FROZEN_SYNTHETIC_USER", **changes):
        value = {"model": c.MODELS["Kimi"]["deployment"],
                 "messages": [{"role": "user", "content": user}], "stream": False}
        value.update(changes)
        return value

    def harness(self, opener=None):
        items, pins, ledger = self.frame("Kimi")
        c.save(self.d / "ACTIVE_CASE_PRIVATE.json", {"case": "case000"})
        class Server:
            def __init__(self, address, handler): self.handler = handler
        class NoNetwork:
            def open(self, *a, **kw): raise AssertionError("unexpected_provider_attempt")
        with patch.object(g.http.server, "ThreadingHTTPServer", Server), patch.object(
                g.urllib.request, "build_opener", return_value=opener or NoNetwork()):
            server = g.make_server(self.d, ledger, deadline=self.clock.now + 100)
        def request(payload, path="/stage5/openai/v1/chat/completions", auth=True):
            body = c.encoded(payload)
            h = object.__new__(server.handler)
            h.path, h.command, h.request_version, h.requestline = path, "POST", "HTTP/1.1", "POST synthetic HTTP/1.1"
            h.headers = {"Content-Length": str(len(body))}
            if auth: h.headers["Authorization"] = "Bearer SYNTHETIC_NOT_A_CREDENTIAL"
            h.rfile, h.wfile = io.BytesIO(body), io.BytesIO()
            h.do_POST()
            return h, h.wfile.getvalue()
        return items, pins, ledger, server, request

    def test_same_pinned_scientific_contract_both_stream_modes(self):
        for stream in (False, True):
            out = g.scientific_request(self.payload(stream=stream), "FROZEN_SYNTHETIC_USER")
            expected = {"model": "linkup-kimi-k3-1-pro", "messages": [
                {"role": "system", "content": c.NOTICE},
                {"role": "user", "content": "FROZEN_SYNTHETIC_USER"}],
                "max_tokens": 16000, "stream": stream}
            if stream: expected["stream_options"] = {"include_usage": True}
            self.assertEqual(c.encoded(out), c.encoded(expected))

    def test_nonuser_envelope_content_never_enters_scientific_request(self):
        base = self.payload()
        expected = c.encoded(g.scientific_request(base, "FROZEN_SYNTHETIC_USER"))
        for role in ("system", "developer", "assistant", "tool", "transport-role-not-classified"):
            with self.subTest(role=role):
                changed = self.payload(messages=[{"role": role, "content": "UNKNOWN_HISTORY_IS_NOT_TRUSTED",
                    "tool_calls": [{"untrusted": "SIDE_CONTEXT"}]}, *base["messages"]],
                    metadata={"source": "SIDE_CONTEXT"}, max_tokens=1, temperature=100,
                    logit_bias={"SIDE_CONTEXT": 100}, tool_choice="SIDE_CONTEXT")
                projected = c.encoded(g.scientific_request(changed, "FROZEN_SYNTHETIC_USER"))
                self.assertEqual(projected, expected)
                self.assertNotIn(b"SIDE_CONTEXT", projected)
                self.assertNotIn(b"UNKNOWN_HISTORY", projected)

    def test_exactly_one_frozen_user_required(self):
        user = self.payload()["messages"][0]
        for messages in ([], [user, user], [{"role": "user", "content": "changed"}],
                         [{"role": "assistant", "content": "FROZEN_SYNTHETIC_USER"}],
                         [{"role": "user", "content": None}]):
            with self.subTest(messages=messages), self.assertRaises(c.BoundaryError):
                g.scientific_request(self.payload(messages=messages), "FROZEN_SYNTHETIC_USER")

    def test_text_part_binding_and_nontext_rejection(self):
        parts = [{"type": "text", "text": "FROZEN_"}, {"type": "text", "text": "SYNTHETIC_USER"}]
        out = g.scientific_request(self.payload(user=parts), "FROZEN_SYNTHETIC_USER")
        self.assertEqual(out["messages"][1]["content"], "FROZEN_SYNTHETIC_USER")
        for bad in (parts + [{"type": "image_url", "image_url": "not-read"}],
                    [{"type": "text", "text": 4}], ["FROZEN_SYNTHETIC_USER"]):
            with self.assertRaisesRegex(c.BoundaryError, "non_text_content_forbidden"):
                g.scientific_request(self.payload(user=bad), "FROZEN_SYNTHETIC_USER")

    def test_tools_functions_model_and_malformed_envelope_still_rejected(self):
        for changes in ({"tools": [{}]}, {"functions": [{}]}, {"model": "unapproved"},
                        {"messages": {}}, {"messages": [None]}, {"messages": [{"role": None}]}):
            with self.assertRaises(c.BoundaryError):
                g.scientific_request(self.payload(**changes), "FROZEN_SYNTHETIC_USER")

    def test_session_namespace_is_deterministic_and_distinct_from_original(self):
        input_sha, case = "a" * 64, "case0000"
        original = hashlib.sha256(("confirmation_stage5_20261118/" + input_sha + "/" + case).encode()).hexdigest()[:24]
        ids = w.session_identifiers(input_sha, case)
        self.assertEqual(ids, w.session_identifiers(input_sha, case))
        self.assertNotEqual(ids["session_id"], "ses_linkupstage5_" + original)
        self.assertIn("v2", ids["session_id"])
        self.assertEqual(c.VERSION, "stage5-bounded-serial-v1")

    def test_rejections_close_connections_and_remain_zero_admission(self):
        items, pins, ledger, server, request = self.harness()
        user = c.kimi_prompt(self.d, items[0])
        for payload, path, auth in ((self.payload(user=user), "/wrong", True),
                (self.payload(user="changed"), "/stage5/openai/v1/chat/completions", True),
                (self.payload(user=user, tools=[{}]), "/stage5/openai/v1/chat/completions", True),
                (self.payload(user=user), "/stage5/openai/v1/chat/completions", False)):
            h, response = request(payload, path, auth)
            self.assertTrue(h.close_connection)
            self.assertIn(b"Connection: close\r\n", response)
        self.assertEqual(ledger.summary()["physical_attempts"], 0)
        self.assertTrue(server.daemon_threads)
        self.assertFalse(server.block_on_close)

    def test_success_closes_and_outbound_is_frozen_reconstruction(self):
        sent = []
        class Response:
            status = 200
            headers = {"Content-Type": "application/json"}
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, n):
                return c.encoded({"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}})
        class Opener:
            def open(self, request, timeout): sent.append(c.parse_json(request.data)); return Response()
        items, pins, ledger, server, request = self.harness(Opener())
        user = c.kimi_prompt(self.d, items[0])
        body = self.payload(user=user)
        body["messages"].append({"role": "assistant", "content": "UNKNOWN_NOT_SCIENTIFIC"})
        h, response = request(body)
        self.assertEqual(sent, [g.scientific_request(self.payload(user=user), user)])
        self.assertEqual(ledger.latest("case000")["state"], "response_saved")
        self.assertTrue(h.close_connection)
        self.assertIn(b"Connection: close\r\n", response)

    def test_shutdown_gate_prevents_new_admission(self):
        items, pins, ledger, server, request = self.harness()
        server.stage5_activity.stop()
        self.assertFalse(server.stage5_activity.enter())
        h, response = request(self.payload(user=c.kimi_prompt(self.d, items[0])))
        self.assertIn(b"gateway_shutdown_hold", response)
        self.assertEqual(ledger.summary()["physical_attempts"], 0)

    def test_shutdown_quiescent_is_bounded(self):
        activity = g.GatewayActivity()
        class Server:
            stage5_activity = activity
            def shutdown(self): pass
            def server_close(self): pass
        serving = threading.Thread(target=lambda: None)
        serving.start(); serving.join()
        result = g.shutdown_server(Server(), serving, timeout=.15)
        self.assertTrue(result["quiescent"])
        self.assertFalse(activity.enter())

    def test_pending_handler_keeps_terminal_false_and_ledger_hold(self):
        items, pins, ledger = self.frame("Kimi")
        ledger.reserve("case000", b"{}", deadline=self.clock.now + 100)
        activity = g.GatewayActivity()
        self.assertTrue(activity.enter())
        class Server:
            stage5_activity = activity
            def shutdown(self): pass
            def server_close(self): pass
        serving = threading.Thread(target=lambda: None)
        serving.start(); serving.join()
        start = time.monotonic()
        result = g.shutdown_server(Server(), serving, timeout=.05)
        self.assertLess(time.monotonic() - start, .5)
        self.assertFalse(result["quiescent"])
        self.assertFalse(ledger.summary(terminal=result["quiescent"])["terminal_no_active_requests"])
        self.assertEqual(ledger.latest("case000")["state"], "forwarding_uncertain")
        activity.leave()

    def test_shutdown_after_reserve_never_forwards_and_is_held(self):
        items, pins, ledger, server, request = self.harness()
        reserve = ledger.reserve
        def reserve_then_stop(*a, **kw):
            attempt = reserve(*a, **kw)
            server.stage5_activity.stop()
            return attempt
        with patch.object(ledger, "reserve", reserve_then_stop):
            h, response = request(self.payload(user=c.kimi_prompt(self.d, items[0])))
        self.assertIn(b"gateway_shutdown_hold", response)
        self.assertEqual(ledger.latest("case000")["state"], "transport_uncertain_no_retry")
        self.assertFalse(ledger.summary(terminal=True)["terminal_no_active_requests"])


if __name__ == "__main__":
    unittest.main()

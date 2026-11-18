"""Synthetic admission/transport tests. No credential reads or network requests."""
import concurrent.futures
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import stage5_common as c
import stage5_cloud_worker as cloud
import stage5_kimi_gateway as gateway
import stage5_kimi_worker as kimi
import stage5_prepare as prepare


class Clock:
    def __init__(self):
        self.now = 1000000000.0

    def time(self):
        return self.now

    def sleep(self, duration):
        self.now += duration


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.clock = Clock()
        self.patches = [patch.object(c.time, "time", self.clock.time), patch.object(c.time, "sleep", self.clock.sleep)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def frame(self, leg="Luna", count=2, predecessor_last=None):
        items = []
        for index in range(count):
            text = "Synthetic full document %s.\n完整上下文。" % index
            items.append(dict(case="case%03d" % index, row=dict(record_id="record%s" % index,
                context_sha256=hashlib.sha256(text.encode()).hexdigest(), full_document=text)))
        (self.d / "INPUTS_PRIVATE.jsonl").write_bytes(b"".join(c.encoded(x) + b"\n" for x in items))
        (self.d / "SCHEMA.json").write_text("{}")
        (self.d / "INSTRUCTIONS.md").write_text("Frozen fixture instructions.")
        c.save(self.d / "EXCLUSIONS_PRIVATE.json", dict(tasks=[], context_sha256=[]))
        (self.d / "FRAME_ROSTER_PRIVATE.json").write_bytes(c.encoded(c.canonical_roster(items)))
        if c.PREDECESSOR[leg]:
            c.save(self.d / "PREDECESSOR_EXCLUSIONS_PRIVATE.json", dict(tasks=[], context_sha256=[]))
            c.save(self.d / (c.PREDECESSOR[leg].upper() + "_FINAL_PUBLIC.json"),
                dict(runtime_version=c.VERSION, leg=c.PREDECESSOR[leg], reserved_nano=0,
                     roster_sha256=c.roster_sha256(items), output_roster_sha256=c.roster_sha256(items),
                     output_sha256="a" * 64, outputs_accounted=len(items),
                     exclusions_sha256=c.sha(self.d / "PREDECESSOR_EXCLUSIONS_PRIVATE.json"),
                     terminal_no_active_requests=True,
                     last_forward_epoch=self.clock.now - 100 if predecessor_last is None else predecessor_last))
        pins = {"sha256": {p.name: c.sha(p) for p in self.d.iterdir()},
                "roster_sha256": c.roster_sha256(items),
                "code_sha256": {name: c.sha(Path(c.__file__).parent / name) for name in c.RUNTIME_FILES}}
        c.save(self.d / "INPUT_PINS_PUBLIC.json", pins)
        items, pins = c.load_inputs(self.d, leg)
        return items, pins, c.Ledger(self.d, leg, items, pins)

    def repin(self, *names):
        pins = c.read(self.d / "INPUT_PINS_PUBLIC.json")
        for name in names:
            pins["sha256"][name] = c.sha(self.d / name)
        c.save(self.d / "INPUT_PINS_PUBLIC.json", pins)
        return pins

    def write_items(self, items):
        (self.d / "INPUTS_PRIVATE.jsonl").write_bytes(b"".join(c.encoded(x) + b"\n" for x in items))
        self.repin("INPUTS_PRIVATE.jsonl")

    def predecessor_quarantine(self, items):
        prior = {"context_sha256": [items[0]["row"]["context_sha256"]]}
        c.save(self.d / "PREDECESSOR_EXCLUSIONS_PRIVATE.json", prior)
        receipt = c.read(self.d / "LUNA_FINAL_PUBLIC.json")
        receipt["exclusions_sha256"] = c.sha(self.d / "PREDECESSOR_EXCLUSIONS_PRIVATE.json")
        c.save(self.d / "LUNA_FINAL_PUBLIC.json", receipt)
        self.repin("PREDECESSOR_EXCLUSIONS_PRIVATE.json", "LUNA_FINAL_PUBLIC.json")
        return prior

    def legacy_route_fixture(self):
        cli = self.d / "fixture_cli"
        cli.write_text("not executed")
        cli.chmod(0o700)
        source = self.d / "known_gateway.py"
        source.write_text("# synthetic known gateway; never executed\n")
        config = self.d / "opencode.json"
        c.save(config, {"providers": {"azure-kimi": {"settings": {
            "baseURL": kimi.LEGACY_ROUTE["url"], "apiKey": "SYNTHETIC_SECRET_NEVER_PRINT"}}}})
        c.save(self.d / "GATEWAY_PUBLIC.json", {"bind": "127\0560\0560\0561", "port": 60735, "pid": 7})
        c.save(self.d / "ACTIVE_LAUNCH_PUBLIC.json", {"gateway_pid": 7,
            "gateway_file": str(source), "gateway_sha256": c.sha(source)})
        pins = {"url": kimi.LEGACY_ROUTE["url"], "configuration_sha256": c.sha(config),
            "gateway_public_sha256": c.sha(self.d / "GATEWAY_PUBLIC.json"),
            "launch_public_sha256": c.sha(self.d / "ACTIVE_LAUNCH_PUBLIC.json"),
            "gateway_source_sha256": c.sha(source), "gateway_source": source}
        return cli, config, pins

    def test_fixed_dollars_and_distinct_model_capabilities(self):
        self.assertEqual(sum(x["cap_nano"] for x in c.MODELS.values()), 50_000_000_000)
        self.assertLessEqual(c.HISTORICAL_RESERVATION_NANO + c.NEW_CAP_NANO, c.STAGE_CAP_NANO)
        self.assertEqual(c.MODELS["Luna"]["api"], "chat/completions")
        self.assertEqual(c.MODELS["Astra"]["api"], "responses")
        self.assertEqual([c.MODELS[x]["physical"] for x in c.MODELS], [180, 180, 6])

    def test_kimi_cannot_change_shared_roster(self):
        items, pins, ledger = self.frame("Kimi")
        items[0]["row"]["record_id"] = "replacement_record"
        self.write_items(items)
        with self.assertRaisesRegex(c.BoundaryError, "leg_not_bound_to_shared_frozen_roster"):
            c.load_inputs(self.d, "Kimi")

    def test_astra_can_only_take_shared_roster_subset(self):
        items, pins, ledger = self.frame("Astra", 3)
        self.write_items(items[:1])
        selected, _ = c.load_inputs(self.d, "Astra")
        self.assertEqual(len(selected), 1)
        selected[0]["row"]["record_id"] = "outside_roster"
        self.write_items(selected)
        with self.assertRaisesRegex(c.BoundaryError, "leg_not_bound_to_shared_frozen_roster"):
            c.load_inputs(self.d, "Astra")

    def test_predecessor_sha_checked_before_body_parsing(self):
        items, pins, ledger = self.frame("Kimi")
        (self.d / "INPUTS_PRIVATE.jsonl").write_text("not parsed: invalid json")
        self.repin("INPUTS_PRIVATE.jsonl")
        receipt = c.read(self.d / "LUNA_FINAL_PUBLIC.json")
        receipt["roster_sha256"] = "f" * 64
        c.save(self.d / "LUNA_FINAL_PUBLIC.json", receipt)
        original_sha = c.sha
        def guarded_sha(path):
            if Path(path).name == "INPUTS_PRIVATE.jsonl":
                raise AssertionError("source_body_opened_before_predecessor_check")
            return original_sha(path)
        with patch.object(c, "sha", guarded_sha):
            with self.assertRaisesRegex(c.BoundaryError, "predecessor_file_pin_mismatch"):
                c.load_inputs(self.d, "Kimi")
        self.repin("LUNA_FINAL_PUBLIC.json")
        with patch.object(c, "sha", guarded_sha):
            with self.assertRaisesRegex(c.BoundaryError, "serial_predecessor_frame_or_receipt_invalid"):
                c.load_inputs(self.d, "Kimi")

    def test_predecessor_quarantine_required_and_metadata_only(self):
        items, pins, ledger = self.frame("Kimi")
        prior = self.predecessor_quarantine(items)
        with self.assertRaisesRegex(c.BoundaryError, "predecessor_quarantine_not_preserved"):
            c.load_inputs(self.d, "Kimi")
        c.save(self.d / "EXCLUSIONS_PRIVATE.json", prior)
        self.repin("EXCLUSIONS_PRIVATE.json")
        with self.assertRaisesRegex(c.BoundaryError, "protected_source_body_present_in_frozen_leg"):
            c.load_inputs(self.d, "Kimi")
        items[0] = c.metadata_only_block(items[0])
        self.write_items(items)
        frozen, pins = c.load_inputs(self.d, "Kimi")
        self.assertEqual(len(frozen), 2)
        self.assertNotIn("full_document", frozen[0]["row"])
        with self.assertRaisesRegex(c.BoundaryError, "blocked_protected_metadata_only"):
            c.kimi_prompt(self.d, frozen[0])

    def test_outputs_cannot_claim_another_frame_or_replace_slot(self):
        items, pins, ledger = self.frame()
        rows = [dict(case=x["case"], **{k: x["row"][k] for k in ("record_id", "context_sha256")},
                     roster_sha256=pins["roster_sha256"], payload=None, field_validation=None,
                     status="unprocessed_bounded_stop") for x in items]
        self.assertEqual(c.verify_output_frame(items, rows, pins["roster_sha256"]), pins["roster_sha256"])
        rows[0]["roster_sha256"] = "a" * 64
        with self.assertRaisesRegex(c.BoundaryError, "output_not_bound_to_frozen_frame"):
            c.verify_output_frame(items, rows, pins["roster_sha256"])

    def test_prepare_merges_quarantine_and_keeps_denominator_slots(self):
        items, pins, ledger = self.frame("Kimi")
        self.predecessor_quarantine(items)
        adapter = self.d / "adapter.py"
        frozen = self.d / "frozen.py"
        adapter.write_text("# synthetic hash-only adapter\n")
        frozen.write_text("def validate_packet(rows):\n    assert len(rows) == 1\n    assert all('full_document' in row for row in rows)\n")
        output = self.d / "prepared"
        argv = ["prepare", "--leg", "Kimi", "--directory", str(output),
            "--inputs", str(self.d / "INPUTS_PRIVATE.jsonl"), "--roster", str(self.d / "FRAME_ROSTER_PRIVATE.json"),
            "--schema", str(self.d / "SCHEMA.json"), "--instructions", str(self.d / "INSTRUCTIONS.md"),
            "--exclusions", str(self.d / "EXCLUSIONS_PRIVATE.json"), "--field-validator", str(adapter),
            "--frozen-validator", str(frozen), "--predecessor-receipt", str(self.d / "LUNA_FINAL_PUBLIC.json"),
            "--predecessor-exclusions", str(self.d / "PREDECESSOR_EXCLUSIONS_PRIVATE.json")]
        with patch("sys.argv", argv), patch("sys.stdout", io.StringIO()):
            prepare.main()
        selected, prepared_pins = c.load_inputs(output, "Kimi")
        self.assertEqual(len(selected), 2)
        self.assertTrue(c.blocked(selected[0]))
        self.assertEqual(set(selected[0]["row"]), {"record_id", "context_sha256"})
        self.assertEqual(prepared_pins["roster_sha256"], pins["roster_sha256"])

    def test_source_binding_protection_and_frozen_pin(self):
        items, pins, ledger = self.frame()
        payload = c.model_payload(self.d, "Luna", items[0])
        self.assertEqual(c.parse_json(payload["messages"][1]["content"]), items[0]["row"])
        p = dict(items[0], task="batch035/packet0001")
        self.assertTrue(c.protected(p, {}))
        p = dict(items[0], thread="01a17beb-973b-74e2-adbb-20f8d004b1fc")
        self.assertTrue(c.protected(p, {}))
        self.assertTrue(c.protected(items[0], {"context_sha256": [items[0]["row"]["context_sha256"]]}))
        (self.d / "INSTRUCTIONS.md").write_text("Changed")
        with self.assertRaises(c.BoundaryError):
            c.load_inputs(self.d, "Luna")

    def test_atomic_exclusive_claim_one_winner(self):
        items, pins, ledger = self.frame()
        barrier = threading.Barrier(2)
        def reserve():
            barrier.wait()
            try:
                return ledger.reserve("case000", b"{}", deadline=self.clock.now + 100)
            except c.BoundaryError:
                return None
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: reserve(), range(2)))
        self.assertEqual(sum(x is not None for x in results), 1)
        self.assertEqual(ledger.summary()["physical_attempts"], 1)

    def test_uncertain_restart_holds_all_new_calls(self):
        items, pins, ledger = self.frame()
        attempt = ledger.reserve("case000", b"{}", deadline=self.clock.now + 100)
        ledger.finish(attempt, "transport_uncertain_no_retry", {})
        reopened = c.Ledger(self.d, "Luna", items, pins)
        with self.assertRaises(c.BoundaryError):
            reopened.reserve("case001", b"{}", deadline=self.clock.now + 100)
        self.assertFalse(reopened.summary(terminal=True)["terminal_no_active_requests"])
        self.assertGreater(reopened.summary()["reserved_nano"], 0)

    def test_confirmed_retry_twice_then_stop_and_no_refund(self):
        items, pins, ledger = self.frame()
        for _ in range(2):
            a = ledger.reserve("case000", b"{}", deadline=self.clock.now + 100)
            ledger.finish(a, "retryable_confirmed_http", {"http_status": 429})
        with self.assertRaises(c.BoundaryError):
            ledger.reserve("case000", b"{}", deadline=self.clock.now + 100)
        self.assertEqual(ledger.summary()["physical_attempts"], 2)
        self.assertEqual(ledger.summary()["reserved_nano"], 2 * (1026 * 100 + 12000 * 500))

    def test_conservative_cost_and_physical_caps(self):
        items, pins, ledger = self.frame("Astra")
        a = ledger.reserve("case000", b"{}", deadline=self.clock.now + 100)
        ledger.finish(a, "response_saved", {})
        with ledger.db() as db:
            db.execute("UPDATE attempts SET dollars_nano=?", (c.MODELS["Astra"]["cap_nano"],))
        with self.assertRaisesRegex(c.BoundaryError, "persistent_attempt_or_dollar_cap"):
            ledger.reserve("case001", b"{}", deadline=self.clock.now + 100)

    def test_astra_sixth_physical_attempt_is_final_cap(self):
        items, pins, ledger = self.frame("Astra", 6)
        for index in range(6):
            a = ledger.reserve("case%03d" % index, b"{}", deadline=self.clock.now + 100)
            ledger.finish(a, "retryable_confirmed_http", {"http_status": 503})
        with self.assertRaisesRegex(c.BoundaryError, "persistent_attempt_or_dollar_cap"):
            ledger.reserve("case005", b"{}", deadline=self.clock.now + 100)
        self.assertEqual(ledger.summary()["physical_attempts"], 6)
        self.assertEqual(ledger.summary()["logical_calls"], 6)

    def test_rolling_window_and_serial_handoff_survive_restart(self):
        items, pins, ledger = self.frame("Kimi", predecessor_last=self.clock.now)
        reopened = c.Ledger(self.d, "Kimi", items, pins)
        before = self.clock.now
        a = reopened.reserve("case000", b"{}", deadline=before + 100)
        self.assertGreaterEqual(self.clock.now - before, 60.1)
        reopened.finish(a, "response_saved", {"rate_headers": {"x-ratelimit-limit-tokens": "20000"}})
        with self.assertRaisesRegex(c.BoundaryError, "request_exceeds_observed_quota"):
            reopened.reserve("case001", b"x" * 5000, deadline=self.clock.now + 100)

    def test_usage_breach_holds_next_call(self):
        items, pins, ledger = self.frame()
        a = ledger.reserve("case000", b"{}", deadline=self.clock.now + 100)
        ledger.finish(a, "response_saved", {"usage": {"prompt_tokens": 2000, "completion_tokens": 1}})
        with self.assertRaises(c.BoundaryError):
            ledger.reserve("case001", b"{}", deadline=self.clock.now + 100)
        self.assertFalse(ledger.summary(True)["terminal_no_active_requests"])

    def test_responses_envelope_and_duplicate_json(self):
        view = cloud.visible_view("Astra", dict(status="completed", model="linkup-gpt-6-astra",
            output=[dict(type="reasoning", summary=[]), dict(type="message", content=[dict(type="output_text", text="{}")])],
            usage={"input_tokens": 50, "output_tokens": 20}))
        self.assertEqual(view["content"], "{}")
        self.assertEqual(view["usage"]["prompt_tokens"], 50)
        for text in ('{"x":1,"x":2}', '{"x":1e999}', '{"x":NaN}'):
            with self.assertRaises(c.BoundaryError):
                c.parse_json(text)

    def test_kimi_gateway_exact_source_no_real_network(self):
        items, pins, ledger = self.frame("Kimi")
        c.save(self.d / "ACTIVE_CASE_PRIVATE.json", {"case": "case000"})
        class Response:
            status = 200
            headers = {"Content-Type": "application/json"}
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, n):
                return c.encoded(dict(choices=[dict(finish_reason="stop", message={"content": "{}"})],
                    usage={"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}))
        class Opener:
            calls = 0
            def open(self, req, timeout):
                self.calls += 1
                sent = c.parse_json(req.data)
                assert sent["max_tokens"] == 16000
                assert sent["model"] == "linkup-kimi-k3-1-pro"
                assert "CANDIDATE_SIDE_CONTEXT" not in req.data.decode()
                assert sent["messages"][0] == {"role": "system", "content": c.NOTICE}
                assert len(sent["messages"]) == 2
                return Response()
        class Server:
            def __init__(self, address, handler):
                self.handler = handler
        opener = Opener()
        with patch.object(gateway.http.server, "ThreadingHTTPServer", Server), patch.object(gateway.urllib.request, "build_opener", return_value=opener):
            server = gateway.make_server(self.d, ledger, deadline=self.clock.now + 100)
        payload = dict(model="linkup-kimi-k3-1-pro", messages=[
            dict(role="user", content=c.kimi_prompt(self.d, items[0])),
            dict(role="system", content="CANDIDATE_SIDE_CONTEXT")],
            metadata={"untrusted": "CANDIDATE_SIDE_CONTEXT"}, stream=False)
        def request(body):
            handler = object.__new__(server.handler)
            handler.path = "/stage5/openai/v1/chat/completions"
            handler.headers = {"Content-Length": str(len(body)), "Authorization": "Bearer synthetic-fixture-only"}
            handler.rfile, handler.wfile = io.BytesIO(body), io.BytesIO()
            handler.send_response = lambda *_: None
            handler.send_header = lambda *_: None
            handler.end_headers = lambda: None
            handler.do_POST()
        request(c.encoded(payload))
        self.assertEqual(opener.calls, 1)
        self.assertEqual(ledger.latest("case000")["state"], "response_saved")
        payload["messages"][0]["content"] += "altered"
        request(c.encoded(payload))
        self.assertEqual(opener.calls, 1)

    @unittest.skip("OpenCode-only route removed; direct Azure MI tests replace it")
    def test_config_preflight_emits_no_credentials_or_model_calls(self):
        cli = self.d / "fixture_cli"
        cli.write_text("not executed")
        cli.chmod(0o700)
        config = self.d / "config.json"
        c.save(config, {"providers": {"azure-kimi": {"settings": {
            "baseURL": "https://rg-linkup.openai.azure.com/openai/v1",
            "apiKey": "SYNTHETIC_SECRET_NEVER_PRINT"}}}})
        with patch.object(kimi, "CLI", cli), patch.object(kimi, "PRIVATE_CONFIG", config):
            result = kimi.route_preflight()
        self.assertNotIn("SYNTHETIC_SECRET_NEVER_PRINT", json.dumps(result))
        self.assertEqual(result["new_model_calls"], 0)

    @unittest.skip("OpenCode-only route removed; direct Azure MI tests replace it")
    def test_legacy_route_requires_exact_url_and_configuration(self):
        cli, config, pins = self.legacy_route_fixture()
        original = config.read_bytes()
        with patch.object(kimi, "CLI", cli), patch.object(kimi, "PRIVATE_CONFIG", config), patch.object(kimi, "LEGACY_ROUTE", pins):
            result = kimi.route_preflight()
            self.assertEqual(result["original_endpoint_kind"], "verified_legacy_loopback_to_existing_azure")
            self.assertNotIn("SYNTHETIC_SECRET_NEVER_PRINT", json.dumps(result))
            for bad in ("http://127\0560\0560\0561:60736/bulk1309/openai/v1",
                        "http://localhost:60735/bulk1309/openai/v1",
                        "http://127\0560\0560\0561:60735/other/openai/v1",
                        pins["url"] + "?key=not_allowed", pins["url"] + "#not_allowed",
                        "https://unapproved.example/openai/v1"):
                cfg = c.parse_json(original)
                cfg["providers"]["azure-kimi"]["settings"]["baseURL"] = bad
                c.save(config, cfg)
                with self.assertRaisesRegex(c.BoundaryError, "original_kimi_endpoint_not_approved"):
                    kimi.route_preflight()
            cfg = c.parse_json(original)
            cfg["providers"]["azure-kimi"]["settings"]["apiKey"] = "changed_synthetic_secret"
            c.save(config, cfg)
            with self.assertRaisesRegex(c.BoundaryError, "legacy_kimi_route_provenance_mismatch"):
                kimi.route_preflight()

    @unittest.skip("OpenCode-only route removed; direct Azure MI tests replace it")
    def test_legacy_gateway_source_change_rejected(self):
        cli, config, pins = self.legacy_route_fixture()
        pins["gateway_source"].write_text("# altered provenance\n")
        with patch.object(kimi, "CLI", cli), patch.object(kimi, "PRIVATE_CONFIG", config), patch.object(kimi, "LEGACY_ROUTE", pins):
            with self.assertRaisesRegex(c.BoundaryError, "legacy_kimi_route_provenance_mismatch"):
                kimi.route_preflight()


if __name__ == "__main__":
    unittest.main()

"""Independent offline direct-Kimi migration tests. No auth, sockets, or OpenCode."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import threading
import unittest
from unittest.mock import patch

import stage5_common as c
import stage5_kimi_worker as w
import test_stage5_runtime as rt


class DirectTests(unittest.TestCase):
    setUp = rt.RuntimeTests.setUp
    tearDown = rt.RuntimeTests.tearDown
    frame = rt.RuntimeTests.frame

    def refresh_closure(self, prior, closure, *, terminal=True):
        with c.Ledger(prior, "Kimi", self.prior_items, self.prior_pins).db() as db:
            rows = [dict(x) for x in db.execute("SELECT * FROM attempts")]
        receipt = {
            "status": "stopped_prior_transport_closed", "worker_stopped": True,
            "terminal_no_active_requests": terminal,
            "roster_sha256": self.prior_pins["roster_sha256"],
            "physical_attempts": len(rows), "logical_calls": len({x["context"] for x in rows}),
            "reserved_nano": sum(x["dollars_nano"] for x in rows),
            "prior_files_sha256": {str(p.relative_to(prior)): c.sha(p)
                for p in sorted(prior.rglob("*")) if p.is_file()},
        }
        c.save(closure, receipt)
        return receipt

    def fixture(self, count=3, admitted=1, state="response_saved"):
        items, pins, unused = self.frame("Kimi", count)
        unused.path.unlink()  # Only this test's empty, newly created fixture ledger.
        prior = self.d / "prior"
        prior.mkdir()
        for source in self.d.iterdir():
            if source.is_file():
                shutil.copy2(source, prior / source.name)
        self.prior_items, self.prior_pins = items, pins
        ledger = c.Ledger(prior, "Kimi", items, pins)
        for item in items[:admitted]:
            payload = w.direct_payload(prior, item)
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
            attempt = ledger.reserve(item["case"], c.encoded(payload), deadline=self.clock.now + 10000)
            if state != "forwarding_uncertain":
                detail = {"http_status": 503 if state == "retryable_confirmed_http" else 200,
                    "complete": state == "response_saved", "filtered": state.startswith("quarantined"),
                    "finish_reasons": ["stop"], "usage_reported": True,
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
                    "rate_headers": {}}
                ledger.finish(attempt, state, detail, quarantined=state.startswith("quarantined"))
            dest = prior / "results" / item["case"]
            dest.mkdir(parents=True, exist_ok=True)
            if state == "response_saved":
                c.immutable(dest / "VISIBLE_RESPONSE_PRIVATE.txt", b"{}")
            c.save(dest / "EXECUTION_PRIVATE.json", {
                "case": item["case"], "roster_sha256": pins["roster_sha256"],
                "record_id": item["row"]["record_id"], "context_sha256": item["row"]["context_sha256"],
                "status": state, "finished": state != "forwarding_uncertain", "submitted": True,
            })
            self.clock.now += 61
        closure = self.d / "CLOSURE_PUBLIC.json"
        terminal = state not in ("forwarding_uncertain", "transport_uncertain_no_retry", "usage_reservation_breach_stop")
        self.refresh_closure(prior, closure, terminal=terminal)
        return items, pins, prior, closure, ledger

    def imported(self, prior, closure):
        with patch.object(w, "APPROVED_PRIOR_CODE_SHA256", self.prior_pins["code_sha256"]):
            return w.import_prior(self.d, prior, closure)

    def new_ledger(self):
        items, pins = c.load_inputs(self.d, "Kimi")
        return c.Ledger(self.d, "Kimi", items, pins)

    def args(self):
        return argparse.Namespace(directory=str(self.d), max_wall_seconds=10000,
            workflow_directory=str(Path.home() / "migration/code"))

    def test_direct_payload_exact_frozen_nonstream_contract(self):
        items, pins, unused = self.frame("Kimi", 1)
        payload = w.direct_payload(self.d, items[0])
        expected = {"model": "linkup-kimi-k3-1-pro", "messages": [
            {"role": "system", "content": c.NOTICE},
            {"role": "user", "content": c.kimi_prompt(self.d, items[0])}],
            "max_tokens": 16000, "stream": False}
        self.assertEqual(c.encoded(payload), c.encoded(expected))
        self.assertEqual(c.MODELS["Kimi"]["tpm"], 240000)
        self.assertEqual(c.AGGREGATE_TPM, 800000)

    def test_prior_rows_and_reservations_carried_idempotently(self):
        items, pins, prior, closure, previous = self.fixture(count=4, admitted=2)
        prior_hashes = {str(p.relative_to(prior)): c.sha(p) for p in prior.rglob("*") if p.is_file()}
        self.imported(prior, closure)
        self.imported(prior, closure)
        current = self.new_ledger()
        self.assertEqual(current.summary()["physical_attempts"], 2)
        self.assertEqual(current.summary()["logical_calls"], 2)
        self.assertEqual(current.summary()["reserved_nano"], previous.summary()["reserved_nano"])
        self.assertEqual(w.imported_contexts(current), {x["row"]["context_sha256"] for x in items[:2]})
        with current.db() as db, previous.db() as old:
            rows = [tuple(r) for r in db.execute("SELECT * FROM attempts ORDER BY id")]
            old_rows = [tuple(r) for r in old.execute("SELECT * FROM attempts ORDER BY id")]
            self.assertEqual(rows, old_rows)
        self.assertEqual(prior_hashes,
            {str(p.relative_to(prior)): c.sha(p) for p in prior.rglob("*") if p.is_file()})

    def test_changed_closure_rejected_after_import(self):
        items, pins, prior, closure, previous = self.fixture()
        self.imported(prior, closure)
        changed = c.read(closure)
        changed["annotation_changed"] = True
        c.save(closure, changed)
        with self.assertRaises(c.BoundaryError):
            self.imported(prior, closure)

    def test_changed_prior_evidence_rejected(self):
        items, pins, prior, closure, previous = self.fixture()
        (prior / "results" / items[0]["case"] / "VISIBLE_RESPONSE_PRIVATE.txt").write_text("changed")
        with self.assertRaises(c.BoundaryError):
            self.imported(prior, closure)

    def test_prior_not_stopped_rejected(self):
        items, pins, prior, closure, previous = self.fixture()
        bad = c.read(closure)
        bad["worker_stopped"] = False
        c.save(closure, bad)
        with self.assertRaises(c.BoundaryError):
            self.imported(prior, closure)

    def test_prior_quota_metadata_preserved(self):
        items, pins, prior, closure, previous = self.fixture()
        expected = {"tpm": "100000", "rpm": "3", "cooldown": str(self.clock.now + 1000),
                    "remaining": "23456", "remaining_at": str(self.clock.now)}
        with previous.db() as db:
            for k, v in expected.items():
                db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, v))
        self.refresh_closure(prior, closure)
        self.imported(prior, closure)
        with self.new_ledger().db() as db:
            actual = dict(db.execute("SELECT key,value FROM meta"))
        for k, v in expected.items():
            self.assertEqual(actual[k], v)

    def test_physical_cap_includes_prior_attempts(self):
        with patch.dict(c.MODELS["Kimi"], {"physical": 2}):
            items, pins, prior, closure, previous = self.fixture(count=3, admitted=2)
            self.imported(prior, closure)
            current = self.new_ledger()
            with self.assertRaisesRegex(c.BoundaryError, "persistent_attempt_or_dollar_cap"):
                current.reserve(items[2]["case"], c.encoded(w.direct_payload(self.d, items[2])),
                    deadline=self.clock.now + 1000)
            self.assertEqual(current.summary()["physical_attempts"], 2)

    def test_dollar_cap_includes_prior_reservations(self):
        with patch.dict(c.MODELS["Kimi"], {"cap_nano": 400000000}):
            items, pins, prior, closure, previous = self.fixture(count=3, admitted=2)
            self.imported(prior, closure)
            current = self.new_ledger()
            self.assertGreater(current.summary()["reserved_nano"], 0)
            with self.assertRaisesRegex(c.BoundaryError, "persistent_attempt_or_dollar_cap"):
                current.reserve(items[2]["case"], c.encoded(w.direct_payload(self.d, items[2])),
                    deadline=self.clock.now + 1000)

    def test_imported_uncertainty_blocks_later_admission(self):
        items, pins, prior, closure, previous = self.fixture(state="transport_uncertain_no_retry")
        self.imported(prior, closure)
        current = self.new_ledger()
        self.assertFalse(current.summary(terminal=True)["terminal_no_active_requests"])
        with self.assertRaisesRegex(c.BoundaryError, "active_or_interrupted_request_hold"):
            current.reserve(items[1]["case"], c.encoded(w.direct_payload(self.d, items[1])),
                deadline=self.clock.now + 1000)

    def test_prior_retryable_context_never_reauthenticates_or_retries(self):
        items, pins, prior, closure, previous = self.fixture(count=1, admitted=1, state="retryable_confirmed_http")
        self.imported(prior, closure)
        auth_calls = []
        class NoNetwork:
            def open(self, *args, **kwargs):
                raise AssertionError("imported_context_was_forwarded")
        def auth(*args):
            auth_calls.append(args)
            raise AssertionError("imported_context_requested_authentication")
        with patch("sys.stdout", io.StringIO()), patch("subprocess.run", side_effect=AssertionError("OpenCode forbidden")):
            w.run_direct(self.args(), token_provider=auth, opener=NoNetwork())
        self.assertEqual(auth_calls, [])
        self.assertEqual(self.new_ledger().summary()["physical_attempts"], 1)

    def test_skip_ten_prior_successes_only_call_two_new_contexts(self):
        items, pins, prior, closure, previous = self.fixture(count=12, admitted=10)
        self.imported(prior, closure)
        sent, auth_calls = [], []
        class Response:
            status = 200
            headers = {"Content-Type": "application/json"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, maximum):
                return c.encoded({"model": "Kimi-K3.1-Pro", "choices": [
                    {"finish_reason": "stop", "message": {"content": "{}"}}],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}})
        class Opener:
            def open(self, request, timeout):
                sent.append(request.data)
                self.assert_url = request.full_url
                if self.assert_url != "https://rg-linkup.openai.azure.com/openai/v1/chat/completions":
                    raise AssertionError("unapproved_direct_endpoint")
                return Response()
        def auth(*args):
            auth_calls.append(args)
            return "SYNTHETIC_NOT_A_CREDENTIAL"
        with patch("sys.stdout", io.StringIO()), patch("subprocess.run", side_effect=AssertionError("OpenCode forbidden")):
            w.run_direct(self.args(), token_provider=auth, opener=Opener())
        self.assertEqual(len(auth_calls), 2)
        self.assertEqual(sent, [c.encoded(w.direct_payload(self.d, item)) for item in items[10:]])
        current = self.new_ledger().summary()
        self.assertEqual(current["physical_attempts"], 12)
        self.assertEqual(current["logical_calls"], 12)
        self.assertGreater(current["reserved_nano"], previous.summary()["reserved_nano"])
        self.assertTrue(current["reserved_nano"] <= c.MODELS["Kimi"]["cap_nano"])
        self.assertEqual(len((self.d / "OUTPUTS_PRIVATE.jsonl").read_text().splitlines()), 12)


    def test_stop_after_reservation_never_forwards(self):
        items, pins, prior, closure, previous = self.fixture(count=2, admitted=1)
        self.imported(prior, closure)
        stop = threading.Event()
        sent = []
        original = c.Ledger.reserve
        def reserve_then_stop(ledger, *args, **kwargs):
            attempt = original(ledger, *args, **kwargs)
            stop.set()
            return attempt
        class Opener:
            def open(self, *args, **kwargs):
                sent.append(args)
                raise AssertionError("stop_after_reserve_forwarded")
        with patch.object(c.Ledger, "reserve", reserve_then_stop), patch("sys.stdout", io.StringIO()):
            final = w.run_direct(self.args(), token_provider=lambda *_: "SYNTHETIC_TOKEN",
                opener=Opener(), stop_event=stop)
        self.assertEqual(sent, [])
        self.assertFalse(final["terminal_no_active_requests"])
        latest = self.new_ledger().latest(items[1]["case"])
        self.assertEqual(latest["state"], "transport_uncertain_no_retry")
        self.assertFalse(c.parse_json(latest["detail"])["provider_forwarded"])

    def test_tampered_prior_cost_decomposition_rejected_before_auth(self):
        items, pins, prior, closure, previous = self.fixture()
        self.imported(prior, closure)
        path = self.d / "PRIOR_IMPORT_PUBLIC.json"
        receipt = c.read(path)
        receipt["imported_reserved_nano"] += 1
        c.save(path, receipt)
        calls = []
        def auth(*args):
            calls.append(args)
            raise AssertionError("tampered_decomposition_requested_auth")
        with self.assertRaisesRegex(c.BoundaryError, "prior_import_cost_decomposition_mismatch"):
            w.run_direct(self.args(), token_provider=auth, opener=object())
        self.assertEqual(calls, [])

    def error_case(self, status, code, expected_code):
        items, pins, prior, closure, previous = self.fixture(count=3, admitted=1)
        self.imported(prior, closure)
        secret_message = "SYNTHETIC_FREE_TEXT_MUST_NEVER_BE_SAVED"
        sent = []
        class Response:
            headers = {"Content-Type": "application/json"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit):
                return c.encoded({"error": {"code": code, "message": secret_message}})
        Response.status = status
        class Opener:
            def open(self, request, timeout):
                sent.append(request.data)
                return Response()
        output = io.StringIO()
        with patch("sys.stdout", output):
            w.run_direct(self.args(), token_provider=lambda *_: "SYNTHETIC_TOKEN", opener=Opener())
        self.assertEqual(len(sent), 1)
        self.assertNotIn(secret_message, output.getvalue())
        latest = self.new_ledger().latest(items[1]["case"])
        detail = c.parse_json(latest["detail"])
        self.assertEqual(latest["state"], "http_error_terminal")
        self.assertEqual(detail["http_status"], status)
        self.assertEqual(detail.get("error_code"), expected_code)
        self.assertNotIn(secret_message, latest["detail"])
        for path in self.d.rglob("*"):
            if path.is_file():
                self.assertNotIn(secret_message.encode(), path.read_bytes())
        self.assertIsNone(self.new_ledger().latest(items[2]["case"]))

    def test_http401_retains_only_symbolic_error_code(self):
        self.error_case(401, "Unauthorized", "Unauthorized")

    def test_http403_retains_only_symbolic_error_code(self):
        self.error_case(403, "Forbidden", "Forbidden")

    def test_free_text_error_code_not_preserved(self):
        self.error_case(403, "Not a symbolic code; do not save", None)


if __name__ == "__main__":
    unittest.main()

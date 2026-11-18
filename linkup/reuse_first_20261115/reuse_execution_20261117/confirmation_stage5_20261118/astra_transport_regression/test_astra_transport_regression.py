"""Offline proposal tests: no runtime writes, real identity helper, or network."""
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parent / "runtime"
sys.path.insert(0, str(RUNTIME))
import test_stage5_runtime as fixtures

ORIGINAL = fixtures.c
CHANGES = {
    "stage5_common.py": (
        'input=encoded(row).decode(), max_output_tokens=p["output"],',
        'input="Return JSON.\\n" + encoded(row).decode(), max_output_tokens=p["output"],'),
    "stage5_cloud_worker.py": (
        'stop = status in (401, 403)\n',
        'stop = status in (401, 403) or (args.leg == "Astra" and status == 400 and not filtered)\n'),
}


def proposal_diff():
    """The public Markdown copy remains usable when .patch is not published."""
    raw = (HERE / "README.md").read_text().split("```diff\n", 1)[1].split("```", 1)[0].encode()
    standalone = HERE / "ASTRA_TRANSPORT_FIX_UNAPPLIED.patch"
    if standalone.exists():
        assert standalone.read_bytes() == raw
    return raw


def proposed_sources():
    """Bind the two in-memory replacements to the exact delivered diff."""
    sources, diff = {}, ""
    for name, (old, new) in CHANGES.items():
        original = (RUNTIME / name).read_text()
        assert original.count(old) == 1, "proposal no longer matches original"
        sources[name] = original.replace(old, new)
        diff += "".join(difflib.unified_diff(
            original.splitlines(keepends=True), sources[name].splitlines(keepends=True),
            fromfile="a/runtime/" + name, tofile="b/runtime/" + name))
    assert diff.encode() == proposal_diff()
    return sources


def memory_module(filename, source, common):
    module = types.ModuleType("regression_" + filename[:-3])
    # The reused fixture checks originals' hashes; no modified file is installed.
    module.__file__ = str(RUNTIME / filename)
    with patch.dict(sys.modules, {"stage5_common": common}):
        exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


class RegressionTests(unittest.TestCase):
    frame = fixtures.RuntimeTests.frame

    def setUp(self):
        sources = proposed_sources()
        self.c = memory_module("stage5_common.py", sources["stage5_common.py"], ORIGINAL)
        self.cloud = memory_module("stage5_cloud_worker.py", sources["stage5_cloud_worker.py"], self.c)
        self.binding = patch.object(fixtures, "c", self.c)
        self.binding.start()
        fixtures.RuntimeTests.setUp(self)
        self.saved_umask = os.umask(0o077)
        self.network_guards = [patch(name, side_effect=AssertionError("network forbidden"))
            for name in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection")]
        for guard in self.network_guards:
            guard.start()

    def tearDown(self):
        for guard in reversed(self.network_guards):
            guard.stop()
        os.umask(self.saved_umask)
        fixtures.RuntimeTests.tearDown(self)
        self.binding.stop()

    def run_http(self, sequence, leg="Astra", count=6):
        """Use original frame/ledger/worker flow with synthetic inputs and HTTP."""
        field, frozen = self.d / "field_fixture.py", self.d / "frozen_fixture.py"
        field.write_text("# Synthetic hash-only adapter; no output validation expected.\n")
        frozen.write_text("def validate_packet(rows):\n    assert rows\n    assert all('full_document' in row for row in rows)\n")
        save = self.c.save

        def save_with_validator_pins(path, value):
            if Path(path).name == "INPUT_PINS_PUBLIC.json":
                value["runtime_sha256"] = {
                    "field_validator": self.c.sha(field), "frozen_validator": self.c.sha(frozen)}
            return save(path, value)

        with patch.object(self.c, "save", save_with_validator_pins):
            items, pins, ledger = self.frame(leg, count)
        sent = []

        def fake_open(request, timeout):
            status, raw = sequence[min(len(sent), len(sequence) - 1)]
            sent.append(json.loads(request.data))
            response = io.BytesIO(raw)
            response.status, response.headers = status, {}
            return response

        opener = types.SimpleNamespace(open=Mock(side_effect=fake_open))
        workflow = types.ModuleType("workflow")
        workflow.token = Mock(return_value="SYNTHETIC_NOT_A_CREDENTIAL")
        args = types.SimpleNamespace(leg=leg, directory=str(self.d),
            field_validator=str(field), frozen_validator=str(frozen),
            workflow_directory=str(Path.home() / "migration/code"), max_wall_seconds=100)
        with patch.dict(sys.modules, {"workflow": workflow}),\
             patch.object(sys, "path", list(sys.path)),\
             patch.object(self.cloud.urllib.request, "build_opener", return_value=opener),\
             patch("sys.stdout", io.StringIO()):
            self.cloud.run(args)
        final = self.c.read(self.d / (leg.upper() + "_FINAL_PUBLIC.json"))
        rows = [json.loads(line) for line in (self.d / "OUTPUTS_PRIVATE.jsonl").read_text().splitlines()]
        self.assertEqual(final["physical_attempts"], len(sent))
        self.assertEqual(workflow.token.call_count, len(sent))
        self.assertEqual(final["outputs_accounted"], count)
        self.assertEqual(self.c.verify_output_frame(items, rows, pins["roster_sha256"]), pins["roster_sha256"])
        return final, rows, sent

    def test_exact_patch_only_changes_two_lines(self):
        proposed_sources()
        diff = proposal_diff()
        readme = (HERE / "README.md").read_text()
        self.assertEqual(readme.split("```diff\n", 1)[1].split("```", 1)[0].encode(), diff)
        self.assertIn(hashlib.sha256(diff).hexdigest(), readme)
        lines = diff.decode().splitlines()
        self.assertEqual(sum(x.startswith("+") and not x.startswith("+++") for x in lines), 2)
        self.assertEqual(sum(x.startswith("-") and not x.startswith("---") for x in lines), 2)

    def test_literal_prefix_preserves_original_source_bytes_and_all_other_fields(self):
        items, _, _ = self.frame("Astra")
        before = ORIGINAL.model_payload(self.d, "Astra", items[0])
        after = self.c.model_payload(self.d, "Astra", items[0])
        prefix = b"Return JSON.\n"
        self.assertFalse(before["input"].encode().startswith(prefix))
        self.assertEqual(after["input"].encode(), prefix + before["input"].encode())
        self.assertEqual(json.loads(after["input"][len(prefix):]), items[0]["row"])
        self.assertEqual({k: v for k, v in before.items() if k != "input"},
                         {k: v for k, v in after.items() if k != "input"})

    def test_luna_payload_and_kimi_prompt_unchanged(self):
        items, _, _ = self.frame()
        self.assertEqual(ORIGINAL.model_payload(self.d, "Luna", items[0]),
                         self.c.model_payload(self.d, "Luna", items[0]))
        self.assertEqual(ORIGINAL.kimi_prompt(self.d, items[0]), self.c.kimi_prompt(self.d, items[0]))

    def test_protection_check_precedes_body_or_file_access(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("file read before protection")):
            with self.assertRaisesRegex(self.c.BoundaryError, "blocked_protected_metadata_only"):
                self.c.model_payload(self.d, "Astra", {"blocked": True})

    def test_models_rates_budgets_and_retry_policy_unchanged(self):
        for name in ("MODELS", "NOTICE", "RETRY_HTTP", "AGGREGATE_TPM", "MAX_REQUEST_BYTES",
                     "HISTORICAL_RESERVATION_NANO", "NEW_CAP_NANO", "STAGE_CAP_NANO", "WHOLE_PHASE_CAP_NANO"):
            self.assertEqual(getattr(ORIGINAL, name), getattr(self.c, name))
        self.assertEqual(self.c.MODELS["Astra"]["physical"], 6)

    def test_first_known_json_input_400_stops_all_remaining_slots(self):
        raw = b'{"error":{"param":"input","message":"json_object requires JSON in input"}}'
        final, rows, sent = self.run_http([(400, raw)])
        self.assertEqual(len(sent), 1)
        self.assertTrue(sent[0]["input"].startswith("Return JSON.\n"))
        self.assertEqual(final["attempt_states"], {"http_error_terminal": 1})
        self.assertEqual([x["status"] for x in rows], ["http_error_terminal"] + ["unprocessed_bounded_stop"] * 5)
        self.assertTrue(all(x["payload"] is None for x in rows))
        self.assertEqual(final["field_validation_complete"], 0)

    def test_unrecognized_non_filter_astra_400_also_stops_conservatively(self):
        _, rows, sent = self.run_http([(400, b"unknown request rejection")])
        self.assertEqual(len(sent), 1)
        self.assertEqual(sum(x["status"] == "unprocessed_bounded_stop" for x in rows), 5)

    def test_provider_filter_is_quarantined_not_bypassed_or_retried(self):
        final, rows, sent = self.run_http([
            (400, b'{"error":{"code":"content_filter"}}'), (400, b"input validation rejection")])
        self.assertEqual(len(sent), 2)
        self.assertEqual([x["status"] for x in rows[:2]], ["quarantined_provider_filter", "http_error_terminal"])
        self.assertEqual(final["attempt_states"], {"quarantined_provider_filter": 1, "http_error_terminal": 1})
        self.assertEqual(self.c.read(self.d / "EXCLUSIONS_EXPORT_PRIVATE.json")["context_sha256"], [rows[0]["context_sha256"]])
        self.assertNotEqual(sent[0]["input"], sent[1]["input"])

    def test_luna_400_handling_is_unchanged(self):
        _, rows, sent = self.run_http([(400, b"input validation rejection")], leg="Luna", count=2)
        self.assertEqual(len(sent), 2)
        self.assertEqual([x["status"] for x in rows], ["http_error_terminal"] * 2)

    def test_authentication_stop_is_unchanged(self):
        _, _, sent = self.run_http([(401, b"authentication rejected")])
        self.assertEqual(len(sent), 1)

    def test_confirmed_retry_rule_is_unchanged(self):
        final, _, sent = self.run_http([(429, b"rate limit")], count=1)
        self.assertEqual(len(sent), 2)
        self.assertEqual(final["attempt_states"], {"retryable_confirmed_http": 2})

    def test_six_attempt_cap_remains_final_using_existing_fixture(self):
        fixtures.RuntimeTests.test_astra_sixth_physical_attempt_is_final_cap(self)

    def test_original_runtime_and_evidence_hashes_unchanged(self):
        before = json.loads((HERE / "ORIGINALS_BEFORE_PUBLIC.json").read_text())
        current = {str(p.relative_to(RUNTIME)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(RUNTIME.rglob("*")) if p.is_file()}
        self.assertEqual(current, before["runtime_sha256"])
        for name, expected in before["evidence_sha256"].items():
            self.assertEqual(hashlib.sha256((HERE / name).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)

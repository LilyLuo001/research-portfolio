"""Synthetic-only runtime tests. Real networking and credentials are forbidden."""
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
import pilot_common as c
import pilot_worker as w


class Clock:
    def __init__(self):
        self.now = 1000000000.0
        self.lock = threading.Lock()

    def time(self):
        with self.lock:
            return self.now

    def sleep(self, value):
        with self.lock:
            self.now += value


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.d = Path(self.temp.name).resolve()
        self.clock = Clock()
        self.umask = os.umask(0o077)
        self.patches = [patch.object(c.time, "time", self.clock.time), patch.object(c.time, "sleep", self.clock.sleep),
            patch.object(w, "CLOUD_RUN", self.d), patch("socket.socket.connect", side_effect=AssertionError("network forbidden")),
            patch("socket.create_connection", side_effect=AssertionError("network forbidden"))]
        for mock in self.patches:
            mock.start()

    def tearDown(self):
        for mock in reversed(self.patches):
            mock.stop()
        os.umask(self.umask)
        self.temp.cleanup()

    def fixture(self, count=5):
        items = []
        for i in range(count):
            doc = "Synthetic full source %s.\n完整上下文。" % i
            items.append(dict(case="case%05d" % i, protected=False, fresh_never_exposed=True,
                row=dict(record_id="record%05d" % i, context_sha256=hashlib.sha256(doc.encode()).hexdigest(), full_document=doc)))
        (self.d / "INPUTS_PRIVATE.jsonl").write_bytes(b"".join(c.encoded(item) + b"\n" for item in items))
        (self.d / "PHYSICAL_ROWS_PRIVATE.jsonl").write_bytes(b'{"synthetic_mapping":"never_prompted"}\n')
        (self.d / "SCHEMA.json").write_text("{}")
        (self.d / "INSTRUCTIONS.md").write_text("Frozen fixture instructions.")
        c.save(self.d / "EXCLUSIONS_PRIVATE.json", {"context_sha256": [], "tasks": []})
        field, frozen = self.d / "field.py", self.d / "frozen.py"
        field.write_text("import json\nparse_review=json.loads\nclass FieldValidator:\n def __init__(self,*args): pass\n def validate(self,packet,review,protected=False):\n  assert not protected\n  assert all(review[k]==packet[k] for k in ('record_id','context_sha256'))\n  return {'fixture_valid':True}\n")
        frozen.write_text("def validate_packet(rows):\n assert rows\n assert all('full_document' in r for r in rows)\n")
        policy = dict(protocol_version=c.VERSION, released_measure_ids=["synthetic_measure"],
            phase_prior_reserved_nano=c.MIN_PRIOR_RESERVED_NANO,
            prior_confirmation_reserved_nano=c.CONFIRMATION_RESERVED_NANO,
            phase_infrastructure_reserved_nano=c.INFRASTRUCTURE_CAP_NANO, phase_cap_nano=c.PHASE_CAP_NANO,
            pins={name:c.sha(self.d/name) for name in ("INPUTS_PRIVATE.jsonl", "PHYSICAL_ROWS_PRIVATE.jsonl", "EXCLUSIONS_PRIVATE.json", "SCHEMA.json", "INSTRUCTIONS.md")},
            code_sha256={name:c.sha(Path(c.__file__).parent/name) for name in ("pilot_common.py", "pilot_worker.py")},
            runtime_sha256={"field_validator":c.sha(field), "frozen_validator":c.sha(frozen)})
        c.save(self.d / "policy.json", policy)
        args = types.SimpleNamespace(directory=str(self.d), policy=str(self.d/"policy.json"),
            leg="Luna", field_validator=str(field), frozen_validator=str(frozen),
            batch_manifest=None, batch_manifest_sha256=None, concurrency=2, max_new_logical=100,
            max_wall_seconds=14400, stop_file=None, workflow_directory=str(w.WORKFLOW_DIRECTORY))
        return items, policy, args

    def ledger(self, policy):
        return c.Ledger(self.d, policy, c.sha(self.d/"policy.json"))

    def run_fake(self, args, status=200, exception=None):
        requests = []
        lock = threading.Lock()
        def fake_open(request, timeout):
            with lock:
                payload = c.parse_json(request.data)
                requests.append(payload)
            if exception:
                raise exception
            if status == 200:
                row = c.parse_json(payload["messages"][1]["content"])
                review = {key:row[key] for key in ("record_id", "context_sha256")}
                raw = c.encoded(dict(model="gpt-6-luna-2026-09-22", choices=[dict(finish_reason="stop", message={"content":json.dumps(review)})],
                    usage={"prompt_tokens":10,"completion_tokens":10,"total_tokens":20}))
            else:
                raw = b'{"error":{"param":"input","message":"json_object needs JSON"}}'
            response = io.BytesIO(raw)
            response.status, response.headers = status, {}
            return response
        opener = types.SimpleNamespace(open=Mock(side_effect=fake_open))
        token = Mock(return_value="SYNTHETIC_NOT_A_CREDENTIAL")
        with patch.object(w, "identity_token_function", return_value=token), \
             patch.object(w.urllib.request, "build_opener", return_value=opener), patch("sys.stdout", io.StringIO()):
            final = w.run(args)
        return final, requests

    def test_hard_caps_and_new_version(self):
        _, policy, _ = self.fixture()
        c.validate_policy(policy)
        self.assertEqual([p["logical"] for p in c.MODELS.values()], [10000,100,20])
        self.assertEqual([p["physical"] for p in c.MODELS.values()], [12000,100,20])
        self.assertEqual(sum(p["cap_nano"] for p in c.MODELS.values()), 150_000_000_000)
        policy["phase_prior_reserved_nano"] = 400_000_000_000
        with self.assertRaisesRegex(c.BoundaryError,"phase_accounting_boundary"):
            c.validate_policy(policy)

    def test_payload_exact_scientific_transfer_and_astra_prefix(self):
        items, _, _ = self.fixture()
        old_path = Path(__file__).parents[2]/"confirmation_stage5_20261118/runtime/stage5_common.py"
        old = c.import_path("original_scientific_payload", old_path)
        self.assertEqual(c.NOTICE, old.NOTICE)
        self.assertEqual(c.model_payload(self.d,"Luna",items[0],{}), old.model_payload(self.d,"Luna",items[0]))
        before, after = old.model_payload(self.d,"Astra",items[0]), c.model_payload(self.d,"Astra",items[0],{})
        self.assertEqual(after.pop("input").encode(), b"Return JSON.\n"+before.pop("input").encode())
        self.assertEqual(after,before)
        expected = dict(model=old.MODELS["Kimi"]["deployment"], messages=[{"role":"system","content":old.NOTICE},
            {"role":"user","content":old.kimi_prompt(self.d,items[0])}], max_tokens=16000, stream=False)
        self.assertEqual(c.model_payload(self.d,"Kimi",items[0],{}), expected)

    def test_protected_before_body_access(self):
        with patch.object(Path,"read_text",side_effect=AssertionError("body read")):
            with self.assertRaisesRegex(c.BoundaryError,"protected_before_payload"):
                c.model_payload(self.d,"Luna",{"blocked":True}, {})

    def test_input_and_mapping_pin_tampering_blocks_before_calls(self):
        _, _, args = self.fixture()
        (self.d/"PHYSICAL_ROWS_PRIVATE.jsonl").write_text("tampered")
        with self.assertRaisesRegex(c.BoundaryError,"policy_file_pin_mismatch"):
            c.load_bundle(self.d,args.policy)

    def test_more_than_old150_contexts_are_allowed(self):
        _, _, args = self.fixture(151)
        _, items, _, _ = c.load_bundle(self.d,args.policy)
        self.assertEqual(len(items),151)

    def test_atomic_exclusive_claim(self):
        items, policy, _ = self.fixture()
        ledger = self.ledger(policy)
        def reserve(_):
            try:
                return ledger.reserve("Luna",items[0],b"{}",self.clock.now+100,100)
            except c.BoundaryError:
                return None
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            results = list(pool.map(reserve,range(4)))
        self.assertEqual(sum(x is not None for x in results),1)
        self.assertEqual(ledger.summary()["legs"]["Luna"]["physical_attempts"],1)

    def test_reservation_uses_full_bytes_not_actual_usage_credit(self):
        items, policy, _ = self.fixture()
        ledger = self.ledger(policy)
        body = b"x"*2000
        attempt = ledger.reserve("Luna",items[0],body,self.clock.now+100,100)
        expected = (len(body)+1024)*100 + 12000*500
        ledger.finish(attempt,"field_local_validation_complete",{"usage":{"prompt_tokens":1,"completion_tokens":1}})
        self.assertEqual(ledger.summary()["reserved_nano"],expected)

    def test_unknown_transport_never_retries_and_holds_restart(self):
        _, policy, args = self.fixture(3)
        args.concurrency = 1
        final, sent = self.run_fake(args,exception=TimeoutError())
        self.assertEqual(len(sent),1)
        self.assertEqual(final["uncertain_requests"],1)
        self.assertFalse(final["terminal_no_active_requests"])
        second, sent = self.run_fake(args)
        self.assertEqual(len(sent),0)
        self.assertIsNotNone(second["admission_hold"])

    def test_systemic400_stops_first_without_spending_batch(self):
        _, _, args = self.fixture(6)
        args.concurrency = 1
        final, sent = self.run_fake(args,status=400)
        self.assertEqual(len(sent),1)
        self.assertEqual(final["admission_hold"],"systemic_http_400")
        self.assertEqual(final["outputs_accounted"],6)
        self.assertEqual(final["unprocessed"],5)

    def test_two_concurrent_workers_do_not_exceed_launch_ceiling(self):
        _, _, args = self.fixture(6)
        args.max_new_logical = 3
        final, sent = self.run_fake(args)
        self.assertEqual(len(sent),3)
        self.assertEqual(final["legs"]["Luna"]["logical_calls"],3)
        self.assertEqual(final["outputs_accounted"],6)
        self.assertTrue(all("never_prompted" not in json.dumps(p) for p in sent))

    def test_cache_resume_checks_sha_and_does_not_reissue(self):
        _, _, args = self.fixture(3)
        first, sent = self.run_fake(args)
        self.assertEqual(len(sent),3)
        second, sent = self.run_fake(args)
        self.assertEqual(len(sent),0)
        self.assertEqual(first["reserved_nano"],second["reserved_nano"])
        result = next((self.d/"results").rglob("RESULT_PRIVATE.json"))
        result.write_text("tampered")
        third, sent = self.run_fake(args)
        self.assertEqual(len(sent),0)
        self.assertIsNotNone(third["admission_hold"])

    def test_retry_only_confirmed_at_most_two_and_twenty_percent(self):
        items, policy, _ = self.fixture(5)
        ledger = self.ledger(policy)
        for item in items:
            attempt=ledger.reserve("Luna",item,b"{}",self.clock.now+1000,100)
            ledger.finish(attempt,"retryable_confirmed_http",{"http_status":503})
        attempt=ledger.reserve("Luna",items[0],b"{}",self.clock.now+1000,100)
        ledger.finish(attempt,"retryable_confirmed_http",{"http_status":503})
        with self.assertRaisesRegex(c.BoundaryError,"duplicate_or_uncertain"):
            ledger.reserve("Luna",items[0],b"{}",self.clock.now+1000,100)
        with self.assertRaisesRegex(c.BoundaryError,"twenty_percent"):
            ledger.reserve("Luna",items[1],b"{}",self.clock.now+1000,100)

    def test_global_and_leg_rate_windows(self):
        items, policy, _ = self.fixture(3)
        ledger = self.ledger(policy)
        for item in items[:2]:
            attempt=ledger.reserve("Luna",item,b"x"*25000,self.clock.now+1000,100)
            ledger.finish(attempt,"field_local_validation_complete",{})
        before=self.clock.now
        ledger.reserve("Luna",items[2],b"x"*25000,self.clock.now+1000,100)
        self.assertGreaterEqual(self.clock.now-before,60.1)

    def test_quarantine_is_cross_leg_and_never_retried(self):
        items, policy, _ = self.fixture()
        ledger=self.ledger(policy)
        attempt=ledger.reserve("Luna",items[0],b"{}",self.clock.now+100,100)
        ledger.finish(attempt,"quarantined_provider_filter",{"http_status":400},quarantined=True)
        self.assertIsNone(ledger.summary()["admission_hold"])
        for leg in c.MODELS:
            with self.assertRaisesRegex(c.BoundaryError,"quarantined"):
                ledger.reserve(leg,items[0],b"{}",self.clock.now+100,100)

    def test_audit_requires_completed_main_and_obeys_own_dollar_cap(self):
        items, policy, _=self.fixture()
        ledger=self.ledger(policy)
        with self.assertRaisesRegex(c.BoundaryError,"audit_requires_completed"):
            ledger.reserve("Kimi",items[0],b"{}",self.clock.now+100,100)
        attempt=ledger.reserve("Luna",items[0],b"{}",self.clock.now+100,100)
        c.save(self.d/"synthetic_result.json",{})
        ledger.finish(attempt,"field_local_validation_complete",{},self.d/"synthetic_result.json")
        attempt=ledger.reserve("Kimi",items[0],b"{}",self.clock.now+100,100)
        ledger.finish(attempt,"http_error_terminal",{})
        with ledger.db() as db:
            db.execute("UPDATE attempts SET dollars_nano=? WHERE leg='Luna'",(c.MODELS['Luna']['cap_nano'],))
        with self.assertRaisesRegex(c.BoundaryError,"persistent_attempt_or_dollar_cap"):
            ledger.reserve("Luna",items[1],b"{}",self.clock.now+100,100)

    def test_batch_append_chain_and_policy_binding(self):
        _, policy, _=self.fixture()
        ledger=self.ledger(policy)
        first=dict(batch_id="batch0001",manifest_sha256="a"*64)
        ledger.register_batch(first)
        ledger.register_batch(first)
        with self.assertRaisesRegex(c.BoundaryError,"batch_append_chain"):
            ledger.register_batch(dict(batch_id="batch0002",manifest_sha256="b"*64))
        ledger.register_batch(dict(batch_id="batch0002",manifest_sha256="b"*64,previous_batch_manifest_sha256="a"*64))
        self.assertEqual(ledger.summary()["registered_batches"],2)
        with self.assertRaisesRegex(c.BoundaryError,"identity_changed"):
            c.Ledger(self.d,policy,"different_policy_hash")

    def test_pinned_manifest_loader_uses_external_physical_mapping(self):
        _, _, args=self.fixture()
        manifest=dict(batch_id="batch0001", previous_batch_manifest_sha256=None,
            filenames={"inputs":"INPUTS_PRIVATE.jsonl","physical_rows":"PHYSICAL_ROWS_PRIVATE.jsonl","exclusions":"EXCLUSIONS_PRIVATE.json"},
            inputs_sha256=c.sha(self.d/"INPUTS_PRIVATE.jsonl"), physical_rows_sha256=c.sha(self.d/"PHYSICAL_ROWS_PRIVATE.jsonl"),
            exclusions_sha256=c.sha(self.d/"EXCLUSIONS_PRIVATE.json"))
        c.save(self.d/"BATCH_MANIFEST_PUBLIC.json",manifest)
        _,items,_,batch=c.load_bundle(self.d,args.policy,self.d/"BATCH_MANIFEST_PUBLIC.json",c.sha(self.d/"BATCH_MANIFEST_PUBLIC.json"))
        self.assertEqual(len(items),5)
        self.assertEqual(batch["physical_mapping_file_sha256"],manifest["physical_rows_sha256"])
        with self.assertRaisesRegex(c.BoundaryError,"explicit_batch_hash"):
            c.load_bundle(self.d,args.policy,self.d/"BATCH_MANIFEST_PUBLIC.json","wrong")

    def test_first100_checkpoint_then_explicit_continuation_same_ledger(self):
        _,_,args=self.fixture(101)
        first,sent=self.run_fake(args)
        self.assertEqual(len(sent),100)
        self.assertEqual(first["legs"]["Luna"]["logical_calls"],100)
        self.assertTrue((self.d/"CHECKPOINT_100_PUBLIC.json").exists())
        checkpoint_sha=c.sha(self.d/"CHECKPOINT_100_PUBLIC.json")
        args.max_new_logical=10000
        second,sent=self.run_fake(args)
        self.assertEqual(len(sent),1)
        self.assertEqual(second["legs"]["Luna"]["logical_calls"],101)
        self.assertEqual(checkpoint_sha,c.sha(self.d/"CHECKPOINT_100_PUBLIC.json"))

    def test_aggregate_window_includes_other_leg(self):
        items,policy,_=self.fixture()
        ledger=self.ledger(policy)
        # A synthetic already-reserved other-leg window exercises the shared limiter.
        with ledger.db() as db:
            db.execute("INSERT INTO attempts(leg,context,attempt,state,forwarded,input_upper,tokens,dollars_nano,request_sha) VALUES(?,?,?,?,?,?,?,?,?)",
                ("Kimi","synthetic_other_context",1,"field_local_validation_complete",self.clock.now,1,795000,1,"synthetic"))
        before=self.clock.now
        ledger.reserve("Luna",items[0],b"{}",self.clock.now+1000,100)
        self.assertGreaterEqual(self.clock.now-before,60.1)

    def test_usage_breach_and_observed_lower_quota_stop(self):
        items,policy,_=self.fixture()
        ledger=self.ledger(policy)
        attempt=ledger.reserve("Luna",items[0],b"{}",self.clock.now+100,100)
        ledger.finish(attempt,"field_local_validation_complete",{"usage":{"prompt_tokens":2000,"completion_tokens":1}})
        self.assertEqual(ledger.summary()["admission_hold"],"usage_reservation_breach_stop")
        with self.assertRaisesRegex(c.BoundaryError,"global_hold"):
            ledger.reserve("Luna",items[1],b"{}",self.clock.now+100,100)

    def test_kimi_short_identifier_requires_exact_arm_evidence(self):
        _,policy,_=self.fixture()
        self.assertFalse(w.expected_model_allowed("Kimi","Kimi-K3.1",self.d,policy))
        source=Path(__file__).parents[2]/"confirmation_stage5_20261118/control/DIRECT_ARM_DEPLOYMENT_PUBLIC.json"
        (self.d/"ARM_PUBLIC.json").write_bytes(source.read_bytes())
        policy["kimi_arm_evidence"]={"path":"ARM_PUBLIC.json","sha256":w.ARM_IDENTITY_SHA256}
        self.assertTrue(w.expected_model_allowed("Kimi","Kimi-K3.1",self.d,policy))
        self.assertFalse(w.expected_model_allowed("Kimi","different_model",self.d,policy))

    def test_successful_other_fields_survive_field_local_failure(self):
        _,policy,args=self.fixture(1)
        field=Path(args.field_validator)
        field.write_text(field.read_text().replace("return {'fixture_valid':True}","return {'fixture_valid':True,'other_field':{'status':'invalid'}}"))
        policy["runtime_sha256"]["field_validator"]=c.sha(field)
        c.save(self.d/"policy.json",policy)
        final,_=self.run_fake(args)
        self.assertEqual(final["field_validation_complete"],1)
        result=c.read(next((self.d/"results").rglob("RESULT_PRIVATE.json")))
        self.assertIsNotNone(result["payload"])
        self.assertEqual(result["field_validation"]["other_field"]["status"],"invalid")

    def test_interrupted_admission_is_held_not_replayed(self):
        items, policy, _=self.fixture()
        ledger=self.ledger(policy)
        ledger.reserve("Luna",items[0],b"{}",self.clock.now+100,100)
        ledger.recover_orphans("Luna")
        with self.assertRaisesRegex(c.BoundaryError,"global_hold"):
            ledger.reserve("Luna",items[1],b"{}",self.clock.now+100,100)

    def test_no_source_or_record_id_in_public_summary(self):
        items, _, args=self.fixture(2)
        final,_=self.run_fake(args)
        public=json.dumps(final)
        for item in items:
            self.assertNotIn(item['row']['record_id'],public)
            self.assertNotIn(item['row']['context_sha256'],public)
            self.assertNotIn(item['row']['full_document'],public)

    def test_original_runtime_files_unchanged(self):
        root=Path(__file__).parents[2]
        before=c.read(Path(__file__).parent/"ORIGINALS_BEFORE_PUBLIC.json")
        self.assertTrue(all(c.sha(root/name)==digest for name,digest in before.items()))


if __name__ == "__main__":
    unittest.main(verbosity=2)

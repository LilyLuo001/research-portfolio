"""Offline migration/rate tests: synthetic ledger, identity and HTTP only."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE_RUNTIME = HERE.parent / "runtime"
sys.path.insert(0, str(BASE_RUNTIME))
import test_pilot_runtime as fixtures
import rate_amendment as a


class AmendmentTests(unittest.TestCase):
    fixture = fixtures.RuntimeTests.fixture

    def setUp(self):
        fixtures.RuntimeTests.setUp(self)
        self.items, self.policy, self.args = self.fixture(10)
        (self.d / "runtime").mkdir()
        for name in a.APPROVED_BASE_CODE:
            (self.d / "runtime" / name).write_bytes((BASE_RUNTIME / name).read_bytes())
        self.common, _, self.policy_sha = a.base_runtime(self.d)
        self.worker = self.load_worker(self.common)
        self.args.concurrency = 1
        self.args.max_new_logical = 2
        self.first, sent = self.run_fake(self.worker)
        self.assertEqual(len(sent), 2)
        self.amendment_path = self.d / "RATE_AMENDMENT_PUBLIC.json"

    def tearDown(self):
        fixtures.RuntimeTests.tearDown(self)

    def load_worker(self, common):
        with patch.dict(sys.modules, {"pilot_common": common}):
            worker = a.module("synthetic_base_worker", self.d / "runtime/pilot_worker.py")
        worker.CLOUD_RUN = self.d
        return worker

    def run_fake(self, worker, header="250000"):
        sent = []
        def fake_open(request, timeout):
            body = self.common.parse_json(request.data)
            sent.append(body)
            row = self.common.parse_json(body["messages"][1]["content"])
            content = json.dumps({key:row[key] for key in ("record_id", "context_sha256")})
            raw = self.common.encoded({"model":"gpt-6-luna-2026-09-22", "choices":[{"finish_reason":"stop", "message":{"content":content}}],
                "usage":{"prompt_tokens":10,"completion_tokens":10,"total_tokens":20}})
            response = io.BytesIO(raw)
            response.status, response.headers = 200, {"x-ratelimit-limit-tokens": header}
            return response
        opener = types.SimpleNamespace(open=Mock(side_effect=fake_open))
        with patch.object(worker,"identity_token_function",return_value=Mock(return_value="SYNTHETIC_TOKEN")), \
             patch.object(worker.urllib.request,"build_opener",return_value=opener), patch("sys.stdout",io.StringIO()):
            final = worker.run(self.args)
        return final, sent

    def prepare(self):
        result = a.prepare(self.d, self.amendment_path)
        self.assertEqual(result["status"], "rate_amendment_prepared_not_applied")
        self.digest = a.sha(self.amendment_path)
        return self.common.read(self.amendment_path)

    def ledger_snapshot(self):
        with contextlib.closing(a.readonly_db(self.d)) as db:
            return a.snapshot(self.common,db,self.d)

    def test_prepare_apply_changes_only_rate_registration_and_clamp(self):
        with self.common.Ledger(self.d,self.policy,self.policy_sha).db() as db:
            db.execute("INSERT INTO meta VALUES('Luna:cooldown',?)",(str(self.clock.now+10),))
            db.execute("INSERT INTO meta VALUES('Luna:remaining','100')")
            db.execute("INSERT INTO meta VALUES('Luna:remaining_at',?)",(str(self.clock.now),))
        before = self.ledger_snapshot()
        amendment = self.prepare()
        self.assertEqual(len(amendment["quota_evidence"]),2)
        result = a.apply(self.d,self.amendment_path,self.digest)
        self.assertTrue(result["all_non_rate_ledger_state_unchanged"])
        self.assertEqual(before,self.ledger_snapshot())
        with contextlib.closing(a.readonly_db(self.d)) as db:
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='Luna:tpm'").fetchone()[0],"200000")
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='Luna:remaining'").fetchone()[0],"100")
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='Luna:cooldown'").fetchone()[0],str(self.clock.now+10))
        self.assertEqual(a.sha(self.d/"policy.json"),self.policy_sha)

    def test_same_batch_resume_keeps_old_cache_and_can_schedule_above80k(self):
        before = self.ledger_snapshot()
        amendment = self.prepare()
        a.apply(self.d,self.amendment_path,self.digest)
        original_class = self.common.Ledger
        original_models = copy.deepcopy(self.common.MODELS)
        rate = a.install_rate_ledger(self.common,self.policy,self.policy_sha,self.d,amendment,self.digest)
        self.assertIs(rate.reserve.__code__, original_class.reserve.__code__)
        self.assertIs(rate.finish.__code__, original_class.finish.__code__)
        self.assertEqual(self.common.MODELS,original_models)
        self.assertEqual(rate.reserve.__globals__["MODELS"]["Luna"]["tpm"],200000)
        worker = self.load_worker(self.common)
        self.args.max_new_logical = 100
        self.args.concurrency = 2
        start = self.clock.now
        final, sent = self.run_fake(worker)
        self.assertEqual(len(sent),8)
        self.assertEqual(final["counters"]["cache_hits"],2)
        self.assertEqual(final["legs"]["Luna"]["logical_calls"],10)
        self.assertEqual(final["legs"]["Luna"]["physical_attempts"],10)
        self.assertEqual(self.clock.now,start)
        self.assertEqual(final["effective_Luna_scheduler_tpm"],200000)
        with contextlib.closing(a.readonly_db(self.d)) as db:
            initial = [dict(row) for row in db.execute("SELECT * FROM attempts WHERE id<=2 ORDER BY id")]
            self.assertEqual(hashlib_sha(self.common.encoded(initial)),before["tables"]["attempts"]["sha256"])
            carrier_policies={self.common.read(self.d/row["result_path"])["policy_sha256"] for row in db.execute("SELECT result_path FROM attempts")}
        self.assertEqual(carrier_policies,{self.policy_sha})

    def test_repeat_apply_never_resets_a_future_lower_quota(self):
        amendment = self.prepare()
        a.apply(self.d,self.amendment_path,self.digest)
        a.install_rate_ledger(self.common,self.policy,self.policy_sha,self.d,amendment,self.digest)
        ledger = self.common.Ledger(self.d,self.policy,self.policy_sha)
        attempt = ledger.reserve("Luna",self.items[2],b"{}",self.clock.now+100,100)
        ledger.finish(attempt,"http_error_terminal",{"http_status":422,"rate_headers":{"x-ratelimit-limit-tokens":"100000"}})
        result = a.apply(self.d,self.amendment_path,self.digest)
        self.assertEqual(result["status"],"same_amendment_already_registered_no_mutation")
        self.assertEqual(ledger.summary()["effective_Luna_scheduler_tpm"],100000)

    def test_reject_active_worker_lease(self):
        with self.common.process_lock(self.d,"Luna"):
            with self.assertRaises(BlockingIOError):
                self.prepare()

    def test_reject_active_or_uncertain_admission(self):
        ledger=self.common.Ledger(self.d,self.policy,self.policy_sha)
        ledger.reserve("Luna",self.items[2],b"{}",self.clock.now+100,100)
        with self.assertRaisesRegex(RuntimeError,"active_or_uncertain"):
            self.prepare()
        ledger.recover_orphans("Luna")
        with self.assertRaisesRegex(RuntimeError,"existing_hold"):
            self.prepare()

    def test_reject_non250k_saved_evidence(self):
        ledger=self.common.Ledger(self.d,self.policy,self.policy_sha)
        with ledger.db() as db:
            detail=self.common.parse_json(db.execute("SELECT detail FROM attempts WHERE id=1").fetchone()[0])
            detail["rate_headers"]["x-ratelimit-limit-tokens"]="100000"
            db.execute("UPDATE attempts SET detail=? WHERE id=1",(self.common.encoded(detail).decode(),))
        with self.assertRaisesRegex(RuntimeError,"uniform_exact_250000"):
            self.prepare()

    def test_snapshot_change_between_prepare_apply_is_rejected(self):
        self.prepare()
        ledger=self.common.Ledger(self.d,self.policy,self.policy_sha)
        with ledger.db() as db:
            db.execute("INSERT INTO meta VALUES('Luna:cooldown','123')")
        with self.assertRaisesRegex(RuntimeError,"checkpoint_changed"):
            a.apply(self.d,self.amendment_path,self.digest)
        with ledger.db() as db:
            self.assertFalse(db.execute("SELECT 1 FROM meta WHERE key=?",(a.AMENDMENT_KEY,)).fetchone())
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='Luna:tpm'").fetchone()[0],"80000")

    def test_tampered_rate_or_digest_rejected(self):
        amendment=self.prepare()
        with self.assertRaisesRegex(RuntimeError,"explicit_amendment_sha"):
            a.apply(self.d,self.amendment_path,"wrong")
        amendment["effective_scheduler_tpm"]=500000
        self.common.save(self.amendment_path,amendment)
        with self.assertRaisesRegex(RuntimeError,"scope_or_code_pin"):
            a.apply(self.d,self.amendment_path,a.sha(self.amendment_path))

    def test_v2_requires_completed_migration(self):
        amendment=self.prepare()
        rate=a.install_rate_ledger(self.common,self.policy,self.policy_sha,self.d,amendment,self.digest)
        with self.assertRaisesRegex(RuntimeError,"migration_required"):
            rate(self.d,self.policy,self.policy_sha)

    def test_postcommit_receipt_recovery_does_not_reapply_rate(self):
        self.prepare()
        a.apply(self.d,self.amendment_path,self.digest)
        receipt=self.d/"RATE_AMENDMENT_APPLIED_PUBLIC.json"
        expected=receipt.read_bytes()
        receipt.unlink()
        ledger=self.common.Ledger(self.d,self.policy,self.policy_sha)
        with ledger.db() as db:
            db.execute("UPDATE meta SET value='100000' WHERE key='Luna:tpm'")
        a.apply(self.d,self.amendment_path,self.digest)
        self.assertEqual(receipt.read_bytes(),expected)
        with ledger.db() as db:
            self.assertEqual(db.execute("SELECT value FROM meta WHERE key='Luna:tpm'").fetchone()[0],"100000")

    def test_original_frozen_runtime_files_unchanged(self):
        before=json.loads((HERE/"ORIGINAL_RUNTIME_BEFORE_PUBLIC.json").read_text())
        self.assertTrue(all(a.sha(HERE.parent/name)==digest for name,digest in before.items()))


def hashlib_sha(value):
    import hashlib
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    unittest.main(verbosity=2)

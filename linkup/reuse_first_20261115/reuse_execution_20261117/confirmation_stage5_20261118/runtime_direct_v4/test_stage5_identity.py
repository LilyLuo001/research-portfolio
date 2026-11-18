"""Offline exact-alias resolution tests; no network, auth, or original artifact writes."""
import contextlib
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

import stage5_common as c
import stage5_kimi_worker as w
import test_stage5_direct as direct


class IdentityTests(unittest.TestCase):
    setUp = direct.DirectTests.setUp
    tearDown = direct.DirectTests.tearDown
    frame = direct.DirectTests.frame
    fixture = direct.DirectTests.fixture
    refresh_closure = direct.DirectTests.refresh_closure
    new_ledger = direct.DirectTests.new_ledger

    def identity_fixture(self, **detail_changes):
        items, pins, prior, closure, ledger = self.fixture(
            count=3, admitted=1, state="returned_model_identity_mismatch_hold")
        body = c.encoded(w.direct_payload(prior, items[0]))
        detail = {"http_status": 200, "returned_model": "Kimi-K3.1",
                  "complete": True, "filtered": False, "usage_reported": True,
                  "finish_reasons": ["stop"], "transport_revision": "stage5-kimi-direct-azure-v3",
                  "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
                  "rate_headers": {}}
        detail.update(detail_changes)
        with ledger.db() as db:
            db.execute("UPDATE attempts SET request_sha=?,input_upper=?,tokens=?,dollars_nano=?,detail=?",
                (hashlib.sha256(body).hexdigest(), len(body)+1024, len(body)+1024+16000,
                 (len(body)+1024)*2300+16000*11500, c.encoded(detail).decode()))
        visible = prior / "results" / items[0]["case"] / "VISIBLE_RESPONSE_PRIVATE.txt"
        c.immutable(visible, b"{}")
        self.refresh_closure(prior, closure, terminal=False)
        held = ledger.latest(items[0]["case"])
        self.synthetic_known = {
            "attempt_id": held["id"], "request_sha256": held["request_sha"],
            "detail_sha256": hashlib.sha256(held["detail"].encode()).hexdigest(),
            "visible_response_sha256": c.sha(visible), "prior_closure_sha256": c.sha(closure),
            "prior_input_pins_sha256": c.sha(prior / "INPUT_PINS_PUBLIC.json"),
        }
        arm = self.d / "ARM_PUBLIC.json"
        c.save(arm, {"status": "existing_deployment_ARM_metadata_verified",
            "account": "rg-linkup", "deployment": "linkup-kimi-k3-1-pro",
            "model": {"format": "MoonshotAI", "name": "Kimi-K3.1-Pro", "version": "2026-11-04"},
            "provisioning_state": "Succeeded", "sku": {"name": "GlobalStandard", "capacity": 3000},
            "rate_limits": [{"key": "request", "renewalPeriod": 60, "count": 3000},
                            {"key": "token", "renewalPeriod": 60, "count": 3000000}],
            "endpoint": "https://rg-linkup.cognitiveservices.azure.com/",
            "new_model_calls": 0, "identity_type": "existing_ARM_service_principal"})
        return items, pins, prior, closure, ledger, arm, self.d / "IDENTITY_RESOLUTION_PUBLIC.json"

    @contextlib.contextmanager
    def pinned(self, arm):
        with patch.object(w, "APPROVED_PRIOR_CODE_SHA256", self.prior_pins["code_sha256"]),\
             patch.object(w, "ARM_IDENTITY_SHA256", c.sha(arm)),\
             patch.object(w, "KNOWN_HELD_RESPONSE", self.synthetic_known):
            yield

    def test_short_alias_needs_validated_resolution_and_exact_spelling(self):
        self.assertFalse(w.expected_model_allowed("Kimi-K3.1"))
        self.assertFalse(w.expected_model_allowed("Kimi-K3.1", {}))
        fixture = self.identity_fixture()
        items, pins, prior, closure, ledger, arm, output = fixture
        with self.pinned(arm):
            w.create_identity_resolution(prior, closure, arm, output)
            verified = w.verify_identity_resolution(output, prior_closure_sha=c.sha(closure))
            self.assertTrue(w.expected_model_allowed("Kimi-K3.1", verified))
            for unknown in ("Kimi-K3.1-extra", "kimi-k3.1", "Kimi-K3.2", "Kimi", "Kimi-K3.1 "):
                self.assertFalse(w.expected_model_allowed(unknown, verified))

    def test_projection_changes_only_state_and_preserves_source_cost_and_detail(self):
        items, pins, prior, closure, previous, arm, output = self.identity_fixture()
        before_hashes = {str(p.relative_to(prior)): c.sha(p) for p in prior.rglob("*") if p.is_file()}
        old_row = previous.latest(items[0]["case"])
        with self.pinned(arm):
            w.create_identity_resolution(prior, closure, arm, output)
            w.import_prior(self.d, prior, closure, identity_resolution_path=output)
        current = self.new_ledger()
        new_row = current.latest(items[0]["case"])
        self.assertEqual(new_row["state"], "response_saved")
        self.assertEqual({k: v for k, v in old_row.items() if k != "state"},
                         {k: v for k, v in new_row.items() if k != "state"})
        self.assertEqual(current.summary()["reserved_nano"], previous.summary()["reserved_nano"])
        self.assertEqual(current.summary()["physical_attempts"], 1)
        self.assertEqual(w.imported_contexts(current), {items[0]["row"]["context_sha256"]})
        self.assertEqual((self.d / "results" / items[0]["case"] / "VISIBLE_RESPONSE_PRIVATE.txt").read_bytes(), b"{}")
        self.assertEqual(before_hashes,
            {str(p.relative_to(prior)): c.sha(p) for p in prior.rglob("*") if p.is_file()})
        self.assertTrue(current.summary(terminal=True)["terminal_no_active_requests"])

    def test_no_resolution_keeps_identity_hold(self):
        items, pins, prior, closure, previous, arm, output = self.identity_fixture()
        with self.pinned(arm):
            w.import_prior(self.d, prior, closure)
        current = self.new_ledger()
        self.assertEqual(current.latest(items[0]["case"])["state"], "returned_model_identity_mismatch_hold")
        self.assertFalse(current.summary(terminal=True)["terminal_no_active_requests"])

    def assert_resolution_rejected(self, **changes):
        items, pins, prior, closure, previous, arm, output = self.identity_fixture(**changes)
        with self.pinned(arm), self.assertRaises(c.BoundaryError):
            w.create_identity_resolution(prior, closure, arm, output)

    def test_unknown_short_name_rejected(self):
        self.assert_resolution_rejected(returned_model="Kimi-K3.1-other")

    def test_malformed_returned_model_rejected(self):
        self.assert_resolution_rejected(returned_model={"name": "Kimi-K3.1"})

    def test_filtered_response_never_resolved(self):
        self.assert_resolution_rejected(filtered=True)

    def test_incomplete_response_never_resolved(self):
        self.assert_resolution_rejected(complete=False)

    def test_missing_usage_confirmation_never_resolved(self):
        self.assert_resolution_rejected(usage_reported=False)

    def test_nonstop_finish_never_resolved(self):
        self.assert_resolution_rejected(finish_reasons=["length"])

    def test_non200_response_never_resolved(self):
        self.assert_resolution_rejected(http_status=403)

    def test_unpinned_arm_bytes_rejected(self):
        items, pins, prior, closure, previous, arm, output = self.identity_fixture()
        with self.pinned(arm):
            changed = c.read(arm)
            changed["model"]["name"] = "Kimi-other"
            c.save(arm, changed)
            with self.assertRaises(c.BoundaryError):
                w.create_identity_resolution(prior, closure, arm, output)

    def test_changed_visible_bytes_rejected(self):
        items, pins, prior, closure, previous, arm, output = self.identity_fixture()
        (prior / "results" / items[0]["case"] / "VISIBLE_RESPONSE_PRIVATE.txt").write_bytes(b"changed")
        with self.pinned(arm), self.assertRaises(c.BoundaryError):
            w.create_identity_resolution(prior, closure, arm, output)

    def test_resolution_cannot_bind_another_closure(self):
        items, pins, prior, closure, previous, arm, output = self.identity_fixture()
        with self.pinned(arm):
            w.create_identity_resolution(prior, closure, arm, output)
            with self.assertRaises(c.BoundaryError):
                w.verify_identity_resolution(output, prior_closure_sha="0" * 64)


if __name__ == "__main__":
    unittest.main()

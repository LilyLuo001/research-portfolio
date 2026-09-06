"""Tests for source-backed numerical claims."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from spec_contract import compute_result_id
import validate_claim_ledger as ledger


SPEC = "yaxspec_v1_" + "b" * 64


class ClaimLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "result.json"
        self.source.write_text('{"coefficient":-0.1321094508}\n', encoding="utf-8")
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        selector = {"kind": "json_pointer", "pointer": "/coefficient"}
        selector_text = json.dumps(selector, sort_keys=True, separators=(",", ":"))
        result_id = compute_result_id(SPEC, "baseline_beta", digest, selector_text)
        self.results = {"schema_version": "yax-result-ledger-v1", "results": [{
            "result_id": result_id, "spec_id": SPEC, "logical_key": "baseline_beta",
            "target_key": "pooled_q5_q1", "canonical": True,
            "source_path": "result.json", "source_sha256": digest,
            "selector": selector, "value": -0.1321094508, "tolerance": 1e-12,
        }]}
        self.claims = {"schema_version": "yax-claim-ledger-v1", "claims": [{
            "claim_id": "main_baseline", "result_id": result_id,
            "target_key": "pooled_q5_q1", "canonical_target": True,
            "value": -0.1321094508, "locations": ["paper/main/working.tex"],
        }]}

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_ledgers(self):
        self.assertEqual(ledger.validate(self.results, self.claims, self.root), (1, 1))

    def test_manuscript_only_patch_fails(self):
        claims = copy.deepcopy(self.claims)
        claims["claims"][0]["value"] = -0.10
        with self.assertRaises(ledger.LedgerError):
            ledger.validate(self.results, claims, self.root)

    def test_source_tampering_fails(self):
        self.source.write_text('{"coefficient":0}\n', encoding="utf-8")
        with self.assertRaises(ledger.LedgerError):
            ledger.validate(self.results, self.claims, self.root)

    def test_duplicate_canonical_target_fails(self):
        results = copy.deepcopy(self.results)
        duplicate = copy.deepcopy(results["results"][0])
        duplicate["logical_key"] = "second"
        duplicate["result_id"] = compute_result_id(
            SPEC, "second", duplicate["source_sha256"],
            json.dumps(duplicate["selector"], sort_keys=True, separators=(",", ":")),
        )
        results["results"].append(duplicate)
        with self.assertRaises(ledger.LedgerError):
            ledger.validate(results, self.claims, self.root)


if __name__ == "__main__":
    unittest.main()

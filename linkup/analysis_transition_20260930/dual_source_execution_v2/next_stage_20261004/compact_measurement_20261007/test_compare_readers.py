#!/usr/bin/env python3

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def prediction(index):
    quote = f"At least 3 years of experience in marketing role number {index}"
    return {
        "findings": [
            {"object": "general_work", "state": "not_mentioned", "state_quote": None, "mentions": []},
            {"object": "occupation_task", "state": "positive", "state_quote": None, "mentions": [{
                "condition_mode": "prior_experience", "strength": "required",
                "qualification_scope": "unconditional", "quote": quote,
                "duration": {"kind": "minimum", "value": 3},
            }]},
            {"object": "industry_domain", "state": "not_mentioned", "state_quote": None, "mentions": []},
        ]
    }


class CompareReadersTests(unittest.TestCase):
    def test_public_counts_and_privacy(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            directory = Path(raw_dir)
            sources, manifest, left, right = [], [], [], []
            for index in range(20):
                record_id = f"private-review-id-{index}"
                text = f"Required: At least 3 years of experience in marketing role number {index}."
                sources.append({"record_id": record_id, "original_text": text})
                split = "development" if index < 4 else "heldout"
                arm = "A" if index < 12 else "B"
                manifest.append({
                    "review_id": record_id, "source_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "split": split, "arm": arm, "canonical_key": ["k", "f", index, index],
                })
                left.append(prediction(index))
                right.append(copy.deepcopy(left[-1]))
            right[4]["findings"][1]["mentions"][0]["strength"] = "preferred"

            paths = {name: directory / f"{name}.jsonl" for name in ("source", "manifest", "left", "right")}
            for name, rows in (("source", sources), ("manifest", manifest), ("left", left), ("right", right)):
                paths[name].write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            left_order, right_order = directory / "left.ORDER_PRIVATE.json", directory / "right.ORDER_PRIVATE.json"
            order_ids = [row["record_id"] for row in sources]
            left_order.write_text(json.dumps({"record_ids": order_ids}), encoding="utf-8")
            right_order.write_text(json.dumps(order_ids), encoding="utf-8")
            public, private = directory / "public.json", directory / "private.json"
            subprocess.run([
                sys.executable, str(ROOT / "compare_readers.py"),
                "--source", str(paths["source"]), "--unblind-manifest", str(paths["manifest"]),
                "--reader", f"left={paths['left']}", "--reader", f"right={paths['right']}",
                "--reader-order", f"left={left_order}", "--reader-order", f"right={right_order}",
                "--public-output", str(public), "--private-output", str(private),
            ], check=True, capture_output=True, text=True)
            result = json.loads(public.read_text())
            self.assertEqual(result["groups"]["overall"]["exact_validator"]["left"]["valid"], 20)
            metric = result["groups"]["heldout_A"]["reader_agreement_counts"]["main_estimand_presence"]
            self.assertEqual(metric["by_object"]["occupation_task"], {"agree": 7, "comparable": 8})
            self.assertNotIn("private-review-id", public.read_text())
            private_result = json.loads(private.read_text())
            self.assertEqual(private_result["records_with_disagreement_or_validation_failure"], 1)

    def test_malformed_reader_fails_closed_without_partial_counts(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            directory = Path(raw_dir)
            source = directory / "source.jsonl"
            manifest = directory / "manifest.jsonl"
            good = directory / "good.jsonl"
            bad = directory / "bad.jsonl"
            order = directory / "order.json"
            sources, keys, predictions = [], [], []
            for index in range(20):
                record_id = f"r{index}"
                text = f"Required: At least 3 years of experience in marketing role number {index}."
                sources.append({"record_id": record_id, "original_text": text})
                keys.append({"review_id": record_id, "source_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                             "split": "development" if index < 4 else "heldout",
                             "arm": "A" if index < 12 else "B"})
                predictions.append(prediction(index))
            source.write_text("".join(json.dumps(row) + "\n" for row in sources))
            manifest.write_text("".join(json.dumps(row) + "\n" for row in keys))
            good.write_text("".join(json.dumps(row) + "\n" for row in predictions))
            bad_lines = [json.dumps(row) for row in predictions]
            bad_lines[3] = "{malformed"
            bad.write_text("\n".join(bad_lines) + "\n")
            order.write_text(json.dumps([row["record_id"] for row in sources]))
            public, private = directory / "public.json", directory / "private.json"
            result = subprocess.run([
                sys.executable, str(ROOT / "compare_readers.py"), "--source", str(source),
                "--unblind-manifest", str(manifest), "--reader", f"left={good}", "--reader", f"right={bad}",
                "--reader-order", f"left={order}", "--reader-order", f"right={order}",
                "--public-output", str(public), "--private-output", str(private),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            failure = json.loads(public.read_text())
            self.assertEqual(failure["status"], "failed_precondition")
            self.assertFalse(failure["comparison_performed"])
            self.assertNotIn("groups", failure)


if __name__ == "__main__":
    unittest.main()

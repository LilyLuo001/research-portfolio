#!/usr/bin/env python3

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from export_candidates import (
    InputFailure,
    adapt_reader_outputs,
    build_public_receipt,
    export_rows,
    strict_jsonl,
    validate_override_layer,
)


TEXT = (
    "Required: At least 3 years of experience designing data pipelines. "
    "Preferred: Knowledge of retail markets."
)


def source(record_id="r1", text=TEXT):
    return {"record_id": record_id, "original_text": text}


def prediction():
    return {
        "findings": [
            {
                "object": "industry_domain",
                "state": "positive",
                "state_quote": None,
                "mentions": [{
                    "condition_mode": "knowledge_proficiency",
                    "strength": "preferred",
                    "qualification_scope": "unconditional",
                    "quote": "Knowledge of retail markets",
                    "duration": None,
                }],
            },
            {
                "object": "general_work",
                "state": "not_mentioned",
                "state_quote": None,
                "mentions": [],
            },
            {
                "object": "occupation_task",
                "state": "positive",
                "state_quote": None,
                "mentions": [{
                    "condition_mode": "prior_experience",
                    "strength": "required",
                    "qualification_scope": "unconditional",
                    "quote": "At least 3 years of experience designing data pipelines",
                    "duration": {"kind": "minimum", "value": 3},
                }],
            },
        ]
    }


def raw_row(value, record_id="r1", position=1, text=TEXT):
    return {
        "processing_position_1based": position,
        "record_id": record_id,
        "source_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "raw_output": json.dumps(value, ensure_ascii=False, separators=(",", ":")),
    }


def by_object(exported):
    return {item["object"]: item for item in exported["objects"]}


class ExportCandidateTests(unittest.TestCase):
    def test_structural_order_and_redundant_positive_quote_are_normalized(self):
        value = prediction()
        quote = value["findings"][2]["mentions"][0]["quote"]
        value["findings"][2]["state_quote"] = quote
        exported = export_rows([source()], [raw_row(value)])[0]
        self.assertEqual([item["object"] for item in exported["objects"]], [
            "general_work", "occupation_task", "industry_domain"
        ])
        task = by_object(exported)["occupation_task"]
        self.assertEqual(task["outcome_status"], "candidate")
        self.assertEqual(task["main_prior_required_unconditional"], 1)
        self.assertEqual(
            task["normalizations"][0]["code"],
            "positive_redundant_state_quote_preserved_as_auxiliary",
        )
        span = task["auxiliary_positive_state_quote_evidence"]
        self.assertEqual(TEXT[span["start"]:span["end"]], quote)

    def test_invalid_duration_preserves_mechanically_valid_binary(self):
        value = prediction()
        value["findings"][2]["mentions"][0]["duration"]["value"] = 9
        task = by_object(export_rows([source()], [raw_row(value)])[0])["occupation_task"]
        self.assertEqual(task["outcome_status"], "candidate")
        self.assertEqual(task["main_prior_required_unconditional"], 1)
        self.assertEqual(task["duration_assessments"][0]["status"], "error")
        self.assertTrue(any("not supported" in error for error in task["duration_assessments"][0]["errors"]))

    def test_bad_quote_isolates_only_affected_object(self):
        value = prediction()
        value["findings"][2]["mentions"][0]["quote"] = "missing exact quote"
        objects = by_object(export_rows([source()], [raw_row(value)])[0])
        self.assertEqual(objects["occupation_task"]["outcome_status"], "error")
        self.assertIsNone(objects["occupation_task"]["main_prior_required_unconditional"])
        self.assertEqual(objects["general_work"]["outcome_status"], "candidate")
        self.assertEqual(objects["general_work"]["main_prior_required_unconditional"], 0)
        self.assertEqual(objects["industry_domain"]["outcome_status"], "candidate")

    def test_missing_or_out_of_order_rows_fail_closed(self):
        sources = [source("r1"), source("r2")]
        with self.assertRaisesRegex(InputFailure, "counts differ"):
            export_rows(sources, [raw_row(prediction(), "r1", 1)])
        rows = [
            raw_row(prediction(), "r2", 1),
            raw_row(prediction(), "r1", 2),
        ]
        with self.assertRaises(InputFailure) as caught:
            export_rows(sources, rows)
        self.assertEqual(caught.exception.code, "record_order_mismatch")

    def test_wrong_hash_quarantines_only_affected_row(self):
        sources = [source("r1"), source("r2")]
        first = raw_row(prediction(), "r1", 1)
        first["source_text_sha256"] = "0" * 64
        second = raw_row(prediction(), "r2", 2)
        exported = export_rows(sources, [first, second])
        self.assertEqual(exported[0]["row_status"], "error")
        self.assertTrue(all(
            obj["outcome_status"] == "error" and obj["main_prior_required_unconditional"] is None
            for obj in exported[0]["objects"]
        ))
        self.assertEqual(exported[1]["row_status"], "candidate")

    def test_malformed_jsonl_is_never_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text('{"record_id":"r1"}\nnot-json\n', encoding="utf-8")
            with self.assertRaises(InputFailure) as caught:
                strict_jsonl(path, "source")
            self.assertEqual(caught.exception.code, "source_invalid_json")

    def test_adapter_preserves_reader_line_and_requires_exact_order(self):
        raw_line = ' {"findings": []} '
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            predictions = directory / "predictions.jsonl"
            order = directory / "order.json"
            predictions.write_text(raw_line + "\n", encoding="utf-8")
            order.write_text('["r1"]\n', encoding="utf-8")
            wrappers = adapt_reader_outputs([source()], predictions, order)
            self.assertEqual(wrappers[0]["raw_output"], raw_line)
            self.assertEqual(
                wrappers[0]["raw_output_line_sha256"],
                hashlib.sha256(raw_line.encode()).hexdigest(),
            )
            order.write_text('["wrong"]\n', encoding="utf-8")
            with self.assertRaises(InputFailure) as caught:
                adapt_reader_outputs([source()], predictions, order)
            self.assertEqual(caught.exception.code, "adapter_order_mismatch")

    def test_public_receipt_has_no_private_row_content_and_keeps_denominator(self):
        exported = export_rows([source()], [raw_row(prediction())])
        receipt = build_public_receipt(exported, "a" * 64, "b" * 64)
        encoded = json.dumps(receipt)
        self.assertNotIn("r1", encoded)
        self.assertNotIn("At least", encoded)
        for object_name in ("general_work", "occupation_task", "industry_domain"):
            self.assertEqual(receipt["objects"][object_name]["eligible_denominator_rows"], 1)

    def test_external_override_is_received_but_not_applied(self):
        source_sha = hashlib.sha256(TEXT.encode()).hexdigest()
        override = {
            "override_version": "review-v1",
            "record_id": "r1",
            "source_text_sha256": source_sha,
            "object": "occupation_task",
            "field": "main_prior_required_unconditional",
            "corrected_value": 0,
            "reason": "Reviewer found the condition was not applicant-facing.",
            "source_quote": "At least 3 years of experience designing data pipelines",
        }
        receipt = validate_override_layer([override], [source()])
        self.assertEqual(receipt["status"], "received_unapplied")
        self.assertEqual(receipt["overrides"][0]["application_status"], "received_unapplied")

    def test_genuine_audit_ampersand_mismatch_remains_object_error(self):
        audit = Path(__file__).resolve().parent / "private" / "batch001" / "audit"
        sources = strict_jsonl(audit / "SOURCE6_PRIVATE.jsonl", "source")
        wrappers = adapt_reader_outputs(
            sources,
            audit / "PREDICTIONS_RAW_PRIVATE.jsonl",
            audit / "ORDER_PRIVATE.json",
        )
        exported = export_rows(sources, wrappers)
        task = by_object(exported[-1])["occupation_task"]
        self.assertEqual(task["outcome_status"], "error")
        self.assertIsNone(task["main_prior_required_unconditional"])
        self.assertTrue(any("not an exact source substring" in error for error in task["errors"]))
        self.assertIn("Training & Development", exported[-1]["raw_output"])
        self.assertIn("Training &amp; Development", sources[-1]["original_text"])


if __name__ == "__main__":
    unittest.main()

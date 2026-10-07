#!/usr/bin/env python3

import copy
import hashlib
import json
import unittest

from export_candidates import export_rows
from finalize_batch import InputFailure, build_receipt, finalize_rows


TEXT = "Required: At least 3 years of experience designing data pipelines."


def source():
    return {"record_id": "r1", "original_text": TEXT}


def prediction():
    return {
        "findings": [
            {"object": "general_work", "state": "not_mentioned", "state_quote": None, "mentions": []},
            {"object": "occupation_task", "state": "positive", "state_quote": None, "mentions": [{
                "condition_mode": "prior_experience",
                "strength": "required",
                "qualification_scope": "unconditional",
                "quote": "At least 3 years of experience designing data pipelines",
                "duration": {"kind": "minimum", "value": 9},
            }]},
            {"object": "industry_domain", "state": "not_mentioned", "state_quote": None, "mentions": []},
        ]
    }


def candidate():
    raw_output = json.dumps(prediction(), separators=(",", ":"))
    wrapper = {
        "processing_position_1based": 1,
        "record_id": "r1",
        "source_text_sha256": hashlib.sha256(TEXT.encode()).hexdigest(),
        "raw_output": raw_output,
    }
    return export_rows([source()], [wrapper])[0]


def decision():
    return {
        "record_id": "r1",
        "source_text_sha256": hashlib.sha256(TEXT.encode()).hexdigest(),
        "object": "occupation_task",
        "reason": "semantic_scope_correction",
        "evidence_quotes": ["At least 3 years of experience designing data pipelines"],
        "main_override": {"value": 0, "status": "candidate"},
        "duration_overrides": [{
            "mention_index_0based": 0,
            "status": "unknown",
            "reason": "duration_binding_unresolved",
        }],
        "ancillary_notes": ["Explicit root adjudication; raw label retained."],
    }


class FinalizeBatchTests(unittest.TestCase):
    def test_adjudication_changes_only_derived_fields_and_preserves_before_and_raw(self):
        original = candidate()
        final_rows, validated = finalize_rows([source()], [original], [decision()], expected_rows=1)
        final = final_rows[0]
        task = next(item for item in final["objects"] if item["object"] == "occupation_task")
        before_task = next(
            item for item in final["candidate_before_adjudication"]["objects"]
            if item["object"] == "occupation_task"
        )
        self.assertEqual(before_task["main_prior_required_unconditional"], 1)
        self.assertEqual(before_task["duration_assessments"][0]["status"], "error")
        self.assertEqual(task["main_prior_required_unconditional"], 0)
        self.assertEqual(task["outcome_status"], "candidate")
        self.assertEqual(task["duration_assessments"][0]["status"], "unknown")
        self.assertEqual(final["raw_output"], original["raw_output"])
        self.assertEqual(final["raw_output_sha256"], original["raw_output_sha256"])
        receipt = build_receipt(final_rows, validated, "a", "b", "c")
        self.assertEqual(receipt["eligible_object_fields"], 3)
        self.assertEqual(receipt["changed_main_count"], 1)
        self.assertNotIn("r1", json.dumps(receipt))
        self.assertNotIn("At least", json.dumps(receipt))

    def test_invalid_or_duplicate_decisions_fail_closed(self):
        original = candidate()
        bad_quote = decision()
        bad_quote["evidence_quotes"] = ["not in source"]
        with self.assertRaises(InputFailure) as caught:
            finalize_rows([source()], [original], [bad_quote], expected_rows=1)
        self.assertEqual(caught.exception.code, "decision_quote_not_exact")

        duplicate = decision()
        with self.assertRaises(InputFailure) as caught:
            finalize_rows([source()], [copy.deepcopy(original)], [decision(), duplicate], expected_rows=1)
        self.assertEqual(caught.exception.code, "decision_duplicate_object")


if __name__ == "__main__":
    unittest.main()

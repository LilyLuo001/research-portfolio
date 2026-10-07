#!/usr/bin/env python3

import copy
import unittest

from expand_and_validate import validate_and_expand


SOURCE_TEXT = (
    "Required: At least 3 years of experience in marketing roles. "
    "Preferred: Knowledge of retail markets."
)


def valid_prediction():
    return {
        "findings": [
            {"object": "general_work", "state": "not_mentioned", "state_quote": None, "mentions": []},
            {"object": "occupation_task", "state": "positive", "state_quote": None, "mentions": [{
                "condition_mode": "prior_experience", "strength": "required",
                "qualification_scope": "unconditional",
                "quote": "At least 3 years of experience in marketing roles",
                "duration": {"kind": "minimum", "value": 3}
            }]},
            {"object": "industry_domain", "state": "positive", "state_quote": None, "mentions": [{
                "condition_mode": "knowledge_proficiency", "strength": "preferred",
                "qualification_scope": "unconditional", "quote": "Knowledge of retail markets",
                "duration": None
            }]}
        ]
    }


class CompactValidatorTests(unittest.TestCase):
    def test_valid_output_gets_metadata_and_offsets(self):
        record, errors = validate_and_expand(valid_prediction(), {"record_id": "r1", "original_text": SOURCE_TEXT})
        self.assertEqual(errors, [])
        self.assertEqual(record["record_id"], "r1")
        evidence = record["findings"][1]["mentions"][0]["evidence"]
        self.assertEqual(SOURCE_TEXT[evidence["start"]:evidence["end"]], evidence["text"])

    def test_repeated_quote_is_rejected(self):
        prediction = valid_prediction()
        prediction["findings"][1]["mentions"][0]["quote"] = "experience"
        record, errors = validate_and_expand(
            prediction,
            {"record_id": "r2", "original_text": "experience in sales; experience in marketing"},
        )
        self.assertIsNone(record)
        self.assertTrue(any("occurs 2 times" in error for error in errors))

    def test_missing_quote_is_rejected(self):
        prediction = valid_prediction()
        prediction["findings"][2]["mentions"][0]["quote"] = "Knowledge of a missing market"
        record, errors = validate_and_expand(prediction, {"record_id": "r3", "original_text": SOURCE_TEXT})
        self.assertIsNone(record)
        self.assertTrue(any("not an exact source substring" in error for error in errors))

    def test_maximum_duration_is_unsupported(self):
        prediction = valid_prediction()
        prediction["findings"][1]["mentions"][0]["quote"] = "Up to 3 years of experience in marketing roles"
        source = SOURCE_TEXT.replace("At least 3 years of experience in marketing roles", "Up to 3 years of experience in marketing roles")
        record, errors = validate_and_expand(prediction, {"record_id": "r4", "original_text": source})
        self.assertIsNone(record)
        self.assertTrue(any("maximum-only duration is unsupported" in error for error in errors))

    def test_duration_omission_is_left_for_semantic_review(self):
        prediction = copy.deepcopy(valid_prediction())
        prediction["findings"][1]["mentions"][0]["duration"] = None
        record, errors = validate_and_expand(prediction, {"record_id": "r5", "original_text": SOURCE_TEXT})
        self.assertEqual(errors, [])
        self.assertIsNotNone(record)

    def test_bare_duration_quote_is_rejected(self):
        prediction = copy.deepcopy(valid_prediction())
        prediction["findings"][1]["mentions"][0]["quote"] = "At least 3 years"
        record, errors = validate_and_expand(prediction, {"record_id": "r6", "original_text": SOURCE_TEXT})
        self.assertIsNone(record)
        self.assertTrue(any("quote cannot be a bare duration" in error for error in errors))

    def test_infinitive_to_is_not_a_range_cue(self):
        prediction = copy.deepcopy(valid_prediction())
        quote = "7 years of experience to lead projects"
        prediction["findings"][1]["mentions"][0]["quote"] = quote
        prediction["findings"][1]["mentions"][0]["duration"] = {"kind": "stated_unspecified", "value": 7}
        record, errors = validate_and_expand(prediction, {"record_id": "r7", "original_text": SOURCE_TEXT.replace("At least 3 years of experience in marketing roles", quote)})
        self.assertEqual(errors, [])
        self.assertIsNotNone(record)

    def test_education_substitution_years_do_not_force_scalar_duration(self):
        prediction = copy.deepcopy(valid_prediction())
        quote = "Bachelor's degree or 4 years of equivalent experience in marketing roles"
        mention = prediction["findings"][1]["mentions"][0]
        mention["quote"] = quote
        mention["qualification_scope"] = "education_substitution"
        mention["duration"] = None
        record, errors = validate_and_expand(prediction, {"record_id": "r8", "original_text": SOURCE_TEXT.replace("At least 3 years of experience in marketing roles", quote)})
        self.assertEqual(errors, [])
        self.assertIsNotNone(record)


if __name__ == "__main__":
    unittest.main()

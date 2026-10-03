from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


MEASUREMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MEASUREMENT))
from validate_extraction import SCHEMA, SCHEMA_VALIDATOR, validate_record  # noqa: E402
from run_local import command_cost, command_prepare  # noqa: E402
from expand_compact_labels import expand_record, locate_quote  # noqa: E402


TEXT = (
    "At least 3 years of software engineering experience or a bachelor's degree. "
    "Proficiency in Python. Use GitHub Copilot to write application code. "
    "No prior healthcare industry experience required."
)


def span(span_id: str, quote: str) -> dict:
    start = TEXT.index(quote)
    return {"span_id": span_id, "start": start, "end": start + len(quote), "text": quote}


def finding(obj: str, state: str, mentions: list | None = None, state_evidence: list | None = None) -> dict:
    return {
        "object": obj, "state": state,
        "state_applicant_context": state in {"explicit_positive", "explicit_negative"},
        "state_evidence": state_evidence or [], "mentions": mentions or [], "note": None
    }


def valid_record() -> dict:
    occupation_quote = "At least 3 years of software engineering experience"
    tool_quote = "Proficiency in Python"
    industry_quote = "No prior healthcare industry experience required"
    ai_quote = "Use GitHub Copilot to write application code"
    return {
        "schema_version": "linkup_measurement_v1.0.0",
        "prompt_version": "linkup_extraction_prompt_v1.0.0",
        "record_id": "synthetic-001",
        "source_text_sha256": hashlib.sha256(TEXT.encode()).hexdigest(),
        "record_text_state": "readable",
        "experience_findings": [
            finding("general_work", "not_mentioned"),
            finding("occupation_task", "explicit_positive", [{
                "mention_id": "exp-occupation-1", "condition_mode": "prior_experience", "strength": "required",
                "applicant_context": True, "branch_id": "experience-option", "branch_relation": "or", "alternative_group": "experience-or-degree",
                "evidence": [span("occ-span", occupation_quote)],
                "duration": {"unit": "years", "interpretation": "minimum", "stated_value": 3, "lower": 3, "upper": None, "evidence_span_id": "occ-span"}
            }]),
            finding("industry_domain", "explicit_negative", state_evidence=[span("industry-neg", industry_quote)]),
            finding("specific_tool", "explicit_positive", [{
                "mention_id": "exp-tool-1", "condition_mode": "proficiency", "strength": "required", "applicant_context": True,
                "branch_id": "tool", "branch_relation": "standalone", "alternative_group": None,
                "evidence": [span("tool-span", tool_quote)], "duration": None
            }]),
        ],
        "technology_findings": [{
            "finding_id": "tech-1", "state": "explicit_positive", "technology_class": "generative_ai", "technology_role": "use_operate",
            "ai_role_basis": "use_ai_to_write_software", "applicant_context": True, "evidence": [span("ai-span", ai_quote)], "note": None
        }],
        "record_note": None,
    }


class MeasurementValidationTest(unittest.TestCase):
    def test_schema_is_real_and_valid_fixture_passes(self) -> None:
        self.assertEqual([], list(SCHEMA_VALIDATOR.iter_errors(valid_record())))
        self.assertEqual([], validate_record(valid_record(), TEXT, "synthetic-001"))

    def test_bad_offset_is_rejected(self) -> None:
        record = valid_record()
        record["experience_findings"][1]["mentions"][0]["evidence"][0]["start"] += 1
        errors = validate_record(record, TEXT)
        self.assertTrue(any("offsets do not reproduce" in error for error in errors), errors)

    def test_unbound_years_are_rejected(self) -> None:
        record = valid_record()
        record["experience_findings"][1]["mentions"][0]["duration"]["evidence_span_id"] = "other-branch"
        errors = validate_record(record, TEXT)
        self.assertTrue(any("not bound" in error for error in errors), errors)

    def test_using_ai_to_write_software_cannot_be_labeled_ai_development(self) -> None:
        record = valid_record()
        record["technology_findings"][0]["technology_role"] = "develop_train"
        errors = validate_record(record, TEXT)
        self.assertTrue(any("requires technology_role=use_operate" in error for error in errors), errors)

    def test_negative_and_unresolved_cannot_be_zero_filled(self) -> None:
        for index, state in ((2, "explicit_negative"), (0, "unresolved")):
            with self.subTest(state=state):
                record = valid_record()
                record["experience_findings"][index]["state"] = state
                record["experience_findings"][index]["state_applicant_context"] = state == "explicit_negative"
                record["experience_findings"][index]["mentions"] = [{
                    "mention_id": f"zero-{state}", "condition_mode": "prior_experience", "strength": "unspecified", "applicant_context": True,
                    "branch_id": "fake-zero", "branch_relation": "standalone", "alternative_group": None,
                    "evidence": [span(f"zero-span-{state}", "No prior healthcare industry experience required")],
                    "duration": {"unit": "years", "interpretation": "exact", "stated_value": 0, "lower": 0, "upper": 0, "evidence_span_id": f"zero-span-{state}"}
                }]
                errors = validate_record(record, TEXT)
                self.assertTrue(any("cannot carry positive mentions or duration" in error for error in errors), errors)

    def test_local_prepare_and_cost_receipt_do_not_claim_a_model_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.jsonl"
            source_rows = [
                {"JOB_HASH": f"job-{number}", "SOURCE_FILE": "source.parquet", "SOURCE_ROW": number,
                 "RECORD_SOURCE_ROW": number, "original_text": TEXT + f" Row {number}."}
                for number in range(2)
            ]
            source.write_text("".join(json.dumps(row) + "\n" for row in source_rows), encoding="utf-8")
            output = root / "private-pack"
            result = command_prepare(Namespace(
                mode="development", input=source, output_dir=output, expected_count=2,
                comparison_manifest=None, evaluation_lock_receipt=None, text_column=None
            ))
            self.assertEqual(0, result)
            prepare_receipt = json.loads((output / "development_pack_receipt.json").read_text())
            self.assertFalse(prepare_receipt["claims"]["model_labels_generated"])
            self.assertEqual(0, prepare_receipt["counts"]["comparison_records"])
            self.assertIsNone(prepare_receipt["outputs"]["comparison_path"])
            cost_path = root / "cost.json"
            result = command_cost(Namespace(
                source=output / "development_2.pack.jsonl", receipt=cost_path,
                characters_per_token=4.0, scale_count=40300
            ))
            self.assertEqual(0, result)
            cost = json.loads(cost_path.read_text())
            self.assertIsNone(cost["billing"]["billed_cost"])
            self.assertFalse(cost["production_l3_started"])

    def test_evaluation_without_lock_receipt_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "evaluation.jsonl"
            source.write_text(json.dumps({
                "JOB_HASH": "eval-1", "SOURCE_FILE": "source.parquet", "SOURCE_ROW": 1,
                "RECORD_SOURCE_ROW": 1, "original_text": TEXT
            }) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "evaluation preparation refused"):
                command_prepare(Namespace(
                    mode="evaluation", input=source, output_dir=root / "eval-pack", expected_count=1,
                    comparison_manifest=None, evaluation_lock_receipt=None, text_column=None
                ))

    def test_config80_uses_l1_manifest_order_without_redrawing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "development.csv"
            manifest = root / "config80.json"
            rows = [
                {"JOB_HASH": f"job-{number:02d}", "SOURCE_FILE": "source.parquet", "SOURCE_ROW": number,
                 "RECORD_SOURCE_ROW": number, "original_text": TEXT + f" {number}"}
                for number in range(80)
            ]
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            manifest.write_text(json.dumps({"selected": [
                {"private_key": json.dumps([row[key] for key in ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")], separators=(",", ":"))}
                for row in reversed(rows)
            ]}), encoding="utf-8")
            output = root / "private-pack"
            self.assertEqual(0, command_prepare(Namespace(
                mode="development", input=source, output_dir=output, expected_count=80,
                comparison_manifest=manifest, evaluation_lock_receipt=None, text_column=None
            )))
            comparison = (output / "development_config_compare_80.pack.jsonl").read_text().splitlines()
            self.assertEqual("job-79", json.loads(comparison[0])["record_id"])
            self.assertEqual("job-00", json.loads(comparison[-1])["record_id"])

    def test_compact_expansion_fills_hash_offsets_and_binding_only(self) -> None:
        formal = valid_record()
        compact = {
            "record_id": formal["record_id"], "record_text_state": formal["record_text_state"],
            "record_note": formal["record_note"], "experience_findings": [], "technology_findings": []
        }
        for finding in formal["experience_findings"]:
            short = {key: value for key, value in finding.items() if key not in {"state_evidence", "mentions"}}
            short["quote"] = finding["state_evidence"][0]["text"] if finding["state_evidence"] else None
            short["mentions"] = []
            for mention in finding["mentions"]:
                item = {key: value for key, value in mention.items() if key != "evidence"}
                item["quote"] = mention["evidence"][0]["text"]
                if item["duration"] is not None:
                    item["duration"] = {key: value for key, value in item["duration"].items() if key != "evidence_span_id"}
                short["mentions"].append(item)
            compact["experience_findings"].append(short)
        for finding in formal["technology_findings"]:
            short = {key: value for key, value in finding.items() if key != "evidence"}
            short["quote"] = finding["evidence"][0]["text"] if finding["evidence"] else None
            compact["technology_findings"].append(short)
        expanded = expand_record(compact, TEXT)
        self.assertEqual([], validate_record(expanded, TEXT, formal["record_id"]))
        self.assertEqual(formal["source_text_sha256"], expanded["source_text_sha256"])

    def test_repeated_quote_requires_occurrence(self) -> None:
        with self.assertRaisesRegex(ValueError, "supply zero-based occurrence"):
            locate_quote("Python then Python", "Python", "span")


if __name__ == "__main__":
    unittest.main()

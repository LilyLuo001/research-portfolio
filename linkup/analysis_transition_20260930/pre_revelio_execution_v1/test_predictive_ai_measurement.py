#!/usr/bin/env python3
"""Synthetic regression evidence for the frozen predictive-AI limitation."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def frozen_modules():
    for base in (ROOT, ROOT / "cleaning_pipeline_20260928" / "source_snapshot"):
        parser = base / "stage_c_v6" / "requirement_candidates.py"
        enrichment = base / "stage_c_release_v1" / "enrichment.py"
        if parser.is_file() and enrichment.is_file():
            return parser, enrichment
    raise FileNotFoundError("frozen V6/release-v1 modules not found in project or Git snapshot")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PARSER_PATH, ENRICHMENT_PATH = frozen_modules()
PARSER = load(PARSER_PATH, "v6_predictive_limit")
ENRICH = load(ENRICHMENT_PATH, "enrich_predictive_limit")


class PredictiveAIMeasurementTests(unittest.TestCase):
    def row(self, text):
        output = ENRICH.enrich(PARSER.extract(text))
        return next(item for item in output["technology_evidence"] if item["technology_name"] == "predictive_model")

    def test_explicit_develop_is_not_applicant_context_without_v6_overlap(self):
        row = self.row("Required: develop predictive models.")
        self.assertEqual((row["technology_type"], row["role"], row["binding_status"]),
                         ("predictive_ai", "develop", "explicit"))
        self.assertFalse(row["applicant_context_candidate"])

    def test_explicit_use_is_not_applicant_context_without_v6_overlap(self):
        row = self.row("Required: experience with predictive models.")
        self.assertEqual((row["technology_type"], row["role"], row["binding_status"]),
                         ("predictive_ai", "use", "explicit"))
        self.assertFalse(row["applicant_context_candidate"])


if __name__ == "__main__":
    unittest.main()

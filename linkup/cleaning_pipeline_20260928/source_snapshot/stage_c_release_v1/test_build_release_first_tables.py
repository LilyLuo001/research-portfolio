#!/usr/bin/env python3
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import build_release_first_tables as tables
import lean_writer


def base_key(tag, row):
    return {"JOB_HASH": "job-" + tag, "SOURCE_FILE": "source-" + tag,
            "SOURCE_ROW": row, "RECORD_SOURCE_ROW": row + 100}


def typed_row(schema, values):
    row = {field.name: None for field in schema}
    row.update(values)
    return row


class FirstTablesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_shard(self, tag, ads, experience=(), technology=(), audit=(), raw_extra=3):
        shard = self.root / ("shard-" + tag)
        chunk = shard / "chunk_00000"
        chunk.mkdir(parents=True)
        for name, schema, rows in (
                ("ad_status", lean_writer.AD_SCHEMA, ads),
                ("experience", lean_writer.EXP_SCHEMA, experience),
                ("technology", lean_writer.TECH_SCHEMA, technology),
                ("v6_audit", lean_writer.AUDIT_SCHEMA, audit)):
            pq.write_table(pa.Table.from_pylist(list(rows), schema=schema), chunk / (name + ".parquet"))
        dispositions = {
            "matched_usa_canonical": len(ads),
            "matched_usa_duplicate_quarantine": 1,
            "matched_non_usa": 1,
            "matched_country_unknown": 0,
            "record_unmatched": raw_extra - 2,
        }
        receipt = self.root / ("receipt-" + tag + ".json")
        receipt.write_text(json.dumps({"status": "complete", "shard_id": tag,
            "accounting": {"raw_rows": len(ads) + raw_extra,
                           "canonical_usa_rows": len(ads),
                           "disposition_counts": dispositions,
                           "row_conservation": True}}))
        return shard, receipt

    def test_ad_dedup_denominators_period_and_merge_conservation(self):
        k1, k2, k3, k4 = (base_key("a", i) for i in range(4))
        ads = [
            typed_row(lean_writer.AD_SCHEMA, {**k1, "CREATED": datetime(2026, 5, 1),
                "DESCRIPTION_EMPTY": False, "PARSE_ERROR": False,
                "INPUT_EVIDENCE_TRUNCATED": False, "ENRICHMENT_INCOMPLETE": False,
                "EXPERIENCE_EVIDENCE_COUNT": 2, "TECHNOLOGY_EVIDENCE_COUNT": 2,
                "V6_AUDIT_EVIDENCE_COUNT": 2}),
            typed_row(lean_writer.AD_SCHEMA, {**k2, "CREATED": datetime(2026, 7, 15),
                "DESCRIPTION_EMPTY": True, "PARSE_ERROR": False,
                "INPUT_EVIDENCE_TRUNCATED": False, "ENRICHMENT_INCOMPLETE": False,
                "EXPERIENCE_EVIDENCE_COUNT": 0, "TECHNOLOGY_EVIDENCE_COUNT": 0,
                "V6_AUDIT_EVIDENCE_COUNT": 0}),
            typed_row(lean_writer.AD_SCHEMA, {**k3, "CREATED": None,
                "DESCRIPTION_EMPTY": False, "PARSE_ERROR": True,
                "INPUT_EVIDENCE_TRUNCATED": False, "ENRICHMENT_INCOMPLETE": True,
                "EXPERIENCE_EVIDENCE_COUNT": 0, "TECHNOLOGY_EVIDENCE_COUNT": 0,
                "V6_AUDIT_EVIDENCE_COUNT": 0}),
            typed_row(lean_writer.AD_SCHEMA, {**k4, "CREATED": datetime(2025, 12, 1),
                "DESCRIPTION_EMPTY": False, "PARSE_ERROR": False,
                "INPUT_EVIDENCE_TRUNCATED": False, "ENRICHMENT_INCOMPLETE": False,
                "EXPERIENCE_EVIDENCE_COUNT": 0, "TECHNOLOGY_EVIDENCE_COUNT": 0,
                "V6_AUDIT_EVIDENCE_COUNT": 0}),
        ]
        exp_values = {"OBJECT_TYPE": "software", "BINDING_STATUS": "explicit_local_relation",
                      "RELATION": "and", "OPTIONAL": False, "REQUIREMENT_STRENGTH": "required",
                      "CONTEXT": "qualification", "APPLICANT_CONTEXT_CANDIDATE": True}
        tech_values = {"TECHNOLOGY_TYPE": "traditional_software", "ROLE": "use",
                       "BINDING_STATUS": "candidate_local_relation", "TECHNOLOGY_AMBIGUITY": None,
                       "CONTEXT": "qualification", "APPLICANT_CONTEXT_CANDIDATE": True}
        exp = [typed_row(lean_writer.EXP_SCHEMA, {**k1, **exp_values, "EVIDENCE_ORDINAL": i}) for i in (0, 1)]
        tech = [typed_row(lean_writer.TECH_SCHEMA, {**k1, **tech_values, "EVIDENCE_ORDINAL": i}) for i in (0, 1)]
        audit = [
            typed_row(lean_writer.AUDIT_SCHEMA, {**k1, "EVIDENCE_ORDINAL": 0,
                "MODULE": "education", "NO_EXPERIENCE_EXPLICIT": False}),
            typed_row(lean_writer.AUDIT_SCHEMA, {**k1, "EVIDENCE_ORDINAL": 1,
                "MODULE": "experience", "NO_EXPERIENCE_EXPLICIT": True}),
        ]
        shard1, receipt1 = self.make_shard("one", ads, exp, tech, audit)
        first = tables.shard_summary(shard1, receipt1)
        self.assertEqual(first["funnel"]["canonical_ad_status"], 4)
        self.assertEqual(first["funnel"]["usable_nonempty_complete_parse"], 2)
        self.assertEqual(first["funnel"]["empty_description"], 1)
        self.assertEqual(first["funnel"]["parse_error"], 1)
        self.assertEqual(first["funnel"]["enrichment_incomplete"], 1)
        self.assertEqual(first["funnel"]["audit_only_education_candidate"], 1)
        self.assertEqual(first["funnel"]["audit_only_no_experience_phrase_candidate"], 1)
        evidence = [r for r in first["technology_experience"]
                    if r["ROW_KIND"] == "evidence_cross"
                    and r["TECHNOLOGY_TYPE"] == "traditional_software"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["ADS"], 1)  # repeated evidence does not repeat the ad
        self.assertTrue(any(r["TECHNOLOGY_TYPE"] == "no_detection"
                            for r in first["technology_experience"]))
        periods = {(r["CREATED_QUARTER"], r["ANALYSIS_PERIOD"])
                   for r in first["created_queue"]}
        self.assertIn(("2026Q2", "complete_queues_through_2026Q2"), periods)
        self.assertIn(("2026Q3", "2026Q3_partial"), periods)
        self.assertIn(("unknown", "date_unknown"), periods)

        k5 = base_key("b", 0)
        ad5 = typed_row(lean_writer.AD_SCHEMA, {**k5, "CREATED": datetime(2026, 6, 30),
            "DESCRIPTION_EMPTY": False, "PARSE_ERROR": False,
            "INPUT_EVIDENCE_TRUNCATED": False, "ENRICHMENT_INCOMPLETE": False,
            "EXPERIENCE_EVIDENCE_COUNT": 0, "TECHNOLOGY_EVIDENCE_COUNT": 0,
            "V6_AUDIT_EVIDENCE_COUNT": 0})
        shard2, receipt2 = self.make_shard("two", [ad5])
        s1, s2 = self.root / "one.json", self.root / "two.json"
        s1.write_text(json.dumps(first)); s2.write_text(json.dumps(tables.shard_summary(shard2, receipt2)))
        merged = tables.merge_summaries([s1, s2])
        self.assertEqual(merged["funnel"]["canonical_ad_status"], 5)
        self.assertEqual(merged["funnel"]["raw_input_rows"], 11)
        self.assertEqual(merged["funnel"]["matched_usa_unique_canonical_rows"], 5)
        output = self.root / "merged"
        tables.write_merged(output, merged)
        self.assertTrue((output / "CONSERVATION_REPORT.json").is_file())
        with self.assertRaises(RuntimeError):
            tables.merge_summaries([s1, s1])


if __name__ == "__main__":
    unittest.main()

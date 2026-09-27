import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from export_research_candidates import export
from requirement_candidates import extract


class ResearchCandidateExporterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.parser = Path(__file__).with_name("requirement_candidates.py")

    def tearDown(self):
        self.temp.cleanup()

    def _write_fixture(self, duplicate=False):
        texts = {
            "no_candidate": "Friendly workplace near public transit.",
            "explicit_none": "Minimum qualifications:\nNo prior experience is required.",
            "work_alternative": "Minimum Qualifications:\nBachelor's degree or five years of work experience required.",
            "credential_equivalent": "Required Qualifications:\nHigh school diploma or equivalent required.\nBenefits follow.",
            "truncated": "\n".join("Python SQL Excel Tableau Slack" for _ in range(30)),
        }
        sample_rows = []
        candidate_rows = []
        for source_row, (name, text) in enumerate(texts.items(), 1):
            job_hash = (name.encode().hex() + "0" * 32)[:32]
            payload = extract(text)
            if name == "credential_equivalent":
                # Reproduce the v3 payload shape where the parser strips the
                # claimed scope text but retains adjacent whitespace in bounds.
                item = next(x for x in payload["evidence"] if x.get("equivalent_credential"))
                normalized = payload["normalized_text"]
                start = item["qualification_scope_start"]
                end = item["qualification_scope_end"]
                self.assertTrue(start > 0 and normalized[start - 1].isspace())
                normalized = normalized[:end] + " " + normalized[end:]
                payload["normalized_text"] = normalized
                payload["normalized_text_fingerprint_sha256"] = hashlib.sha256(normalized.encode()).hexdigest()
                item["qualification_scope_start"] = start - 1
                item["qualification_scope_end"] = end + 1
            sample_rows.append({
                "JOB_HASH": job_hash, "SOURCE_FILE": "fixture.parquet", "SOURCE_ROW": source_row,
                "RECORD_SOURCE_ROW": source_row + 100, "COUNTRY": "USA", "COUNTRY_GROUP": "USA",
                "STATE": "CA", "COHORT": "fixture", "CREATED": None, "LAST_UPDATED": None,
                "LAST_CHECKED": None, "DELETE_DATE": None, "BOUNDARY_STATUS": "unknown",
                "JAN01_STATUS": "unknown", "SAMPLE_HASH": "sample-" + name,
            })
            candidate_rows.append({
                "JOB_HASH": job_hash, "SOURCE_FILE": "fixture.parquet", "SOURCE_ROW": source_row,
                "COUNTRY_GROUP": "USA", "COHORT": "fixture",
                "RAW_SHA256": payload["source_fingerprint_sha256"],
                "NORMALIZED_SHA256": payload["normalized_text_fingerprint_sha256"],
                "STATUS": "unvalidated_candidate", "CANDIDATE_JSON": json.dumps(payload),
            })
        if duplicate:
            sample_rows.append(copy.deepcopy(sample_rows[0]))
            candidate_rows.append(copy.deepcopy(candidate_rows[0]))
        sample = self.root / "sample.parquet"
        candidates = self.root / "candidates.parquet"
        pq.write_table(pa.Table.from_pylist(sample_rows), sample)
        pq.write_table(pa.Table.from_pylist(candidate_rows), candidates)
        return sample, candidates

    def test_preserves_empty_negation_relations_and_truncation(self):
        sample, candidates = self._write_fixture()
        out = self.root / "out"
        receipt = export(sample, candidates, out, self.parser)
        self.assertEqual(receipt["source_row_count"], 5)
        self.assertTrue((out / "COMPLETE.json").is_file())
        self.assertTrue(any("AND/OR graph" in note for note in receipt["known_limitations"]))

        ads = pq.read_table(out / "ad_candidate_status.parquet").to_pylist()
        by_hash = {row["JOB_HASH"]: row for row in ads}
        no_candidate = by_hash[("no_candidate".encode().hex() + "0" * 32)[:32]]
        self.assertEqual(no_candidate["EXPERIENCE_STATUS"], "no_candidate")
        self.assertFalse(receipt["no_candidate_is_no_requirement"])
        explicit = by_hash[("explicit_none".encode().hex() + "0" * 32)[:32]]
        self.assertEqual(explicit["EXPERIENCE_CANDIDATE_COUNT"], 1)
        truncated = by_hash[("truncated".encode().hex() + "0" * 32)[:32]]
        self.assertTrue(truncated["EVIDENCE_TRUNCATED"])
        self.assertTrue(truncated["SOFTWARE_EVIDENCE_TRUNCATED"])

        evidence = pq.read_table(out / "requirement_evidence.parquet").to_pylist()
        none_rows = [row for row in evidence if row["NO_EXPERIENCE_EXPLICIT"]]
        self.assertEqual(len(none_rows), 1)
        self.assertEqual((none_rows[0]["MIN_YEARS"], none_rows[0]["MAX_YEARS"]), (0.0, 0.0))
        self.assertFalse(none_rows[0]["IS_APPLICANT_REQUIREMENT_CANDIDATE"])
        self.assertTrue(any(row["AD_EVIDENCE_TRUNCATED"] and row["MODULE_EVIDENCE_TRUNCATED"] for row in evidence))

        relations = pq.read_table(out / "qualification_relation_candidates.parquet").to_pylist()
        kinds = {row["RELATION_TYPE_CANDIDATE"] for row in relations}
        self.assertEqual(kinds, {"ALTERNATIVE_PATH_CANDIDATE", "EQUIVALENT_CREDENTIAL_CANDIDATE"})
        self.assertTrue(all(row["RELATION_RESOLUTION_STATUS"] == "unresolved_candidate" for row in relations))
        self.assertTrue(all(not row["COMPLETE_PATH_GRAPH"] and row["PATH_ID"] is None for row in relations))
        self.assertTrue(all(row["SCOPE_START"] is not None and row["SCOPE_END"] is not None for row in relations))
        self.assertTrue(all(len(row["SCOPE_TEXT"]) == row["SCOPE_END"] - row["SCOPE_START"] for row in relations))
        credential = next(row for row in relations if row["RELATION_TYPE_CANDIDATE"] == "EQUIVALENT_CREDENTIAL_CANDIDATE")
        provenance = json.loads(credential["DETAIL_JSON"])
        self.assertTrue(provenance["exporter_scope_whitespace_trimmed"])
        self.assertEqual(provenance["exporter_scope_left_trim_codepoints"], 1)
        self.assertEqual(provenance["exporter_scope_right_trim_codepoints"], 1)

        again = export(sample, candidates, out, self.parser)
        self.assertEqual(again, receipt)

    def test_rejects_nonunique_source_keys_without_complete_receipt(self):
        sample, candidates = self._write_fixture(duplicate=True)
        out = self.root / "duplicate-out"
        with self.assertRaisesRegex(ValueError, "source key is not unique"):
            export(sample, candidates, out, self.parser)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()

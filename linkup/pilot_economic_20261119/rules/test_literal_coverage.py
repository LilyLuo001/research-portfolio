"""Synthetic literal-coverage assertions, not semantic validation."""
import unittest

try:
    from . import cpu_candidates as engine
    from .literal_coverage import compare
except ImportError:
    import cpu_candidates as engine
    from literal_coverage import compare


class CoverageTest(unittest.TestCase):
    def audit(self, text, evidence):
        sha = engine._source_sha(text)
        return compare({sha: text}, [{"context_sha256": sha, "evidence": evidence}])

    def test_verified_quote_covered(self):
        report, detail = self.audit("3 years of experience required.", [{"quote": "3 years of experience"}])
        self.assertEqual(report["covered_fraction"], 1)
        self.assertEqual(len(detail), 1)

    def test_repeated_quote_location_not_guessed(self):
        report, detail = self.audit("3 years experience; 3 years experience", [{"quote": "3 years experience"}])
        self.assertIsNone(report["covered_fraction"])
        self.assertEqual(report["counts"]["citations_with_ambiguous_quote_location"], 1)

    def test_offsets_disambiguate(self):
        report, detail = self.audit("3 years experience; 3 years experience", [{"quote": "3 years experience", "start": 0, "end": 18}])
        self.assertEqual(report["covered_fraction"], 1)

    def test_age_is_uncovered_not_false_success(self):
        report, detail = self.audit("Must be 18 years of age.", [{"quote": "18 years of age"}])
        self.assertEqual(report["covered_fraction"], 0)
        self.assertFalse(detail[0]["covered_by_cpu_duration_candidate"])

    def test_duplicate_citations_count_once(self):
        report, detail = self.audit("3 years of experience", [{"quote": "3 years"}, {"quote": "3 years of experience"}])
        self.assertEqual(report["counts"]["duplicate_cited_duration_spans"], 1)
        self.assertEqual(report["counts"]["unique_verified_cited_duration_spans"], 1)

    def test_bad_offsets_and_unknown_source_separate(self):
        report, detail = self.audit("3 years experience", [{"quote": "3 years", "start": 2, "end": 9}])
        self.assertEqual(report["counts"]["citations_with_invalid_offsets"], 1)
        report, detail = compare({}, [{"context_sha256": "0" * 64, "evidence": []}])
        self.assertEqual(report["counts"]["reference_records_without_exact_source"], 1)


if __name__ == "__main__":
    unittest.main()

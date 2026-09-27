import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v6_parser", ROOT / "stage_c_v6" / "requirement_candidates.py")
PARSER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARSER)


def items(result, module):
    return [x for x in result["evidence"] if x["module"] == module]


class FocusedV6RepairTests(unittest.TestCase):
    def test_structural_headings(self):
        cases = (
            ("Required Skills\n5 years previous coating experience or experience calling on architects", "experience"),
            ("Job Specification:\nHigh School or Equivalent", "education"),
            ("Minimum Education/Experience Requirements A Senior category has over 10 years of experience and a MA/MS degree.", "education"),
        )
        for text, module in cases:
            with self.subTest(text=text):
                out = PARSER.extract(text)
                self.assertGreater(out["summary"][module]["applicant_qualification_candidate_count"], 0)

    def test_compound_credential_duration_line_under_duties(self):
        out = PARSER.extract("Key Responsibilities:\nHigh School Diploma OR GED Equivalent AND 7 years of experience")
        self.assertGreater(out["summary"]["education"]["applicant_qualification_candidate_count"], 0)
        self.assertGreater(out["summary"]["experience"]["applicant_qualification_candidate_count"], 0)

    def test_current_enrollment_is_not_attained_degree(self):
        out = PARSER.extract("Current Second Year, Third Year, or Fourth year student on campus able to commit one year")
        enrollment = [x for x in items(out, "education") if x.get("education_status") == "current_enrollment"]
        self.assertEqual(len(enrollment), 1)
        self.assertFalse(enrollment[0]["attained_degree"])
        self.assertFalse(enrollment[0]["is_applicant_requirement"])
        self.assertFalse(enrollment[0]["is_applicant_qualification_candidate"])
        self.assertFalse(enrollment[0]["is_unconditional_education_requirement"])
        self.assertTrue(enrollment[0]["education_enrollment_mention_candidate"])

    def test_bonus_tenure_is_not_job_experience_requirement(self):
        out = PARSER.extract("Overview $5,000 sign-on bonus and relocation for nurses with 1 or more years experience - External Applicants Only The RN Supervisor coordinates staff.")
        self.assertEqual(out["summary"]["experience"]["applicant_qualification_candidate_count"], 0)
        ordinary = PARSER.extract("Requirements:\nNurses with 1 or more years experience are eligible to apply.")
        self.assertEqual(ordinary["summary"]["experience"]["applicant_qualification_candidate_count"], 1)

    def test_foreign_language_is_not_phrase_patched(self):
        out = PARSER.extract("Vi söker dig med\nErfarenhet av att leda team i digitaliseringsinitiativ")
        self.assertEqual(out["summary"]["experience"]["applicant_qualification_candidate_count"], 0)

    def test_no_identifiers_in_parser(self):
        source = (ROOT / "stage_c_v6" / "requirement_candidates.py").read_text()
        for forbidden in ("D003", "D006", "D012", "D015", "D020", "D029", "D032"):
            self.assertNotIn(forbidden, source)

    def test_base_truncation_metadata_is_preserved_and_marked_incomplete(self):
        out = PARSER.extract("Requirements:\n" + "\n".join("Python required." for _ in range(110)))
        self.assertTrue(out["evidence_truncated"])
        self.assertGreater(out["evidence_total_before_truncation"], out["evidence_limit"])
        self.assertTrue(out["module_evidence_truncated"]["software"])
        self.assertTrue(out["v6_candidate_incomplete"])
        self.assertEqual(len(out["evidence"]), out["evidence_limit"])


if __name__ == "__main__":
    unittest.main()

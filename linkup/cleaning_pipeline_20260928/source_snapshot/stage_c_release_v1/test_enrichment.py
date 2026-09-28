import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

PARSER = load(ROOT / "stage_c_v6" / "requirement_candidates.py", "v6")
ENRICH = load(ROOT / "stage_c_release_v1" / "enrichment.py", "enrich")


class EnrichmentTests(unittest.TestCase):
    def run_enrich(self, text):
        return ENRICH.enrich(PARSER.extract(text))

    def test_duration_binds_only_explicit_object(self):
        out = self.run_enrich("Requirements: 3 years of accounting experience using SAP.")
        row = out["experience_evidence"][0]
        self.assertEqual((row["object_type"], row["min_years"], row["binding_status"]), ("object_unspecified", 3.0, "explicit"))
        sap = [x for x in out["technology_evidence"] if x["technology_name"] == "sap"][0]
        self.assertEqual(sap["role"], "use")

    def test_tool_experience_and_domain_do_not_share_duration(self):
        out = self.run_enrich("Qualifications: 3 years of SAP experience in healthcare.")
        exp = out["experience_evidence"][0]
        self.assertEqual(exp["object_type"], "specific_tool")
        self.assertEqual(exp["min_years"], 3.0)
        self.assertEqual(len(out["experience_evidence"]), 1)

    def test_multi_object_and_or_are_retained(self):
        out = self.run_enrich("Qualifications: experience with Python and SQL; experience in banking or insurance.")
        self.assertEqual(len(out["experience_evidence"]), 4)
        self.assertEqual([x["relation"] for x in out["experience_evidence"]], ["AND", "AND", "OR", "OR"])

    def test_technology_types_and_explicit_roles(self):
        out = self.run_enrich("Develop machine learning models, deploy predictive models, and use a large language model with Python and SQL required.")
        keyed = {(x["technology_name"], x["role"]) for x in out["technology_evidence"]}
        self.assertIn(("machine_learning", "develop"), keyed)
        self.assertIn(("predictive_model", "implement"), keyed)
        self.assertIn(("large_language_model", "use"), keyed)
        self.assertIn(("python", "unknown"), keyed)
        self.assertIn(("sql", "unknown"), keyed)

    def test_ai_unspecified_never_promoted_by_calendar_or_software(self):
        out = self.run_enrich("Use artificial intelligence. Python and SQL were required in 2018.")
        types = {x["technology_name"]: x["technology_type"] for x in out["technology_evidence"]}
        self.assertEqual(types["artificial_intelligence"], "unspecified_ai")
        self.assertEqual(types["python"], "traditional_software")
        self.assertEqual(types["sql"], "traditional_software")

    def test_generic_ai_terms_and_bare_llm_are_conservative(self):
        out = self.run_enrich("Develop machine learning and use LLM tools; build a large language model.")
        types = {x["technology_name"]: x for x in out["technology_evidence"]}
        self.assertEqual(types["machine_learning"]["technology_type"], "unspecified_ai")
        self.assertEqual(types["llm_ambiguous"]["technology_type"], "unspecified_ai")
        self.assertEqual(types["llm_ambiguous"]["technology_ambiguity"], "bare_llm")
        self.assertEqual(types["large_language_model"]["technology_type"], "generative_ai")

    def test_company_experience_is_not_applicant_candidate(self):
        out = self.run_enrich("About us:\nWe have 20 years of healthcare experience.")
        row = out["experience_evidence"][0]
        self.assertEqual(row["context"], "company")
        self.assertFalse(row["applicant_context_candidate"])

    def test_cooccurrence_does_not_create_role(self):
        out = self.run_enrich("Our team studies AI. Responsibilities include reports and coordination.")
        ai = out["technology_evidence"][0]
        self.assertEqual((ai["role"], ai["binding_status"]), ("unknown", "unknown"))

    def test_bare_experience_stays_object_unspecified(self):
        out = self.run_enrich("Qualifications:\nExperience required.")
        self.assertEqual(len(out["experience_evidence"]), 1)
        row = out["experience_evidence"][0]
        self.assertEqual((row["object_type"], row["binding_status"]), ("object_unspecified", "unknown"))
        self.assertIsNone(row["object_start"])

    def test_truncated_or_error_payload_suppresses_relations(self):
        payload = PARSER.extract("Requirements:\n" + "\n".join("Python required." for _ in range(110)))
        out = ENRICH.enrich(payload)
        self.assertTrue(out["flags"]["enrichment_incomplete"])
        self.assertEqual(out["experience_evidence"] + out["technology_evidence"], [])
        bad = ENRICH.enrich(PARSER.extract(None))
        self.assertTrue(bad["flags"]["input_parse_error"])

    def test_offsets_are_exact_and_no_text_is_copied(self):
        payload = PARSER.extract("Use Tableau and develop neural networks with 2 years of audit experience.")
        out = ENRICH.enrich(payload)
        text = payload["normalized_text"]
        for row in out["experience_evidence"]:
            self.assertTrue(text[row["object_start"]:row["object_end"]])
        for row in out["technology_evidence"]:
            self.assertTrue(text[row["technology_start"]:row["technology_end"]])
        self.assertNotIn("normalized_text", out)


if __name__ == "__main__":
    unittest.main()

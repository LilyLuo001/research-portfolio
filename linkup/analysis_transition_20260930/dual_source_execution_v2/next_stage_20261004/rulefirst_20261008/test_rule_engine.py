"""Synthetic QA for the bounded rule-first engine.

These cases contain no research records or private identifiers. They test only
the public rule contract and the engine's normalized-text coordinate system.
"""
from __future__ import annotations

import unittest

import rule_engine as engine


def evidence(result, *, kind=None, rule=None):
    items = result["evidence"]
    if kind is not None:
        items = [item for item in items if item["kind"] == kind]
    if rule is not None:
        items = [item for item in items if item["rule"] == rule]
    return items


def experience(result):
    items = evidence(result, kind="experience", rule="experience_clause")
    if len(items) != 1:
        raise AssertionError(f"expected one experience clause, found {len(items)}: {items}")
    return items[0]


class RuleEngineSyntheticTests(unittest.TestCase):
    def test_recent_graduate_language_is_an_entry_cue_only(self):
        out = engine.extract("Who you are:\nRecent college graduates are encouraged to apply.")
        self.assertTrue(out["flags"]["graduate_language"])
        self.assertEqual(evidence(out, kind="entry")[0]["rule"], "graduate_targeting_language")
        self.assertNotIn("explicit_no_experience", {item["rule"] for item in out["evidence"]})

    def test_explicit_no_experience_is_a_waiver(self):
        out = engine.extract("Minimum Qualifications:\nNo prior experience is required.")
        waiver = evidence(out, kind="entry", rule="explicit_no_experience")
        self.assertEqual(len(waiver), 1)
        self.assertEqual(waiver[0]["strength"], "explicit_waiver")
        self.assertEqual(evidence(out, kind="experience"), [])

    def test_object_specific_no_experience_is_a_waiver(self):
        out = engine.extract("Minimum Qualifications:\nNo Python experience is required.")
        waiver = evidence(out, kind="entry", rule="explicit_no_experience")
        self.assertEqual(len(waiver), 1)
        tech = evidence(out, kind="technology")
        self.assertEqual(len(tech), 1)
        self.assertTrue(tech[0]["negated"])

    def test_minimum_duration_and_task_object(self):
        out = engine.extract("Required Qualifications:\nAt least 3 years of accounting experience.")
        item = experience(out)
        self.assertEqual(item["objects"], ["occupation_task"])
        self.assertEqual(item["strength"], "required")
        self.assertEqual(item["duration"]["kind"], "minimum")
        self.assertEqual(item["duration"]["lower_years"], 3)

    def test_maximum_duration_and_domain_object(self):
        out = engine.extract("Preferred Qualifications:\nUp to 24 months of healthcare experience.")
        item = experience(out)
        self.assertEqual(item["objects"], ["industry_domain"])
        self.assertEqual(item["strength"], "preferred")
        self.assertEqual(item["duration"]["kind"], "maximum")
        self.assertEqual(item["duration"]["upper_years"], 2)

    def test_range_duration(self):
        out = engine.extract("Requirements:\n3–5 years of project management experience.")
        item = experience(out)
        self.assertEqual(item["duration"]["kind"], "range")
        self.assertEqual(item["duration"]["lower_years"], 3)
        self.assertEqual(item["duration"]["upper_years"], 5)

    def test_experience_object_families_are_kept_distinct(self):
        cases = (
            ("Requirements:\n5 years of professional work experience.", ["general_work"]),
            ("Requirements:\n5 years of nursing experience.", ["occupation_task"]),
            ("Requirements:\n5 years of banking experience.", ["industry_domain"]),
            ("Requirements:\n5 years of Python experience.", ["tool"]),
        )
        for text, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(experience(engine.extract(text))["objects"], expected)

    def test_education_or_experience_is_conditional_and_retains_years(self):
        out = engine.extract("Required Qualifications:\nBachelor's degree or 4 years of accounting experience.")
        item = experience(out)
        self.assertEqual(item["scope"], "education_alternative")
        self.assertEqual(item["duration"]["lower_years"], 4)
        self.assertIn("conditional_qualification", item["review_reasons"])
        self.assertTrue(out["flags"]["education_experience_alternative"])

    def test_required_and_preferred_headings_propagate_strength(self):
        required = engine.extract("Required Qualifications:\n3 years of sales experience.")
        preferred = engine.extract("Preferred Qualifications:\n3 years of sales experience.")
        self.assertEqual(experience(required)["strength"], "required")
        self.assertEqual(experience(preferred)["strength"], "preferred")

    def test_must_haves_heading_propagates_required_strength(self):
        out = engine.extract("Must Haves:\n3 years of accounting experience.")
        self.assertEqual(experience(out)["strength"], "required")

    def test_execution_assistance_is_not_supervision(self):
        out = engine.extract("Responsibilities:\nAssist the manager with routine processing.")
        families = {item["task_family"] for item in evidence(out, kind="task")}
        self.assertIn("execution_assistance", families)
        self.assertNotIn("people_supervision", families)

    def test_supervision_and_independent_responsibility_are_separate(self):
        out = engine.extract(
            "Responsibilities:\nSupervise a team of analysts.\nWork independently to manage projects."
        )
        families = {item["task_family"] for item in evidence(out, kind="task")}
        self.assertIn("people_supervision", families)
        self.assertIn("independent_responsibility", families)

    def test_client_ownership_is_not_contact_only(self):
        out = engine.extract(
            "Responsibilities:\nManage client relationships.\nCommunicate with customers."
        )
        families = [item["task_family"] for item in evidence(out, kind="task")]
        self.assertEqual(families.count("client_ownership"), 1)
        self.assertEqual(families.count("client_contact_only"), 1)

    def test_technology_role_cues_distinguish_mention_use_and_development(self):
        out = engine.extract(
            "Responsibilities:\nMonitor AI trends.\nUse ChatGPT for drafting.\nDevelop machine learning models."
        )
        roles = [(item["technology"], item["role_cue"]) for item in evidence(out, kind="technology")]
        self.assertIn(("ai_unspecified", "mention_only"), roles)
        self.assertIn(("genai", "use_cue"), roles)
        self.assertIn(("predictive_ai", "development_cue"), roles)

    def test_negated_task_is_not_emitted_as_positive_task(self):
        out = engine.extract("Responsibilities:\nDo not supervise staff.")
        self.assertEqual(evidence(out, kind="task"), [])
        self.assertIn("task_scope_ambiguous", out["review_reasons"])

    def test_company_history_and_customer_experience_are_not_work_history(self):
        company = engine.extract("About Us:\nOur company has 20 years of software experience.")
        customer = engine.extract("Responsibilities:\nImprove the customer experience through thoughtful design.")
        self.assertEqual(evidence(company, kind="experience"), [])
        self.assertEqual(evidence(customer, kind="experience"), [])

    def test_multiline_education_alternatives_are_not_universal_years(self):
        out = engine.extract("Requirements:\nMaster's degree\n2 years of accounting experience\nOR\nBachelor's degree\n4 years of accounting experience")
        rows = evidence(out, kind="experience")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(x['outcome_status']=='needs_review' for x in rows))
        self.assertFalse(out['flags'].get('required_experience_occupation_task', False))

    def test_unrecognized_specialty_is_not_general_experience(self):
        out = engine.extract('Requirements:\n3 years of professional experience in archival preservation')
        self.assertFalse(out['flags'].get('experience_general_work', False))
        self.assertIn('experience_object_unresolved', out['review_reasons'])

    def test_experience_design_business_prose_is_not_prior_work_requirement(self):
        out = engine.extract('Our capabilities span product and experience design.')
        self.assertFalse(out['flags'].get('experience_occupation_task', False))
        self.assertIn('experience_assertion_unresolved', out['review_reasons'])

    def test_questionnaire_answer_choices_are_not_job_requirements(self):
        out = engine.extract("Requirements:\n2 years of accounting experience\n01\nWhich of the following best describes your software proficiency?\nEntry level\nAdvanced\nDo you have experience in Python?")
        self.assertEqual(len(evidence(out, kind="experience")), 1)
        self.assertFalse(out['flags'].get('entry_junior_text', False))
        self.assertTrue(out['flags']['application_questionnaire_tail_excluded'])

    def test_quotes_and_offsets_are_exact_in_normalized_text(self):
        out = engine.extract(
            "<h2>Requirements</h2><p>3 years of analysis experience &amp; knowledge of SQL.</p>"
        )
        self.assertGreater(len(out["evidence"]), 0)
        for item in out["evidence"]:
            self.assertEqual(out["normalized_text"][item["start"]:item["end"]], item["quote"])
        self.assertIn("&", out["normalized_text"])
        self.assertNotIn("&amp;", out["normalized_text"])


if __name__ == "__main__":
    unittest.main()

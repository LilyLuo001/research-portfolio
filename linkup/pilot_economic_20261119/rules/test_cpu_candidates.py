"""Synthetic contract fixtures; no private advertisements or corpus labels."""
import json
import unittest

try:
    from . import cpu_candidates as engine
except ImportError:
    import cpu_candidates as engine


DEFAULT = ("experience.general_work", "experience.occupation_task", "experience.industry_domain",
           "experience.tool_specific", "education", "technology", "entry.explicit_no_experience")


def run(text, fields=DEFAULT):
    return engine.extract(text, fields)


def items(result, kind):
    return [row for row in result["candidates"] if row["kind"] == kind]


def duration(text):
    rows = items(run(text), "experience_duration")
    if len(rows) != 1:
        raise AssertionError("Expected one duration, got %d" % len(rows))
    return rows[0]


class CandidateContractTest(unittest.TestCase):
    def test_bare_years_not_general_or_posting_minimum(self):
        row = duration("5 years of experience.")
        self.assertEqual(row["subject_cues"], [])
        self.assertEqual(row["subject_assignment"], "unresolved")
        self.assertEqual(row["duration"]["kind"], "stated_unspecified")
        self.assertFalse(row["duration"]["is_posting_minimum"])

    def test_explicit_work_and_industry_are_cues_not_assignments(self):
        row = duration("At least 5 years of general work experience in healthcare.")
        self.assertIn("general_work", row["subject_cues"])
        self.assertIn("industry_domain", row["subject_cues"])
        self.assertIn("multiple_subject_cues", row["review_reasons"])
        self.assertEqual(row["subject_assignment"], "unresolved")

    def test_range(self):
        value = duration("3–5 years of programming experience.")["duration"]
        self.assertEqual((value["lower_years"], value["upper_years"]), (3.0, 5.0))
        self.assertEqual(value["kind"], "range")

    def test_between_range(self):
        value = duration("Between three and five years of experience.")["duration"]
        self.assertEqual((value["lower_years"], value["upper_years"]), (3.0, 5.0))

    def test_range_with_units_both_ends(self):
        value = duration("3 years to 5 years of experience.")["duration"]
        self.assertEqual((value["lower_years"], value["upper_years"]), (3.0, 5.0))

    def test_months_and_part_time_not_fte(self):
        row = duration("6–18 months of part-time work experience preferred.")
        self.assertEqual((row["duration"]["lower_years"], row["duration"]["upper_years"]), (0.5, 1.5))
        self.assertTrue(row["part_time_cue"])
        self.assertEqual(row["strength_cue"], "preferred")

    def test_strict_lower(self):
        value = duration("More than 5 years' experience.")["duration"]
        self.assertTrue(value["strict_lower"])
        self.assertEqual(value["kind"], "minimum")

    def test_strict_upper(self):
        value = duration("Less than 3 years of experience.")["duration"]
        self.assertTrue(value["strict_upper"])
        self.assertIsNone(value["lower_years"])
        self.assertEqual(value["upper_years"], 3)

    def test_postfix_minimum_is_not_semantic_minimum(self):
        row = duration("5 years or more of experience.")
        self.assertEqual(row["duration"]["kind"], "minimum")
        self.assertNotIn("or_alternative", row["scope_cues"])
        self.assertFalse(row["duration"]["is_posting_minimum"])

    def test_postfix_upper(self):
        self.assertEqual(duration("5 years or less of experience.")["duration"]["upper_years"], 5)

    def test_parenthetical_number_disagreement(self):
        row = duration("five (6) years of experience.")
        self.assertIn("word_parenthetical_number_disagreement", row["review_reasons"])
        self.assertIsNone(row["duration"]["lower_years"])

    def test_reversed_range(self):
        row = duration("5-3 years of experience.")
        self.assertIsNone(row["duration"]["lower_years"])
        self.assertIn("reversed_range_unresolved", row["review_reasons"])

    def test_age_and_salary_excluded(self):
        result = run("Applicants must be 18 years of age. Salary $50,000; posted 2026-11-19.")
        self.assertEqual(items(result, "experience_duration"), [])
        self.assertEqual(result["excluded_spans"][0]["reason"], "age_duration")

    def test_2000_not_parsed_as_years_of_work(self):
        self.assertEqual(items(run("The company dates to 2000 years ago."), "experience_duration"), [])

    def test_contract_duration_not_work_history(self):
        result = run("A 3 year contract; no prior experience required.")
        self.assertEqual(items(result, "experience_duration"), [])
        self.assertTrue(items(result, "experience_waiver"))

    def test_programming_is_not_program_duration(self):
        self.assertEqual(duration("3 years programming experience.")["duration"]["lower_years"], 3)

    def test_company_history_not_applicant_history(self):
        result = run("Our company has 25 years of experience.")
        self.assertEqual(items(result, "experience_duration"), [])
        self.assertEqual(result["excluded_spans"][0]["reason"], "company_history_duration")

    def test_degree_or_experience_preserves_branch_text(self):
        text = "A bachelor's degree with 2 years of experience OR a master's degree with 1 year of experience required."
        result = run(text)
        rows = items(result, "experience_duration")
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["duration"]["lower_years"] for row in rows], [2, 1])
        for row in rows:
            self.assertEqual(row["sentence"]["quote"], text)
            self.assertIn("or_alternative", row["scope_cues"])
            self.assertIn("duration_experience_association_unresolved", row["review_reasons"])
            self.assertFalse(row["duration"]["is_posting_minimum"])
        self.assertEqual({row["degree_level_cue"] for row in items(result, "degree_mention")}, {"bachelor", "master"})

    def test_multiline_or(self):
        text = "Requirements:\nBachelor's degree and 3 years of experience\nOR\nMaster's degree and 1 year of experience"
        rows = items(run(text), "experience_duration")
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIn("multiline_alternative_unresolved", row["scope_cues"])
            self.assertIn("OR", row["alternative_context"]["quote"])

    def test_substitution_kept_unknown(self):
        row = duration("5 years of experience may substitute for a degree.")
        self.assertIn("substitution", row["scope_cues"])
        self.assertFalse(row["duration"]["is_posting_minimum"])

    def test_no_experience_does_not_clear_other_fields(self):
        result = run("No Python experience is required; 2 years of sales experience preferred.")
        waivers = items(result, "experience_waiver")
        self.assertTrue(waivers)
        self.assertIn("tool", waivers[0]["subject_cues"])
        self.assertEqual(result["resolved_fields"], [])
        self.assertEqual(result["field_updates"], {})

    def test_mixed_required_preferred(self):
        row = duration("3 years required, but 5 preferred in this experience area.")
        self.assertEqual(row["strength_cue"], "mixed")
        self.assertIn("mixed_required_preferred", row["review_reasons"])

    def test_required_preferred_different_clauses(self):
        rows = items(run("3 years of work experience required; 2 years of banking experience preferred."), "experience_duration")
        self.assertEqual([row["strength_cue"] for row in rows], ["required", "preferred"])

    def test_headings_carry_forward(self):
        row = duration("Preferred Qualifications:\n3 years of SQL experience")
        self.assertEqual(row["strength_cue"], "preferred")

    def test_junior_mentees_do_not_make_worker_junior(self):
        result = run("You will mentor junior engineers with 2 years of experience.", DEFAULT + ("entry.explicit_junior_or_entry_label",))
        row = items(result, "experience_duration")[0]
        self.assertEqual(row["actor_cue"], "other_people_cue")
        self.assertEqual(result["field_status"]["entry.explicit_junior_or_entry_label"]["state"], "unsupported_unknown")

    def test_advertised_applicant_cue_stays_unresolved(self):
        row = duration("You must have 5 years of experience.")
        self.assertEqual(row["actor_cue"], "advertised_worker_cue")
        self.assertEqual(row["semantic_status"], "unknown")

    def test_nohit_never_absence(self):
        result = run("Welcome to our team.")
        self.assertEqual({entry["state"] for entry in result["field_status"].values()}, {"no_rule_hit_unknown"})
        self.assertEqual(result["field_updates"], {})

    def test_missing_fields_only(self):
        result = run("5 years of experience, a bachelor's degree, Python and ChatGPT.", ("technology",))
        self.assertTrue(result["candidates"])
        self.assertEqual({row["kind"] for row in result["candidates"]}, {"technology_keyword"})
        self.assertEqual(set(result["field_status"]), {"technology"})

    def test_unknown_field_stays_unsupported(self):
        result = run("5 years of experience", ("experience.unrecognized_taxonomy",))
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["unsupported_fields"], ["experience.unrecognized_taxonomy"])

    def test_technology_exact_keywords_and_offsets(self):
        text = "Use Python, C++, C#, ChatGPT and machine learning. No AI tools in interviews."
        rows = items(run(text), "technology_keyword")
        terms = {row["term"] for row in rows}
        self.assertTrue({"Python", "C++", "C#", "ChatGPT", "machine learning", "AI"}.issubset(terms))
        for row in rows:
            self.assertEqual(text[row["match"]["start"]:row["match"]["end"]], row["term"])
            self.assertTrue(row["lexical_only"])
        ai = next(row for row in rows if row["term"] == "AI")
        self.assertIn("negation", ai["scope_cues"])

    def test_tool_substrings_not_keywords(self):
        rows = items(run("Excellent Pythonesque examples with MySQL and C#suffix."), "technology_keyword")
        self.assertEqual(rows, [])

    def test_degree_abbreviations_not_lowercase_prepositions(self):
        self.assertEqual(items(run("Work as required; I am ready."), "degree_mention"), [])
        rows = items(run("BS or MS required."), "degree_mention")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all("abbreviated_degree_ambiguous" in row["review_reasons"] for row in rows))

    def test_phd_abbreviation_or_sentence_retained(self):
        text = "Ph.D. OR 5 years of experience required."
        for row in run(text)["candidates"]:
            self.assertEqual(row["sentence"]["quote"], text)

    def test_unicode_original_coordinates(self):
        text = "招聘 🚀\r\nRequired:\r\n  三 3–5 years’ experience in Python.\r\nBachelor’s degree."
        result = run(text)
        for row in result["candidates"]:
            for key in ("match", "clause", "sentence", "alternative_context"):
                if key in row:
                    value = row[key]
                    self.assertEqual(text[value["start"]:value["end"]], value["quote"])
        self.assertNotIn("normalized_text", result)

    def test_markup_is_not_silently_normalized(self):
        text = "<p>5 years of Python experience</p>"
        result = run(text)
        self.assertIn("markup_present_original_coordinates_retained", result["document_flags"])
        for row in result["candidates"]:
            span = row["match"]
            self.assertEqual(text[span["start"]:span["end"]], span["quote"])

    def test_questionnaire_is_not_requirement(self):
        text = "Which of the following best describes you?\n5 years of experience"
        row = duration(text)
        self.assertIn("questionnaire_answer_or_prompt", row["review_reasons"])
        self.assertEqual(row["semantic_status"], "unknown")

    def test_no_field_selection_is_noop(self):
        result = run("5 years", ())
        self.assertEqual(result["status"], "no_fields_requested")
        self.assertEqual(result["candidates"], [])

    def test_empty_and_oversized_are_distinct(self):
        self.assertEqual(run("")["status"], "empty_input")
        result = run("x" * (engine.MAX_TEXT_CHARACTERS + 1))
        self.assertEqual(result["status"], "input_limit_exceeded")
        self.assertFalse(result["candidates"])

    def test_invalid_inputs_raise(self):
        for text, fields in ((None, ("technology",)), ("x", None), ("x", "technology"), ("x", (None,))):
            with self.assertRaises(TypeError):
                engine.extract(text, fields)

    def test_cache_deterministic_and_missing_fields_specific(self):
        text = "5 years of experience in Python"
        first = run(text, ("technology", "experience.general_work"))
        second = run(text, ("experience.general_work", "technology", "technology"))
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertNotEqual(first["cache_key"], run(text, ("technology",))["cache_key"])
        self.assertNotEqual(first["cache_key"], run(text + " ")["cache_key"])
        self.assertEqual(len(engine.ENGINE_SHA256), 64)

    def test_candidate_cap_explicit(self):
        result = run("Python\n" * (engine.MAX_CANDIDATES + 3), ("technology",))
        self.assertTrue(result["candidates_truncated"])
        self.assertEqual(len(result["candidates"]), engine.MAX_CANDIDATES)
        self.assertEqual(result["candidate_count_before_limit"], engine.MAX_CANDIDATES + 3)
        self.assertEqual(result["status"], "candidate_limit_exceeded")

    def test_large_clause_context_bounded_with_full_bounds(self):
        text = "padding " * 1500 + "5 years of experience"
        row = duration(text)
        self.assertTrue(row["clause"]["truncated"])
        self.assertLessEqual(len(row["clause"]["quote"]), engine.MAX_CONTEXT_CHARACTERS)
        self.assertEqual((row["clause"]["full_start"], row["clause"]["full_end"]), (0, len(text)))
        self.assertEqual(text[row["clause"]["start"]:row["clause"]["end"]], row["clause"]["quote"])


if __name__ == "__main__":
    unittest.main()

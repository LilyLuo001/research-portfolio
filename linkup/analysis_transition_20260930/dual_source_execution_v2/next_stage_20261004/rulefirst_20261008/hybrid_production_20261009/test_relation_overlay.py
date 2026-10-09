#!/usr/bin/env python3
"""Synthetic-only regressions for the bounded relation overlay."""
import copy
import hashlib
import unittest

import relation_overlay as overlay


def result(text, evidence):
    return {
        "source_text_sha256": hashlib.sha256(("source:" + text).encode()).hexdigest(),
        "normalized_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "normalized_text": text,
        "evidence": evidence,
    }


def evidence(text, quote, kind, **fields):
    start = text.index(quote)
    return {"kind": kind, "rule": fields.pop("rule", "synthetic"),
            "quote": quote, "start": start, "end": start + len(quote), **fields}


def rules(applied):
    return [a["rule"] for item in applied["annotations"] for a in item["annotations"]]


class RelationOverlayTests(unittest.TestCase):
    def test_overlay_does_not_mutate_frozen_result(self):
        text = "Responsibilities\nBuild dashboards using Tableau."
        frozen = result(text, [evidence(text, "Build dashboards using Tableau.", "technology",
                                        term="Tableau", negated=False)])
        before = copy.deepcopy(frozen)
        overlay.apply(frozen)
        self.assertEqual(frozen, before)

    def test_rejects_normalized_hash_mismatch(self):
        text = "Required Qualifications\nFive years experience required."
        frozen = result(text, [evidence(text, "Five years experience required.", "experience")])
        frozen["normalized_text_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            overlay.apply(frozen)

    def test_rejects_negative_or_out_of_bounds_offsets(self):
        text = "abc"
        for start, end, quote in [(-1, 3, "c"), (0, 4, "abc")]:
            frozen = result(text, [{"kind": "experience", "rule": "synthetic",
                                    "quote": quote, "start": start, "end": end}])
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    overlay.apply(frozen)

    def test_rejects_quote_mismatch(self):
        text = "Two years experience."
        frozen = result(text, [{"kind": "experience", "rule": "synthetic",
                                "quote": "Three years", "start": 0, "end": 9}])
        with self.assertRaises(ValueError):
            overlay.apply(frozen)

    def test_required_heading_is_candidate_and_offsets_are_exact(self):
        text = "Required Qualifications\nExperience with audits."
        frozen = result(text, [evidence(text, "Experience with audits.", "experience",
                                        strength="required")])
        item = overlay.apply(frozen)["annotations"][0]
        heading = item["candidate_heading"]
        self.assertEqual(text[heading["start"]:heading["end"]], heading["quote"])
        self.assertEqual(heading["scope"], "required")
        self.assertEqual(item["heading_scope_status"], "recognized_preceding_heading_not_exhaustive")
        strength = next(a for a in item["annotations"] if a["rule"] == "experience_strength_components")
        self.assertEqual(strength["strength"], "required_heading_candidate")

    def test_no_heading_does_not_claim_recognized_heading(self):
        text = "Experience with audits."
        frozen = result(text, [evidence(text, text, "experience", strength="unspecified")])
        item = overlay.apply(frozen)["annotations"][0]
        self.assertIsNone(item["candidate_heading"])
        self.assertEqual(item["heading_scope_status"], "no_recognized_preceding_heading")

    def test_local_preferred_word_remains_clause_local(self):
        text = "Required Qualifications\nFinance experience preferred."
        frozen = result(text, [evidence(text, "Finance experience preferred.", "experience",
                                        strength="mixed")])
        item = overlay.apply(frozen)["annotations"][0]
        strength = next(a for a in item["annotations"] if a["rule"] == "experience_strength_components")
        self.assertEqual(strength["strength"], "preferred_candidate")
        self.assertEqual(strength["scope"], "local_clause_only")

    def test_mentoring_juniors_is_not_entry_eligibility(self):
        text = "Responsibilities\nMentor junior engineers on delivery."
        quote = "Mentor junior engineers on delivery."
        frozen = result(text, [evidence(text, quote, "entry", rule="entry_junior_text_mention")])
        applied = overlay.apply(frozen)
        marker = next(a for item in applied["annotations"] for a in item["annotations"]
                      if a["rule"] == "junior_refers_to_people_assisted")
        self.assertEqual(marker["entry_eligibility"], "not_established_by_this_phrase")
        self.assertIn("mentoring_other_people", rules(applied))

    def test_training_received_is_not_mentoring_others(self):
        text = "What We Offer\nYou will be provided with training for the role."
        quote = "You will be provided with training for the role."
        frozen = result(text, [evidence(text, quote, "task")])
        applied = overlay.apply(frozen)
        self.assertIn("explicit_training_for_applicant", rules(applied))
        self.assertNotIn("mentoring_other_people", rules(applied))

    def test_degree_or_experience_does_not_absorb_separate_years(self):
        text = ("Minimum Qualifications\nBachelor's degree or equivalent work experience.\n"
                "At least eight years of professional experience required.")
        alt = "Bachelor's degree or equivalent work experience."
        years = "At least eight years of professional experience required."
        frozen = result(text, [evidence(text, alt, "experience", strength="required"),
                               evidence(text, years, "experience", strength="required")])
        applied = overlay.apply(frozen)
        first = applied["annotations"][0]
        relation = next(a for a in first["annotations"]
                        if a["rule"] == "explicit_degree_or_equivalent_experience")
        self.assertEqual(relation["relation"], "OR")
        self.assertEqual(relation["experience_years"], "not_inferred")
        self.assertEqual(relation["other_experience_clauses"], "remain_separate_constraints")
        self.assertEqual(applied["annotations"][1]["evidence_index"], 1)

    def test_using_tool_does_not_infer_developing_tool(self):
        text = "Responsibilities\nBuild dashboards using Tableau."
        quote = "Build dashboards using Tableau."
        frozen = result(text, [evidence(text, quote, "technology", term="Tableau", negated=False)])
        marker = next(a for item in overlay.apply(frozen)["annotations"] for a in item["annotations"]
                      if a["rule"] == "explicit_using_named_tool")
        self.assertEqual(marker["relationship"], "use_of_named_tool")
        self.assertEqual(marker["not_inferred"], "development_of_named_tool")

    def test_developing_or_negated_use_is_not_tool_use_candidate(self):
        cases = [("Develop Python libraries.", False), ("Do not use Python.", True)]
        for quote, negated in cases:
            frozen = result(quote, [evidence(quote, quote, "technology", term="Python", negated=negated)])
            with self.subTest(quote=quote):
                self.assertNotIn("explicit_using_named_tool", rules(overlay.apply(frozen)))

    def test_no_marker_is_not_reported_as_absence(self):
        text = "General company information."
        applied = overlay.apply(result(text, []))
        self.assertEqual(applied["annotations"], [])
        self.assertIn("no-hit-as-absence", applied["interpretation"])


if __name__ == "__main__":
    unittest.main()

"""Synthetic-only adapter checks; no private fixtures, files, network or models."""
from copy import deepcopy
import unittest

from adapter import adapt_document, item_anchor, EXP, ENTRY, DUTY, NEW_REPRESENTATIONS


def review():
    return {"context_sha256": "synthetic-context", "document_status": "reviewed_full",
            "experience_outcomes": {x: "not_mentioned" for x in EXP},
            "experience_clauses": [], "qualification_alternatives": [],
            "entry_outcomes": {x: "not_mentioned" for x in ENTRY}, "entry_items": [],
            "responsibility_outcomes": {x: "not_mentioned" for x in DUTY}, "responsibility_items": [],
            "technology_inventory_status": "not_mentioned_after_full_review", "technology_items": []}


def clause(obj="general_work", lo=5, strength="required"):
    return {"object": obj, "object_detail": "synthetic object", "years_min": lo,
            "years_max": None, "years_relation": "at_least", "strength": strength,
            "conditionality": "unconditional", "alternative_group": None,
            "alternative_branch": None, "quotes": ["Synthetic experience evidence."]}


def responsibility(subject="advertised_worker", relation="current_duty", dim="training_mentoring"):
    return {"dimension": dim, "subject": subject, "relation": relation,
            "conditionality": "unconditional", "quotes": ["Synthetic duty evidence."]}


def masks(d):
    if "field_family" in d:
        return {d["field_family"]: d["status"]}
    result = {"document_status": d["document_status"],
              "technology_inventory_status": d["technology_inventory_status"]}
    for family in ("experience_outcomes", "entry_outcomes", "responsibility_outcomes"):
        result.update({family + "." + k: v for k, v in d[family].items()})
    return result


def adapt(d, **overrides):
    args = {"asset": "fixed10k" if "field_family" in d else "Pro",
            "source_sha": "synthetic-source", "source_ordinal": 1,
            "context_sha256": "synthetic-context", "original_accepted": True,
            "family_masks": masks(d)}
    args.update(overrides)
    return adapt_document(d, **args)


def rows(output, key):
    return [r for r in output["rows"] if r["variable_key"] == key]


def fixed(family, value, status="known"):
    return {"normalized_context_sha256": "synthetic-context", "field_family": family,
            "status": status, "structured_value": value}


class AdapterTest(unittest.TestCase):
    def test_stable_repeated_result_and_no_mutation(self):
        d = review(); d["experience_clauses"] = [clause()]
        d["experience_outcomes"]["general_work"] = "present"
        before = deepcopy(d)
        self.assertEqual(adapt(d), adapt(d))
        self.assertEqual(d, before)

    def test_anchor_all_components_bound(self):
        base = ["a", 1, "items", 0, "ctx"]
        key = item_anchor(*base)["anchor_id"]
        for i, replacement in enumerate(["b", 2, "other_items", 1, "ctx2"]):
            changed = base.copy(); changed[i] = replacement
            self.assertNotEqual(key, item_anchor(*changed)["anchor_id"])

    def test_same_item_atoms_bound_not_ad_minimum(self):
        d = review(); d["experience_clauses"] = [clause(lo=5), clause("industry_domain", 2, "preferred")]
        d["experience_outcomes"].update(general_work="present", industry_domain="present")
        o = adapt(d)
        year_rows = rows(o, "lk.exp.years_min")
        self.assertEqual([5, 2], [r["value"] for r in year_rows])
        self.assertNotEqual(year_rows[0]["item_anchor"], year_rows[1]["item_anchor"])
        for i in range(2):
            self.assertEqual(year_rows[i]["item_anchor"], rows(o, "lk.exp.object")[i]["item_anchor"])
            self.assertEqual(year_rows[i]["item_anchor"], rows(o, "lk.exp.strength")[i]["item_anchor"])
        self.assertFalse(rows(o, "measure.experience_bundle"))

    def test_zero_null_and_missing_not_collapsed(self):
        d = review(); c = clause(lo=0); d["experience_clauses"] = [c]
        d["experience_outcomes"]["general_work"] = "present"
        o = adapt(d)
        self.assertEqual(rows(o, "lk.exp.years_min")[0]["value"], 0)
        self.assertTrue(rows(o, "lk.exp.years_max")[0]["value_present"])
        self.assertIsNone(rows(o, "lk.exp.years_max")[0]["value"])
        del c["years_max"]
        self.assertFalse(rows(adapt(d), "lk.exp.years_max")[0]["value_present"])

    def test_bad_year_relation_blocked(self):
        d = review(); d["experience_clauses"] = [clause()]
        d["experience_outcomes"]["general_work"] = "present"
        d["experience_clauses"][0]["years_max"] = 2
        self.assertFalse(rows(adapt(d), "lk.exp.years_min")[0]["eligible_original_scope"])

    def test_no_cross_item_subject_relation_conjunction(self):
        d = review()
        d["responsibility_outcomes"]["training_mentoring"] = "present"
        d["responsibility_items"] = [responsibility(relation="required_capability"),
                                     responsibility(subject="other_employee")]
        row = next(r for r in rows(adapt(d), "lk.duty.current") if r["dimension"] == "training_mentoring")
        self.assertEqual(row["value"], "not_mentioned")
        self.assertEqual(row["supporting_item_anchors"], [])

    def test_broad_duty_kept_separate_from_current(self):
        d = review(); d["responsibility_outcomes"]["client_ownership"] = "present"
        d["responsibility_items"] = [responsibility(relation="prior_experience", dim="client_ownership")]
        o = adapt(d)
        self.assertEqual(rows(o, "lk.duty.client_ownership")[0]["value"], "present")
        self.assertEqual(next(r["value"] for r in rows(o, "lk.duty.current") if r["dimension"] == "client_ownership"), "not_mentioned")

    def test_current_same_item_positive(self):
        d = review(); d["responsibility_outcomes"]["training_mentoring"] = "present"
        d["responsibility_items"] = [responsibility()]
        row = next(r for r in rows(adapt(d), "lk.duty.current") if r["dimension"] == "training_mentoring")
        self.assertEqual(row["value"], "present")
        self.assertEqual(len(row["supporting_item_anchors"]), 1)

    def test_partial_does_not_establish_absence(self):
        d = review(); d["document_status"] = "reviewed_partial"
        o = adapt(d)
        self.assertFalse(rows(o, "lk.entry.explicit_new_graduate")[0]["eligible_original_scope"])
        self.assertTrue(all(r["value"] == "unknown" for r in rows(o, "lk.duty.current")))

    def test_relevant_unresolved_prevents_current_negative(self):
        d = review(); d["responsibility_items"] = [responsibility(subject="unresolved")]
        d["responsibility_outcomes"]["training_mentoring"] = "present"
        row = next(r for r in rows(adapt(d), "lk.duty.current") if r["dimension"] == "training_mentoring")
        self.assertEqual(row["value"], "unknown")

    def test_missing_inventory_prevents_current_negative(self):
        d = review(); del d["responsibility_items"]
        self.assertTrue(all(r["value"] == "unknown" for r in rows(adapt(d), "lk.duty.current")))

    def test_positive_broad_outcome_without_items_not_current_negative(self):
        d = review(); d["responsibility_outcomes"]["training_mentoring"] = "present"
        row = next(r for r in rows(adapt(d), "lk.duty.current") if r["dimension"] == "training_mentoring")
        self.assertEqual(row["value"], "unknown")

    def test_outer_accepted_does_not_override_unknown_family(self):
        d = fixed("experience_strength", [{"object": "general_work", "strength": "required"}], "unknown_or_conflict")
        row = rows(adapt(d), "lk.exp.strength")[0]
        self.assertFalse(row["eligible_original_scope"])
        self.assertEqual(row["measurement_state"], "unknown_or_conflict")

    def test_fixed_partial_preserved(self):
        d = fixed("experience_strength", [{"object": "general_work", "strength": "required"}], "partial")
        row = rows(adapt(d), "lk.exp.strength")[0]
        self.assertEqual(row["measurement_state"], "partial")
        self.assertFalse(row["eligible_original_scope"])

    def test_not_applicable_not_converted_to_zero(self):
        d = fixed("experience_literal_years", [], "not_applicable")
        self.assertFalse(rows(adapt(d), "lk.exp.years_min"))

    def test_kimi_unverified_never_promoted(self):
        o = adapt(review(), asset="Kimi_saved_unverified", original_accepted=False)
        self.assertTrue(all(not r["eligible_original_scope"] for r in o["rows"]))
        self.assertTrue(all(r["workflow_state"] == "saved_unverified" for r in o["rows"]))

    def test_missing_masks_never_promoted(self):
        o = adapt(review(), family_masks={})
        self.assertTrue(all(not r["eligible_original_scope"] for r in o["rows"]))

    def test_conflicting_masks_never_promoted(self):
        d = review(); m = masks(d); m["entry_outcomes.explicit_no_experience"] = "conflicting_original_masks"
        row = rows(adapt(d, family_masks=m), "lk.entry.explicit_no_experience")[0]
        self.assertEqual(row["measurement_state"], "unknown_or_conflict")
        self.assertFalse(row["eligible_original_scope"])

    def test_value_mask_mismatch_never_promoted(self):
        d = review(); m = masks(d); m["entry_outcomes.explicit_no_experience"] = "present"
        self.assertFalse(rows(adapt(d, family_masks=m), "lk.entry.explicit_no_experience")[0]["eligible_original_scope"])

    def test_fixed_mask_mismatch_never_promoted(self):
        d = fixed("experience_strength", [{"object": "general_work", "strength": "required"}])
        o = adapt(d, family_masks={"experience_strength": "not_applicable"})
        self.assertFalse(rows(o, "lk.exp.strength")[0]["eligible_original_scope"])

    def test_shared_condition_null_branch_and_and_preserved(self):
        d = review(); c = clause(); c.update(alternative_group="g", alternative_branch=None, conditionality="conditional")
        d["experience_clauses"] = [c]; d["experience_outcomes"]["general_work"] = "present"
        d["qualification_alternatives"] = [{"group": "g", "relation": "AND", "branches": [
            {"branch": "a", "condition": "Synthetic condition A", "quotes": ["Synthetic A"]},
            {"branch": "b", "condition": "Synthetic condition B", "quotes": ["Synthetic B"]}]}]
        o = adapt(d)
        self.assertEqual(rows(o, "lk.qual.group_link")[0]["value"]["binding"], "shared_condition")
        self.assertEqual(rows(o, "lk.qual.legacy_groups")[0]["value"]["relation"], "AND")
        self.assertEqual(d["qualification_alternatives"][0], rows(o, "lk.qual.legacy_groups")[0]["value"])

    def test_unresolved_shared_dimension_blocks_group_reuse(self):
        d = review(); a = clause(); a.update(alternative_group="g", alternative_branch="a")
        b = clause("industry_domain"); b.update(alternative_group="g", alternative_branch=None)
        d["experience_clauses"] = [a, b]
        d["experience_outcomes"].update(general_work="present", industry_domain="unknown")
        d["qualification_alternatives"] = [{"group": "g", "relation": "OR", "branches": [
            {"branch": "a", "condition": "Synthetic A", "quotes": ["Synthetic A"]}]}]
        self.assertFalse(rows(adapt(d), "lk.qual.legacy_groups")[0]["eligible_original_scope"])

    def test_undeclared_group_link_blocked(self):
        d = review(); c = clause(); c["alternative_group"] = "not_declared"
        d["experience_clauses"] = [c]; d["experience_outcomes"]["general_work"] = "present"
        self.assertFalse(rows(adapt(d), "lk.qual.group_link")[0]["eligible_original_scope"])

    def test_fixed_stripped_condition_not_recovered(self):
        d = fixed("qualification_conditions_and_alternatives", {"clauses": [],
                 "qualification_alternatives": [{"group": "g", "relation": "OR", "branches": [{"branch": "a"}]}]})
        row = rows(adapt(d), "lk.qual.legacy_groups")[0]
        self.assertFalse(row["eligible_original_scope"])
        self.assertEqual(row["measurement_state"], "partial")

    def test_fixed_carriers_never_cross_bind_arrays(self):
        a = fixed("experience_strength", [{"object": "general_work", "strength": "required"}])
        b = fixed("experience_literal_years", [{"object": "general_work", "years_min": 5, "years_max": None, "years_relation": "at_least"}])
        aa = rows(adapt(a, source_ordinal=5), "lk.exp.strength")[0]["item_anchor"]
        bb = rows(adapt(b, source_ordinal=6), "lk.exp.years_min")[0]["item_anchor"]
        self.assertNotEqual(aa, bb)

    def test_fixed_stripped_technology_not_invented(self):
        d = fixed("technology_category_and_role", {"inventory_status": "explicit_mentions_recorded",
                  "items": [{"family": "traditional_software_system", "role": "use_tool_for_work"}]})
        o = adapt(d)
        self.assertTrue(rows(o, "lk.tech.family")[0]["eligible_original_scope"])
        self.assertFalse(rows(o, "lk.tech.entity")[0]["value_present"])
        self.assertFalse(rows(o, "lk.tech.developed_object")[0]["value_present"])

    def test_new_representations_deferred_never_filled(self):
        o = adapt(review())
        self.assertTrue(set(NEW_REPRESENTATIONS).issubset({x["variable_key"] for x in o["deferred"]}))
        self.assertFalse(set(NEW_REPRESENTATIONS) & {x["variable_key"] for x in o["rows"]})

    def test_no_semantic_qualification_claim(self):
        o = adapt(review())
        self.assertFalse(o["new_semantic_acceptance_granted"])
        self.assertEqual(o["new_model_calls"], 0)
        self.assertTrue(all(not r["new_semantic_acceptance_granted"] for r in o["rows"]))

    def test_identity_mismatch_no_rows(self):
        self.assertFalse(adapt(review(), context_sha256="other-context")["rows"])

    def test_source_ordinal_bool_rejected(self):
        with self.assertRaises(ValueError):
            adapt(review(), source_ordinal=True)

    def test_nonfinite_input_rejected(self):
        d = review(); d["experience_clauses"] = [clause(lo=float("nan"))]
        with self.assertRaises(ValueError):
            adapt(d)

    def test_unresolved_conditions_preserved_not_known(self):
        d = review(); d["entry_outcomes"]["explicit_new_graduate"] = "present"
        d["entry_items"] = [{"target": "explicit_new_graduate", "conditionality": "unresolved", "quotes": ["Synthetic entry."]}]
        row = rows(adapt(d), "lk.entry.conditions")[0]
        self.assertEqual(row["value"]["conditionality"], "unresolved")
        self.assertFalse(row["eligible_original_scope"])

    def test_evidence_retained_not_verified(self):
        d = review(); d["experience_clauses"] = [clause()]
        d["experience_outcomes"]["general_work"] = "present"
        row = rows(adapt(d), "lk.evidence.ref")[0]
        self.assertEqual(row["value"]["quotes"], d["experience_clauses"][0]["quotes"])
        self.assertEqual(row["value"]["verification"], "retained_original_not_reverified_against_full_text")

    def test_unknown_legacy_shape_preserved_not_guessed(self):
        d = fixed("experience_object", {"present_objects": ["general_work"], "nonmention_status": "other"})
        self.assertFalse(rows(adapt(d), "lk.exp.general_work"))

    def test_outcome_conflict_propagates_to_same_family_atoms(self):
        d = review(); d["experience_outcomes"]["general_work"] = "present"
        d["experience_clauses"] = [clause()]
        m = masks(d); m["experience_outcomes.general_work"] = "not_mentioned"
        before = deepcopy(m); o = adapt(d, family_masks=m)
        affected = [r for r in o["rows"] if r["source_family"] == "experience_outcomes.general_work"]
        self.assertTrue(affected)
        self.assertTrue(all(not r["eligible_original_scope"] for r in affected))
        self.assertTrue(all(r["original_mask"] == "not_mentioned" for r in affected))
        self.assertTrue(all(r["effective_mask"] == "conflicting_original_masks" for r in affected))
        self.assertTrue(rows(o, "lk.entry.explicit_new_graduate")[0]["eligible_original_scope"])
        self.assertEqual(before, m)

    def test_duty_outcome_conflict_propagates_to_current(self):
        d = review(); d["responsibility_outcomes"]["training_mentoring"] = "present"
        d["responsibility_items"] = [responsibility()]
        m = masks(d); m["responsibility_outcomes.training_mentoring"] = "not_mentioned"
        row = next(r for r in rows(adapt(d, family_masks=m), "lk.duty.current")
                   if r["dimension"] == "training_mentoring")
        self.assertEqual(row["value"], "present")
        self.assertFalse(row["eligible_original_scope"])
        self.assertEqual(row["effective_mask"], "conflicting_original_masks")

    def test_technology_conflict_propagates_to_items(self):
        d = review(); d["technology_inventory_status"] = "unknown"
        d["technology_items"] = [{"technology": "Synthetic", "family": "traditional_software_system",
                                  "role": "use_tool_for_work", "developed_object": "", "context_note": "",
                                  "quotes": ["Synthetic technology"]}]
        m = masks(d); m["technology_inventory_status"] = "explicit_mentions_recorded"
        o = adapt(d, family_masks=m)
        self.assertTrue(all(not r["eligible_original_scope"] for r in o["rows"]
                            if r["source_family"] == "technology_inventory_status"))
        self.assertEqual(rows(o, "lk.tech.family")[0]["original_mask"], "explicit_mentions_recorded")

    def test_document_completeness_conflict_blocks_only_negatives(self):
        d = review(); d["experience_outcomes"]["general_work"] = "present"
        d["experience_clauses"] = [clause()]
        m = masks(d); m["document_status"] = "reviewed_partial"
        o = adapt(d, family_masks=m)
        self.assertFalse(rows(o, "lk.entry.explicit_new_graduate")[0]["eligible_original_scope"])
        self.assertTrue(rows(o, "lk.exp.years_min")[0]["eligible_original_scope"])
        self.assertTrue(all(r["value"] == "unknown" for r in rows(o, "lk.duty.current")))

    def test_missing_mask_never_looks_known(self):
        d = review(); d["experience_outcomes"]["general_work"] = "present"
        d["experience_clauses"] = [clause()]
        row = rows(adapt(d, family_masks={}), "lk.exp.strength")[0]
        self.assertEqual(row["value"], "required")
        self.assertEqual(row["measurement_state"], "missing_original_mask")
        self.assertFalse(row["eligible_original_scope"])

    def test_fixed_missing_mask_retains_source_status(self):
        d = fixed("experience_strength", [{"object": "general_work", "strength": "required"}])
        o = adapt(d, family_masks={})
        row = rows(o, "lk.exp.strength")[0]
        self.assertEqual(row["original_mask"], "missing_original_mask")
        self.assertEqual(row["effective_mask"], "missing_original_mask")
        self.assertEqual(d["status"], "known")
        self.assertFalse(row["eligible_original_scope"])

    def test_fixed_unavailable_and_candidate_masks_not_known(self):
        for status in ("source_unavailable", "candidate_only"):
            d = fixed("experience_strength", [{"object": "general_work", "strength": "required"}], status)
            row = rows(adapt(d), "lk.exp.strength")[0]
            self.assertEqual(row["measurement_state"], status)
            self.assertEqual(row["value"], "required")
            self.assertFalse(row["eligible_original_scope"])

    def test_fixed_conflicting_masks_preserved_separately(self):
        d = fixed("experience_strength", [{"object": "general_work", "strength": "required"}])
        row = rows(adapt(d, family_masks={"experience_strength": "not_applicable"}), "lk.exp.strength")[0]
        self.assertEqual(row["original_mask"], "not_applicable")
        self.assertEqual(row["effective_mask"], "conflicting_original_masks")
        self.assertEqual(row["value"], "required")

    def test_consistent_nonmention_mask_but_positive_duty_item_conflicts(self):
        d = review(); d["responsibility_items"] = [responsibility()]
        o = adapt(d)
        affected = [r for r in o["rows"] if r["source_family"] == "responsibility_outcomes.training_mentoring"]
        self.assertTrue(all(not r["eligible_original_scope"] for r in affected))
        self.assertEqual(rows(o, "lk.duty.training_mentoring")[0]["value"], "not_mentioned")
        self.assertEqual(next(r["value"] for r in rows(o, "lk.duty.current")
                              if r["dimension"] == "training_mentoring"), "present")

    def test_consistent_technology_nonmention_but_items_conflicts(self):
        d = fixed("technology_category_and_role", {"inventory_status": "not_mentioned_after_full_review",
                  "items": [{"family": "traditional_software_system", "role": "use_tool_for_work"}]})
        o = adapt(d)
        self.assertFalse(rows(o, "lk.tech.family")[0]["eligible_original_scope"])
        self.assertEqual(rows(o, "lk.tech.family")[0]["original_mask"], "known")
        self.assertEqual(rows(o, "lk.tech.family")[0]["effective_mask"], "conflicting_original_masks")

    def test_consistent_experience_nonmention_but_nonwaived_clause_conflicts(self):
        d = review(); d["experience_clauses"] = [clause()]
        o = adapt(d)
        self.assertFalse(rows(o, "lk.exp.years_min")[0]["eligible_original_scope"])
        self.assertEqual(rows(o, "lk.exp.general_work")[0]["value"], "not_mentioned")

    def test_waiver_does_not_create_experience_presence_conflict(self):
        d = review(); d["experience_clauses"] = [clause(strength="explicitly_waived")]
        o = adapt(d)
        self.assertEqual(rows(o, "lk.exp.general_work")[0]["effective_mask"], "not_mentioned")

    def test_generic_missing_document_mask_cannot_establish_nonmention(self):
        d = review(); d["experience_outcomes"]["general_work"] = "present"
        d["experience_clauses"] = [clause()]
        m = masks(d); del m["document_status"]
        o = adapt(d, asset="Pro", family_masks=m)
        negative = rows(o, "lk.entry.explicit_new_graduate")[0]
        self.assertEqual(negative["value"], "not_mentioned")
        self.assertEqual(negative["measurement_state"], "unknown")
        self.assertFalse(negative["eligible_original_scope"])
        self.assertTrue(rows(o, "lk.exp.years_min")[0]["eligible_original_scope"])

    def test_accepted_pro_merged_legacy_full_review_fallback(self):
        d = review(); m = masks(d); del m["document_status"]
        o = adapt(d, asset="Pro_merged", original_accepted=True, family_masks=m)
        negative = rows(o, "lk.entry.explicit_new_graduate")[0]
        self.assertEqual(negative["measurement_state"], "not_mentioned")
        self.assertTrue(negative["eligible_original_scope"])
        # The exception does not invent a document-status mask or qualify its row.
        self.assertFalse(rows(o, "lk.document.completeness")[0]["eligible_original_scope"])

    def test_unaccepted_pro_merged_cannot_use_completeness_fallback(self):
        d = review(); m = masks(d); del m["document_status"]
        o = adapt(d, asset="Pro_merged", original_accepted=False, family_masks=m)
        negative = rows(o, "lk.entry.explicit_new_graduate")[0]
        self.assertEqual(negative["measurement_state"], "unknown")
        self.assertFalse(negative["complete_review_requirement_met"])

    def test_pro_merged_fallback_never_supplies_family_mask(self):
        d = review(); m = masks(d)
        del m["document_status"]; del m["entry_outcomes.explicit_new_graduate"]
        o = adapt(d, asset="Pro_merged", original_accepted=True, family_masks=m)
        negative = rows(o, "lk.entry.explicit_new_graduate")[0]
        self.assertEqual(negative["measurement_state"], "missing_original_mask")
        self.assertFalse(negative["eligible_original_scope"])


if __name__ == "__main__":
    unittest.main()

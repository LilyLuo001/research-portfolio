"""Independent synthetic adapter invariants; reads no research data and writes no files."""
from copy import deepcopy
import json
from test_adapter import review, clause, responsibility, adapt, rows, masks


def run_checks():
    checks = {}
    d = review()
    d["experience_outcomes"]["general_work"] = "present"
    d["experience_clauses"] = [clause()]
    m = masks(d)
    m["experience_outcomes.general_work"] = "not_mentioned"
    before_d, before_m = deepcopy(d), deepcopy(m)
    o = adapt(d, family_masks=m)
    checks["family_conflict_all_descendants_blocked"] = all(
        not r["eligible_original_scope"] for r in o["rows"]
        if r["source_family"] == "experience_outcomes.general_work")
    checks["source_inputs_immutable"] = d == before_d and m == before_m
    checks["unrelated_family_retained"] = rows(o, "lk.entry.explicit_new_graduate")[0]["eligible_original_scope"]

    d = review()
    d["responsibility_outcomes"]["training_mentoring"] = "present"
    d["responsibility_items"] = [responsibility()]
    m = masks(d)
    m["responsibility_outcomes.training_mentoring"] = "not_mentioned"
    o = adapt(d, family_masks=m)
    checks["strict_duty_inherits_conflict"] = all(
        not r["eligible_original_scope"] for r in rows(o, "lk.duty.current")
        if r["dimension"] == "training_mentoring")

    d = review()
    d["experience_clauses"] = [clause(strength="explicitly_waived")]
    o = adapt(d)
    checks["waiver_not_promoted_to_presence"] = rows(o, "lk.exp.general_work")[0]["value"] == "not_mentioned"
    checks["waiver_clause_retained"] = rows(o, "lk.exp.strength")[0]["value"] == "explicitly_waived"

    d = review()
    m = masks(d)
    m.pop("document_status")
    o = adapt(d, family_masks=m)
    checks["generic_missing_doc_mask_negative_blocked"] = not rows(o, "lk.entry.explicit_new_graduate")[0]["eligible_original_scope"]
    o = adapt(d, family_masks=m, asset="Pro_merged")
    checks["accepted_merged_exception_scoped"] = rows(o, "lk.entry.explicit_new_graduate")[0]["eligible_original_scope"]
    o = adapt(d, family_masks=m, asset="Pro_merged", original_accepted=False)
    checks["unverified_merged_not_promoted"] = all(not r["eligible_original_scope"] for r in o["rows"])

    d = review()
    d["experience_outcomes"]["general_work"] = "present"
    d["experience_clauses"] = [clause()]
    o = adapt(d, family_masks={})
    checks["missing_family_mask_not_known"] = rows(o, "lk.exp.strength")[0]["measurement_state"] == "missing_original_mask"
    o = adapt(d)
    evidence = rows(o, "lk.evidence.ref")[0]
    checks["legacy_evidence_not_revalidated"] = evidence["value"]["verification"] == "retained_original_not_reverified_against_full_text"
    checks["no_new_acceptance"] = (not o["new_semantic_acceptance_granted"] and
                                   all(not r["new_semantic_acceptance_granted"] for r in o["rows"]))
    assert len(checks) == 12
    assert all(checks.values()), checks
    return checks


if __name__ == "__main__":
    print(json.dumps({"independent_synthetic_checks": run_checks(), "all_pass": True}, sort_keys=True))

#!/usr/bin/env python3
"""Synthetic regression of shared versus branch-specific qualification clauses."""
import copy
import json
import os
from validate_reviews import VERSION, validate_cross_fields

base = {
    "document_status": "reviewed_full",
    "experience_outcomes": {"general_work": "present", "occupation_task": "not_mentioned",
                            "industry_domain": "not_mentioned", "tool_specific": "not_mentioned"},
    "entry_outcomes": {}, "responsibility_outcomes": {},
    "entry_items": [], "responsibility_items": [],
    "technology_inventory_status": "not_mentioned_after_full_review", "technology_items": [],
    "experience_clauses": [{"object": "general_work", "strength": "required",
        "years_min": 3, "years_max": None, "years_relation": "at_least",
        "alternative_group": "education", "alternative_branch": None}],
    "qualification_alternatives": [{"group": "education", "branches": [
        {"branch": "bachelors"}, {"branch": "masters"}]}],
}
# Complete dimensions are necessary even though this fixture targets relations.
from validate_reviews import ENTRY_DIMS, RESP_DIMS
base["entry_outcomes"] = {x: "not_mentioned" for x in ENTRY_DIMS}
base["responsibility_outcomes"] = {x: "not_mentioned" for x in RESP_DIMS}
cases = [
    ("shared_condition", "education", None, None),
    ("real_single_branch", "education", "bachelors", None),
    ("unassociated_clause", None, None, None),
    ("orphan_branch", None, "bachelors", "requires a group"),
    ("unknown_group_shared", "absent", None, "undeclared alternative group"),
    ("invented_branch", "education", "all_options", "undeclared alternative branch"),
]
for name, group, branch, expected in cases:
    row = copy.deepcopy(base)
    row["experience_clauses"][0].update(alternative_group=group, alternative_branch=branch)
    errors = validate_cross_fields(row)
    if expected is None:
        assert not errors, (name, errors)
    else:
        assert len(errors) == 1 and expected in errors[0], (name, errors)
print(json.dumps({"status": "pass", "synthetic_cases": len(cases),
                  "validator_version": VERSION, "job_id": os.getenv("SLURM_JOB_ID"),
                  "research_data_used": False}))

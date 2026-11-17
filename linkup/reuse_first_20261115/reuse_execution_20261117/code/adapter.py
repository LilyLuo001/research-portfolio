"""Deterministic adapter for retained LinkUp values, dictionary 1.0.0.

This module does not read files, advertisements or credentials; call models;
change a source object; resolve conflicts; or qualify a new measurement route.
The caller must exclude protected contexts *before* reading document payloads,
verify source hashes/versions, and supply masks from the exact same carrier.

Rows retain the original value even when it cannot be reused as known.  The
``eligible_original_scope`` flag is a compatibility/mask guard, NOT a new
semantic-accuracy certification.  Missing values and empty item inventories do
not create negative observations.  Independent carriers never share anchors.
"""
from copy import deepcopy
import hashlib
import json
import math


VERSION = "1.0.0"
EXP = ("general_work", "occupation_task", "industry_domain", "tool_specific")
ENTRY = ("explicit_no_experience", "explicit_new_graduate",
         "current_student_internship", "explicit_junior_or_entry_label")
DUTY = ("independent_judgment", "client_ownership", "people_supervision",
        "training_mentoring")
OUTCOMES = {"present", "not_mentioned", "unknown"}
STRENGTH = {"required", "preferred", "explicitly_waived", "unspecified", "unresolved"}
CONDITIONALITY = {"unconditional", "conditional", "unspecified", "unresolved"}
YEARS = {"at_least", "range", "exact", "at_most", "not_stated", "unresolved"}
SUBJECT = {"advertised_worker", "other_employee", "employer_general", "unresolved"}
RELATION = {"current_duty", "required_capability", "prior_experience",
            "other_person", "employer_description", "unresolved"}
TECH_FAMILY = {"traditional_software_system", "predictive_ml_ai", "generative_ai", "unresolved"}
TECH_ROLE = {"develop_technology", "implement_deploy_technology", "use_tool_for_work",
             "background_mention", "unresolved"}
TECH_INVENTORY = {"explicit_mentions_recorded", "not_mentioned_after_full_review", "unknown"}
KNOWN_MASKS = {"known", "not_applicable", "present", "not_mentioned",
               "reviewed_full", "explicit_mentions_recorded", "not_mentioned_after_full_review"}
UNKNOWN_MASKS = {"unknown", "unresolved", "unknown_or_conflict", "conflicting_original_masks"}
NEW_REPRESENTATIONS = (
    "lk.exp.bound_inclusivity", "lk.qual.condition_atoms", "lk.exp.object_concept",
    "lk.qual.logic", "lk.task.activity", "lk.task.code", "measure.cross_domain_openness",
)
FIXED_FAMILIES = {
    "experience_object", "experience_strength", "experience_literal_years",
    "qualification_conditions_and_alternatives", "entry_wording_and_scope",
    "current_responsibility_subject_and_relation", "technology_category_and_role",
}
_MISSING = object()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def item_anchor(source_sha, source_ordinal, array_path, item_index, context_sha256):
    """Source-position identity only; never a semantic cross-carrier join key."""
    components = {"source_sha": source_sha, "source_ordinal": source_ordinal,
                  "array_path": array_path, "item_index": item_index,
                  "context_sha256": context_sha256}
    return {"anchor_id": hashlib.sha256(_canonical(components).encode()).hexdigest(),
            **components}


def _number(value):
    return value is None or (type(value) in (int, float) and math.isfinite(value) and value >= 0)


def _enum(value, values):
    return isinstance(value, str) and value in values


def _strings(value):
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x for x in value)


def _years_consistent(item):
    if not all(k in item for k in ("years_min", "years_max", "years_relation")):
        return False
    lo, hi, relation = item["years_min"], item["years_max"], item["years_relation"]
    if not _number(lo) or not _number(hi) or not _enum(relation, YEARS):
        return False
    if lo is not None and hi is not None and lo > hi:
        return False
    return {"not_stated": lo is None and hi is None,
            "at_least": lo is not None and hi is None,
            "at_most": lo is None and hi is not None,
            "exact": lo is not None and hi is not None and lo == hi,
            "range": lo is not None and hi is not None,
            "unresolved": False}[relation]


def _block(row, state="unknown"):
    # A later item-level uncertainty must not conceal an existing mask problem.
    if row["measurement_state"] in {"unknown_or_conflict", "partial", "missing_original_mask",
                                    "candidate_only", "source_unavailable"}:
        state = row["measurement_state"]
    row.update(eligible_original_scope=False, route_qualification="not_qualified",
               measurement_state=state)


class _Adapter:
    def __init__(self, document, asset, source_sha, source_ordinal, context, accepted,
                 masks, versions):
        self.document = document
        self.asset = asset
        self.source_sha = source_sha
        self.ordinal = source_ordinal
        self.context = context
        self.accepted = accepted
        self.masks = masks
        self.effective_masks = dict(masks)
        self.versions = deepcopy(versions or {})
        self.rows = []
        self.issues = []
        self.deferred = []
        self.fixed = document.get("field_family") in FIXED_FAMILIES
        # Validate exact scalar masks once, before any atom is emitted.  A
        # family-level disagreement applies to ALL descendants of that family,
        # not merely the ad-level outcome row.  Original masks remain untouched.
        if self.fixed:
            family = document["field_family"]
            self.check_exact_mask(family, document.get("status", _MISSING), "status")
        else:
            for family in ("document_status", "technology_inventory_status"):
                self.check_exact_mask(family, document.get(family, _MISSING), family)
            for family in ("experience_outcomes", "entry_outcomes", "responsibility_outcomes"):
                values = document.get(family)
                if isinstance(values, dict):
                    for dimension, value in values.items():
                        self.check_exact_mask(family + "." + dimension, value,
                                              family + "." + dimension)
        self.check_inventory_consistency()
        # Completeness disagreement restricts negative/nonmention derivations;
        # it does not invalidate compatible explicit positive atoms elsewhere.
        # Only already-accepted historical Pro_merged carriers have the verified
        # legacy contract allowing a missing separate document-status mask.
        # This narrow fallback never supplies any missing family mask.
        doc_mask = self.effective_mask("document_status")
        legacy_merged_full = (self.asset == "Pro_merged" and self.accepted and
                              doc_mask == "missing_original_mask")
        self.full = (document.get("document_status") == "reviewed_full" and
                     (doc_mask == "reviewed_full" or legacy_merged_full))

    def issue(self, code, path, variable=None):
        issue = {"code": code, "source_path": path}
        if variable:
            issue["variable_key"] = variable
        if issue not in self.issues:
            self.issues.append(issue)

    def defer(self, variable, reason, path="", family=None):
        row = {"variable_key": variable, "reason": reason, "source_path": path,
               "source_family": family, "new_semantic_acceptance_granted": False}
        if row not in self.deferred:
            self.deferred.append(row)

    def mask(self, family):
        return self.masks.get(family, "missing_original_mask")

    def effective_mask(self, family):
        return self.effective_masks.get(family, "missing_original_mask")

    def check_exact_mask(self, family, observed, path):
        if family not in self.masks or self.masks[family] == "conflicting_original_masks":
            return
        if observed is _MISSING or self.masks[family] != observed:
            self.effective_masks[family] = "conflicting_original_masks"
            self.issue("original_value_and_mask_disagree", path)

    def conflict(self, family, path):
        self.effective_masks[family] = "conflicting_original_masks"
        self.issue("original_outcome_and_inventory_disagree", path)

    def check_inventory_consistency(self):
        """Frozen structural outcome/item checks, not a new text interpretation."""
        d = self.document
        checks = (("experience_outcomes", "experience_clauses", "object", EXP,
                   lambda x: x.get("strength") in {"required", "preferred", "unspecified"}),
                  ("entry_outcomes", "entry_items", "target", ENTRY, lambda x: True),
                  ("responsibility_outcomes", "responsibility_items", "dimension", DUTY,
                   lambda x: x.get("subject") == "advertised_worker" and x.get("relation") in
                   {"current_duty", "required_capability", "prior_experience"}))
        if self.fixed:
            f, value = d["field_family"], d.get("structured_value")
            if not isinstance(value, dict):
                return
            if f in {"entry_wording_and_scope", "current_responsibility_subject_and_relation"}:
                check = checks[1] if f == "entry_wording_and_scope" else checks[2]
                checks = (("outcomes", "items", check[2], check[3], check[4]),)
                d = value
            elif f == "technology_category_and_role":
                checks = ()
                d = value
            else:
                return
        for out_key, items_key, selector, dimensions, supporting in checks:
            outcomes, items = d.get(out_key), d.get(items_key)
            if not isinstance(outcomes, dict) or not isinstance(items, list):
                continue
            for dimension in dimensions:
                matched = any(isinstance(x, dict) and x.get(selector) == dimension and supporting(x)
                              for x in items)
                state = outcomes.get(dimension)
                if (state == "not_mentioned" and matched) or (state == "present" and not matched):
                    self.conflict(self.document["field_family"] if self.fixed else out_key + "." + dimension,
                                  ("structured_value." if self.fixed else "") + out_key + "." + dimension)
        inventory_key = "inventory_status" if self.fixed else "technology_inventory_status"
        items_key = "items" if self.fixed else "technology_items"
        if self.fixed and self.document["field_family"] != "technology_category_and_role":
            return
        inventory, items = d.get(inventory_key), d.get(items_key)
        if isinstance(items, list) and ((bool(items) and inventory != "explicit_mentions_recorded") or
                                      (inventory == "explicit_mentions_recorded" and not items)):
            self.conflict(self.document["field_family"] if self.fixed else "technology_inventory_status",
                          ("structured_value." if self.fixed else "") + inventory_key)

    def anchor(self, path, index):
        return item_anchor(self.source_sha, self.ordinal, path, index, self.context)

    def emit(self, variable, value, path, family, *, anchor=None, valid=True,
             complete=None, dimension=None, dependencies=(), derived=False):
        present = value is not _MISSING
        mask = self.mask(family)
        effective = self.effective_mask(family)
        all_masks = {family: mask}
        all_effective_masks = {family: effective}
        for dep in dependencies:
            all_masks[dep] = self.mask(dep)
            all_effective_masks[dep] = self.effective_mask(dep)
        original_known = all(x in KNOWN_MASKS for x in all_effective_masks.values())
        complete = self.full if complete is None else complete
        is_negative = isinstance(value, str) and value in {
            "not_mentioned", "not_mentioned_after_full_review"}
        unknown_atom = isinstance(value, str) and value in {"unknown", "unresolved"}
        if not present:
            measurement = "missing"
        elif any(x in UNKNOWN_MASKS for x in all_effective_masks.values()):
            measurement = "unknown_or_conflict"
        elif "missing_original_mask" in all_effective_masks.values():
            measurement = "missing_original_mask"
        elif "source_unavailable" in all_effective_masks.values():
            measurement = "source_unavailable"
        elif "candidate_only" in all_effective_masks.values():
            measurement = "candidate_only"
        elif any(x in {"partial", "reviewed_partial"} for x in all_effective_masks.values()):
            measurement = "partial"
        elif not original_known:
            measurement = "unrecognized_original_mask"
        elif not valid:
            measurement = "invalid_original_value"
        elif unknown_atom or (is_negative and not complete):
            measurement = "unknown"
        elif effective == "not_applicable":
            measurement = "not_applicable"
        elif is_negative:
            measurement = "not_mentioned"
        elif value is None:
            measurement = "null_preserved"
        else:
            measurement = "known"
        eligible = bool(self.accepted and present and valid and original_known
                        and not unknown_atom and (not is_negative or complete))
        if not self.accepted:
            workflow = "saved_unverified"
        elif effective in UNKNOWN_MASKS:
            workflow = "reviewed_unknown"
        elif effective in {"partial", "reviewed_partial"}:
            workflow = "partial_original_scope"
        elif effective in {"candidate_only", "source_unavailable", "missing_original_mask"}:
            workflow = effective
        else:
            workflow = "accepted_original_scope"
        row = {"variable_key": variable, "definition_version": VERSION,
               "value": deepcopy(value) if present else None, "value_present": present,
               "source_path": path, "source_family": family, "original_mask": mask,
               "effective_mask": effective, "dependency_masks": all_masks,
               "effective_dependency_masks": all_effective_masks,
               "original_accepted": self.accepted,
               "asset": self.asset, "source_sha": self.source_sha,
               "source_ordinal": self.ordinal, "context_sha256": self.context,
               "source_versions": deepcopy(self.versions), "item_anchor": deepcopy(anchor),
               "workflow_state": workflow, "measurement_state": measurement,
               "engineering_state": "structurally_mapped_not_revalidated" if valid and present
                                    else "missing" if not present else "invalid_original_value",
               "route_qualification": "original_scope_only" if eligible else "not_qualified",
               "eligible_original_scope": eligible, "new_semantic_acceptance_granted": False,
               "deterministic_derivation": derived,
               "complete_review_required": is_negative,
               "complete_review_requirement_met": bool(complete) if is_negative else None}
        if dimension is not None:
            row["dimension"] = dimension
        self.rows.append(row)
        if not present:
            self.defer(variable, "source_atom_missing", path, family)
        elif not valid:
            self.issue("source_atom_invalid", path, variable)
        elif is_negative and not complete:
            self.issue("nonmention_requires_complete_original_review", path, variable)
        return row

    def scalar(self, item, key, variable, path, family, anchor=None, validator=None,
               **kwargs):
        value = item.get(key, _MISSING)
        valid = value is _MISSING or validator is None or validator(value)
        return self.emit(variable, value, path + "." + key, family, anchor=anchor,
                         valid=valid, **kwargs)

    def items(self, value, path):
        if not isinstance(value, list):
            self.issue("item_inventory_missing_or_malformed", path)
            return []
        result = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                self.issue("item_not_object", path + "[" + str(index) + "]")
                continue
            result.append((index, item, self.anchor(path, index)))
        return result

    def emit_anchor(self, anchor, family):
        self.emit("lk.claim.item_anchor", anchor, anchor["array_path"] + "[" +
                  str(anchor["item_index"]) + "]", family, anchor=anchor, derived=True)

    def evidence(self, item, path, family, anchor):
        # Existing quotes are carried forward but NEVER verified against text here.
        if "quotes" not in item:
            self.defer("lk.evidence.ref", "original_evidence_not_in_carrier", path, family)
            return
        self.emit("lk.evidence.ref", {"quotes": item["quotes"],
                  "evidence_resolution": self.document.get("evidence_resolution"),
                  "source_item_anchor": anchor,
                  "verification": "retained_original_not_reverified_against_full_text"},
                  path + ".quotes", family, anchor=anchor, valid=_strings(item["quotes"]))

    def outcomes(self, value, dims, prefix, path, family=None, complete=None):
        if not isinstance(value, dict):
            self.issue("outcome_container_missing_or_malformed", path)
            value = {}
        for dim in dims:
            fam = family or path + "." + dim
            self.scalar(value, dim, prefix + dim, path, fam,
                        validator=lambda v: _enum(v, OUTCOMES), complete=complete,
                        dimension=dim)

    def group_links(self, item, path, family, anchor, groups):
        if "alternative_group" not in item or "alternative_branch" not in item:
            self.emit("lk.qual.group_link", _MISSING, path, family, anchor=anchor)
            return
        g, b = item["alternative_group"], item["alternative_branch"]
        valid = ((g is None or isinstance(g, str)) and (b is None or isinstance(b, str))
                 and (g is not None or b is None))
        if g is not None:
            matches = [x for x in groups if isinstance(x, dict) and x.get("group") == g]
            valid = valid and len(matches) == 1
            if len(matches) == 1:
                branches = matches[0].get("branches")
                valid = valid and isinstance(branches, list)
                if b is not None and isinstance(branches, list):
                    valid = valid and sum(isinstance(x, dict) and x.get("branch") == b
                                          for x in branches) == 1
        value = {"group": g, "branch": b,
                 "binding": "shared_condition" if g is not None and b is None
                            else "branch" if b is not None else "no_group_recorded"}
        self.emit("lk.qual.group_link", value, path + ".alternative_group+alternative_branch",
                  family, anchor=anchor, valid=bool(valid))

    def experience_items(self, values, path, *, fixed_family=None, fields=None, groups=None):
        groups = groups if isinstance(groups, list) else []
        fields = fields or {"object", "object_detail", "years_min", "years_max",
                            "years_relation", "strength", "conditionality", "group_link"}
        for index, item, anchor in self.items(values, path):
            at = path + "[" + str(index) + "]"
            # Wave02 used resulting_dimension; retain its different field name in provenance.
            object_key = "object" if "object" in item else "resulting_dimension"
            obj = item.get(object_key)
            family = fixed_family or "experience_outcomes." + str(obj)
            self.emit_anchor(anchor, family)
            mapping = [("object", object_key, "lk.exp.object", lambda v: _enum(v, set(EXP) | {"unresolved"})),
                       ("object_detail", "object_detail", "lk.exp.object_label", lambda v: isinstance(v, str)),
                       ("years_min", "years_min", "lk.exp.years_min", _number),
                       ("years_max", "years_max", "lk.exp.years_max", _number),
                       ("years_relation", "years_relation", "lk.exp.years_relation", lambda v: _enum(v, YEARS)),
                       ("strength", "strength", "lk.exp.strength", lambda v: _enum(v, STRENGTH)),
                       ("conditionality", "conditionality", "lk.exp.conditionality", lambda v: _enum(v, CONDITIONALITY))]
            for selector, key, variable, validator in mapping:
                if selector in fields:
                    row = self.scalar(item, key, variable, at, family, anchor, validator)
                    if not _enum(obj, set(EXP)):
                        _block(row)
                    if selector.startswith("years_") and not _years_consistent(item):
                        _block(row, "unknown" if item.get("years_relation") == "unresolved"
                               else "invalid_original_value")
                        self.issue("same_clause_year_bounds_not_compatible", at, variable)
            if "group_link" in fields:
                self.group_links(item, at, family, anchor, groups)
            self.evidence(item, at, family, anchor)
        self.defer("measure.experience_bundle", "qualified_logic_and_cross_family_binding_not_materialized", path, fixed_family)

    def qualifications(self, groups, path, family=None, clauses=None):
        for index, group, anchor in self.items(groups, path):
            at = path + "[" + str(index) + "]"
            deps = sorted({"experience_outcomes." + str(c.get("object")) for c in (clauses or [])
                           if isinstance(c, dict) and c.get("alternative_group") == group.get("group")})
            fam = family or (deps[0] if deps else "qualification_alternatives")
            branches = group.get("branches")
            valid = (isinstance(group.get("group"), str)
                     and _enum(group.get("relation"), {"AND", "OR", "unresolved"})
                     and isinstance(branches, list) and bool(branches)
                     and all(isinstance(b, dict) and isinstance(b.get("branch"), str) for b in branches))
            self.emit_anchor(anchor, fam)
            row = self.emit("lk.qual.legacy_groups", group, at, fam, anchor=anchor,
                            dependencies=deps, valid=valid)
            # Legacy group text is not a parsed qualification logic tree.
            if group.get("relation") == "unresolved":
                _block(row)
            if isinstance(branches, list):
                names = [b.get("branch") for b in branches if isinstance(b, dict)]
                if len(names) != len(set(names)):
                    _block(row, "invalid_original_value")
                    self.issue("duplicate_qualification_branch", at, "lk.qual.legacy_groups")
                if any(not isinstance(b, dict) or not isinstance(b.get("condition"), str)
                       for b in branches):
                    _block(row, "partial")
                    self.defer("lk.qual.legacy_groups", "original_condition_text_not_in_carrier", at, fam)
                for j, branch in enumerate(branches):
                    if isinstance(branch, dict):
                        self.evidence(branch, at + ".branches[" + str(j) + "]", fam,
                                      self.anchor(at + ".branches", j))

    def entry_items(self, values, path, family=None):
        for index, item, anchor in self.items(values, path):
            at = path + "[" + str(index) + "]"
            fam = family or "entry_outcomes." + str(item.get("target"))
            valid = (_enum(item.get("target"), set(ENTRY))
                     and _enum(item.get("conditionality"), CONDITIONALITY))
            self.emit_anchor(anchor, fam)
            row = self.emit("lk.entry.conditions", item, at, fam, anchor=anchor, valid=valid)
            if item.get("conditionality") == "unresolved":
                _block(row)
            self.evidence(item, at, fam, anchor)

    def responsibility(self, outcomes, values, path, *, family=None, complete=None):
        complete = self.full if complete is None else complete
        inventory = self.items(values, path)
        for index, item, anchor in inventory:
            at = path + "[" + str(index) + "]"
            fam = family or "responsibility_outcomes." + str(item.get("dimension"))
            self.emit_anchor(anchor, fam)
            self.scalar(item, "subject", "lk.duty.subject", at, fam, anchor, lambda v: _enum(v, SUBJECT))
            self.scalar(item, "relation", "lk.duty.relation", at, fam, anchor, lambda v: _enum(v, RELATION))
            row = self.emit("lk.duty.conditions", item, at, fam, anchor=anchor,
                            valid=_enum(item.get("dimension"), set(DUTY)) and
                                  _enum(item.get("conditionality"), CONDITIONALITY))
            if item.get("conditionality") == "unresolved":
                _block(row)
            self.evidence(item, at, fam, anchor)
        for dim in DUTY:
            fam = family or "responsibility_outcomes." + dim
            selected = [(item, anchor) for _, item, anchor in inventory if item.get("dimension") == dim]
            positive = [anchor for item, anchor in selected
                        if item.get("subject") == "advertised_worker" and item.get("relation") == "current_duty"
                        and _enum(item.get("conditionality"), CONDITIONALITY - {"unresolved"})]
            relevant_unknown = any(item.get("subject") not in SUBJECT - {"unresolved"}
                                   or item.get("relation") not in RELATION - {"unresolved"}
                                   or item.get("conditionality") not in CONDITIONALITY - {"unresolved"}
                                   for item, _ in selected)
            unassignable = (not isinstance(values, list) or len(inventory) != len(values)
                            or any(item.get("dimension") not in DUTY for _, item, _ in inventory))
            original_outcome = outcomes.get(dim) if isinstance(outcomes, dict) else None
            inventory_complete = (complete and not unassignable and not relevant_unknown
                                  and original_outcome in {"present", "not_mentioned"}
                                  and not (original_outcome == "present" and not selected))
            result = "present" if positive else "not_mentioned" if inventory_complete else "unknown"
            row = self.emit("lk.duty.current", result, path, fam, complete=inventory_complete,
                            dimension=dim, derived=True)
            row["supporting_item_anchors"] = positive

    def technology(self, inventory, values, path, *, family="technology_inventory_status", complete=None):
        self.emit("lk.tech.inventory", inventory, path.rsplit(".", 1)[0] + ".inventory_status"
                  if path.endswith(".items") else "technology_inventory_status", family,
                  valid=inventory is _MISSING or _enum(inventory, TECH_INVENTORY), complete=complete)
        for index, item, anchor in self.items(values, path):
            at = path + "[" + str(index) + "]"
            self.emit_anchor(anchor, family)
            self.scalar(item, "technology", "lk.tech.entity", at, family, anchor, lambda v: isinstance(v, str) and bool(v))
            self.scalar(item, "family", "lk.tech.family", at, family, anchor, lambda v: _enum(v, TECH_FAMILY))
            self.scalar(item, "role", "lk.tech.role", at, family, anchor, lambda v: _enum(v, TECH_ROLE))
            developed = ({k: deepcopy(item[k]) for k in ("developed_object", "context_note") if k in item}
                         if "developed_object" in item else _MISSING)
            self.emit("lk.tech.developed_object", developed, at + ".developed_object+context_note",
                      family, anchor=anchor,
                      valid=developed is _MISSING or isinstance(item["developed_object"], (str, type(None))))
            self.evidence(item, at, family, anchor)

    def formal(self):
        d = self.document
        self.scalar(d, "document_status", "lk.document.completeness", "document", "document_status",
                    validator=lambda v: _enum(v, {"reviewed_full", "reviewed_partial", "unresolved"}))
        for path, dims, prefix in (("experience_outcomes", EXP, "lk.exp."),
                                   ("entry_outcomes", ENTRY, "lk.entry."),
                                   ("responsibility_outcomes", DUTY, "lk.duty.")):
            self.outcomes(d.get(path), dims, prefix, path)
        self.experience_items(d.get("experience_clauses"), "experience_clauses",
                              groups=d.get("qualification_alternatives"))
        self.qualifications(d.get("qualification_alternatives"), "qualification_alternatives",
                            clauses=d.get("experience_clauses"))
        self.entry_items(d.get("entry_items"), "entry_items")
        self.responsibility(d.get("responsibility_outcomes"), d.get("responsibility_items"), "responsibility_items")
        self.technology(d.get("technology_inventory_status", _MISSING), d.get("technology_items"), "technology_items")

    def fixed10k(self):
        d = self.document
        f = d["field_family"]
        value = d.get("structured_value", _MISSING)
        path = "structured_value"
        # Fixed10k full-review scope was encoded in family status by its frozen adapter.
        complete = self.effective_mask(f) in {"known", "not_applicable"}
        if value is _MISSING or value is None:
            self.issue("fixed_family_has_no_value_carrier", path)
            return
        if f == "experience_object":
            if isinstance(value, dict) and any(k in value for k in EXP):
                # Wave02 absence enum differs; preserve as legacy instead of rewriting.
                self.outcomes(value, EXP, "lk.exp.", path, f, complete)
            else:
                self.defer("lk.exp.object", "legacy_object_shape_not_same_definition", path, f)
            self.defer("lk.exp.object_label", "original_text_detail_stripped_from_fixed_carrier", path, f)
        elif f in {"experience_strength", "experience_literal_years"} and isinstance(value, list):
            fields = {"object", "strength"} if f == "experience_strength" else {
                "object", "years_min", "years_max", "years_relation"}
            self.experience_items(value, path, fixed_family=f, fields=fields)
        elif f == "qualification_conditions_and_alternatives":
            if isinstance(value, dict) and isinstance(value.get("clauses"), list):
                groups = value.get("qualification_alternatives")
                self.experience_items(value["clauses"], path + ".clauses", fixed_family=f,
                                      fields={"object", "conditionality", "group_link"}, groups=groups)
                self.qualifications(groups, path + ".qualification_alternatives", family=f)
            elif isinstance(value, list):
                self.experience_items(value, path, fixed_family=f,
                                      fields={"object", "conditionality", "group_link"})
            else:
                self.issue("fixed_qualification_shape_not_supported", path)
        elif f == "entry_wording_and_scope" and isinstance(value, dict) and "outcomes" in value:
            self.outcomes(value.get("outcomes"), ENTRY, "lk.entry.", path + ".outcomes", f, complete)
            self.entry_items(value.get("items"), path + ".items", f)
        elif f == "current_responsibility_subject_and_relation" and isinstance(value, dict) and "outcomes" in value:
            self.outcomes(value.get("outcomes"), DUTY, "lk.duty.", path + ".outcomes", f, complete)
            self.responsibility(value.get("outcomes"), value.get("items"), path + ".items", family=f, complete=complete)
        elif f == "technology_category_and_role" and isinstance(value, dict) and "inventory_status" in value:
            self.technology(value.get("inventory_status", _MISSING), value.get("items"), path + ".items",
                            family=f, complete=complete)
        else:
            self.issue("fixed_legacy_shape_preserved_not_promoted", path)


def adapt_document(document, *, asset, source_sha, source_ordinal, context_sha256,
                   original_accepted, family_masks, source_versions=None):
    """Return atom rows, structural issues and deferred mappings, without I/O.

    ``family_masks`` is a same-context/source-SHA/asset/ad-key dictionary.  If
    an exact family has conflicting historical masks, the caller passes
    ``conflicting_original_masks`` (and retains all originals separately).
    No cross-source precedence or array-position alignment is performed here.
    """
    if not isinstance(document, dict) or not isinstance(family_masks, dict):
        raise TypeError("document_and_exact_family_masks_must_be_dicts")
    if not isinstance(original_accepted, bool):
        raise TypeError("original_accepted_must_be_bool")
    if not all(isinstance(x, str) and x for x in (asset, source_sha, context_sha256)):
        raise ValueError("source_identity_required")
    if type(source_ordinal) is not int or source_ordinal < 1:
        raise ValueError("one_based_source_ordinal_required")
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in family_masks.items()):
        raise TypeError("family_masks_must_map_strings_to_strings")
    _canonical(document)  # Fail closed on nonfinite/non-JSON values, before emitting anything.
    a = _Adapter(document, asset, source_sha, source_ordinal, context_sha256,
                 original_accepted, dict(family_masks), source_versions)
    context = document.get("normalized_context_sha256", document.get("context_sha256"))
    if context != context_sha256:
        a.issue("context_identity_mismatch_or_missing", "context_sha256")
    elif a.fixed:
        a.fixed10k()
    else:
        a.formal()
    for variable in NEW_REPRESENTATIONS:
        a.defer(variable, "new_representation_not_inferred_from_legacy_carrier")
    return {"adapter_version": VERSION, "rows": a.rows, "issues": a.issues,
            "deferred": a.deferred, "new_model_calls": 0,
            "new_semantic_acceptance_granted": False}

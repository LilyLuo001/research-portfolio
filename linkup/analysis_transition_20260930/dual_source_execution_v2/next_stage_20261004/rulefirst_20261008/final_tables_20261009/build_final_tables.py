#!/usr/bin/env python3
"""Build D56 public tables from immutable frozen results and relation overlay.

This is aggregation only: it performs no extraction, parsing-rule change,
model inference, weighting, or population extrapolation.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import socket
import time
from pathlib import Path

OBJECTS = ("general_work", "occupation_task", "industry_domain", "tool")
TECH = ("software", "predictive_ai", "genai", "ai_unspecified")
GROUPS = ("ALL", "A", "B", "C")
UNITS = ("unique_exact_text", "represented_posting")


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except Exception as exc:
                    raise RuntimeError(f"invalid JSONL {path}:{n}: {exc}")


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def frac(n, d):
    return round(n / d, 8) if d else None


def applies(group, arm):
    return group == "ALL" or group == arm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--overlay", required=True)
    ap.add_argument("--represented", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    started = time.time()
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True, mode=0o700)

    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    if contract.get("decision") != "D56-finite-six-table-release" or contract.get("api_calls_allowed") is not False:
        raise RuntimeError("unexpected measurement contract")

    baseline_rows = list(read_jsonl(args.baseline))
    overlay_rows = list(read_jsonl(args.overlay))
    represented = list(read_jsonl(args.represented))
    if len(baseline_rows) != 7635 or len(overlay_rows) != 7635 or len(represented) != 10000:
        raise RuntimeError("frozen row counts changed")
    baseline = {x.get("exact_text_sha256"): x for x in baseline_rows}
    overlay = {x.get("exact_text_sha256"): x for x in overlay_rows}
    if len(baseline) != 7635 or len(overlay) != 7635 or set(baseline) != set(overlay):
        raise RuntimeError("baseline/overlay unique SHA mismatch")
    positions = [x.get("fixed_sample_position_1based") for x in represented]
    if positions != list(range(1, 10001)):
        raise RuntimeError("represented positions are not ordered 1..10000")
    if {x.get("exact_text_sha256") for x in represented} != set(baseline):
        raise RuntimeError("represented/baseline SHA sets differ")

    arm_by_sha = collections.defaultdict(set)
    represented_by_sha = collections.Counter()
    years_by_sha = collections.defaultdict(set)
    represented_den = collections.Counter()
    for row in represented:
        sha, arm = row.get("exact_text_sha256"), row.get("arm")
        if arm not in {"A", "B", "C"}:
            raise RuntimeError("invalid legacy arm")
        arm_by_sha[sha].add(arm)
        represented_by_sha[sha] += 1
        represented_den[arm] += 1
        year = (row.get("cell") or {}).get("created_year")
        if year is not None:
            years_by_sha[sha].add(year)
    if any(len(v) != 1 for v in arm_by_sha.values()):
        raise RuntimeError("one exact text spans multiple arms")
    unique_den = collections.Counter(next(iter(arm_by_sha[s])) for s in baseline)
    denominators = {
        "unique_exact_text": {"ALL": 7635, **dict(unique_den)},
        "represented_posting": {"ALL": 10000, **dict(represented_den)},
    }

    span_checks = span_errors = overlay_index_checks = overlay_index_errors = 0
    features = {}
    for sha, base_row in baseline.items():
        arm = next(iter(arm_by_sha[sha]))
        if base_row.get("status") != "complete":
            features[sha] = {"arm": arm, "processing_complete": False}
            continue
        result = base_row.get("result") or {}
        normalized = result.get("normalized_text")
        if result.get("source_text_sha256") != sha or not isinstance(normalized, str):
            raise RuntimeError("baseline source binding invalid")
        if hashlib.sha256(normalized.encode("utf-8")).hexdigest() != result.get("normalized_text_sha256"):
            raise RuntimeError("baseline normalized SHA invalid")
        evidence = result.get("evidence") or []
        for e in evidence:
            span_checks += 1
            a, b = e.get("start"), e.get("end")
            if (not isinstance(a, int) or not isinstance(b, int)
                    or not (0 <= a <= b <= len(normalized)) or normalized[a:b] != e.get("quote")):
                span_errors += 1
        over = overlay[sha]
        if over.get("status") != "candidate_markers_complete" or over.get("baseline_normalized_text_sha256") != result.get("normalized_text_sha256"):
            raise RuntimeError("overlay/baseline binding invalid")
        overlay_rules = set()
        background_indices = set()
        mentoring_duty_candidate = False
        mentoring_referent_or_prior_marker = False
        for item in over.get("candidate_annotations") or []:
            overlay_index_checks += 1
            idx = item.get("evidence_index")
            if not isinstance(idx, int) or idx < 0 or idx >= len(evidence):
                overlay_index_errors += 1
                continue
            e = evidence[idx]
            if (item.get("start"), item.get("end"), item.get("kind")) != (e.get("start"), e.get("end"), e.get("kind")):
                overlay_index_errors += 1
            for ann in item.get("annotations") or []:
                rule = ann.get("rule")
                if rule:
                    overlay_rules.add(rule)
                    if rule == "preceding_background_heading":
                        background_indices.add(idx)
                    if rule == "mentoring_other_people":
                        heading_scope = (item.get("candidate_heading") or {}).get("scope")
                        span_kinds = {
                            other.get("kind") for other in evidence
                            if (other.get("start"), other.get("end")) == (e.get("start"), e.get("end"))
                        }
                        excluded_section = e.get("section") in {
                            "required", "preferred", "qualification_unspecified", "background"
                        }
                        is_current_duty_candidate = (
                            heading_scope == "duties"
                            and not (span_kinds & {"experience", "knowledge", "education"})
                            and not excluded_section
                        )
                        if is_current_duty_candidate:
                            mentoring_duty_candidate = True
                        else:
                            mentoring_referent_or_prior_marker = True
        if span_errors or overlay_index_errors:
            raise RuntimeError("span/index validation failed")

        exp_indexed = [(i, e) for i, e in enumerate(evidence) if e.get("kind") == "experience"]
        tech = [e for e in evidence if e.get("kind") == "technology" and not e.get("negated")]
        flags = {k for k, v in (result.get("flags") or {}).items() if v is True}
        broad_objects = set()
        narrow_objects = set()
        for _, e in exp_indexed:
            broad_objects.update(x for x in (e.get("objects") or []) if x in OBJECTS)
            objs = [x for x in (e.get("objects") or []) if x in OBJECTS]
            if (len(objs) == 1 and e.get("outcome_status") == "explicit_rule_candidate"
                    and e.get("scope") == "unconditional_explicit_clause"):
                narrow_objects.add(objs[0])
        entry_broad = bool(flags & {"entry_junior_text", "graduate_language", "explicit_no_experience", "explicit_experience_waiver"})
        entry_narrow = bool(flags & {"graduate_language", "explicit_no_experience"})
        baseline_responsibility = bool(flags & {"task_people_supervision", "task_independent_responsibility", "task_client_ownership"})
        responsibility = baseline_responsibility or mentoring_duty_candidate
        features[sha] = {
            "arm": arm,
            "processing_complete": True,
            "evidence": evidence,
            "experience": exp_indexed,
            "broad_objects": broad_objects,
            "narrow_objects": narrow_objects,
            "numeric": [(i, e) for i, e in exp_indexed if e.get("duration") is not None],
            "unresolved_or_multi": any(len(e.get("objects") or []) != 1 for _, e in exp_indexed),
            "overlay_rules": overlay_rules,
            "background_indices": background_indices,
            "tech": tech,
            "entry_broad": entry_broad,
            "entry_narrow": entry_narrow,
            "responsibility": responsibility,
            "mentoring_duty_candidate": mentoring_duty_candidate,
            "mentoring_referent_or_prior_marker": mentoring_referent_or_prior_marker,
            "years": years_by_sha[sha],
        }

    instances = {"unique_exact_text": [], "represented_posting": []}
    for sha, feat in features.items():
        instances["unique_exact_text"].append((sha, feat["arm"]))
    for row in represented:
        instances["represented_posting"].append((row["exact_text_sha256"], row["arm"]))

    # T1: processing and observable-coverage funnel.
    t1 = []
    t1_metrics = (
        ("input_identity", lambda f: True),
        ("processing_complete", lambda f: f.get("processing_complete") is True),
        ("processing_failure", lambda f: f.get("processing_complete") is not True),
        ("experience_evidence_observed", lambda f: bool(f.get("experience"))),
        ("numeric_duration_evidence_observed", lambda f: bool(f.get("numeric"))),
        ("object_unresolved_or_multiobject", lambda f: f.get("unresolved_or_multi") is True),
        ("overlay_relation_candidate_observed", lambda f: bool(f.get("overlay_rules"))),
        ("experience_not_observed_by_rules", lambda f: f.get("processing_complete") is True and not f.get("experience")),
    )
    for unit in UNITS:
        for group in GROUPS:
            denom = denominators[unit][group]
            selected = [features[s] for s, arm in instances[unit] if applies(group, arm)]
            for metric, pred in t1_metrics:
                n = sum(bool(pred(f)) for f in selected)
                t1.append({"unit": unit, "group": group, "metric": metric, "numerator": n,
                           "denominator": denom, "fraction": frac(n, denom),
                           "status": "observed", "claim_boundary": "current frozen sample only; no-match is unknown"})

    # T2: document incidence and evidence counts are separate and nonadditive.
    t2 = []
    for unit in UNITS:
        for group in GROUPS:
            denom = denominators[unit][group]
            selected = [(s, features[s]) for s, arm in instances[unit] if applies(group, arm)]
            for definition in ("broad_object_membership", "narrow_singleobject_explicit_unconditional"):
                for dimension in OBJECTS:
                    keys = collections.Counter()
                    docs = collections.defaultdict(set)
                    for instance_no, (sha, f) in enumerate(selected):
                        for _, e in f.get("experience", []):
                            objs = [x for x in (e.get("objects") or []) if x in OBJECTS]
                            qualifies = dimension in objs
                            if definition.startswith("narrow"):
                                qualifies = (objs == [dimension] and e.get("outcome_status") == "explicit_rule_candidate"
                                             and e.get("scope") == "unconditional_explicit_clause")
                            if not qualifies:
                                continue
                            d = e.get("duration") or {}
                            key = (e.get("outcome_status", "unknown"), e.get("strength", "unknown"),
                                   e.get("scope", "unknown"), d.get("kind", "missing"),
                                   d.get("lower_years"), d.get("upper_years"))
                            keys[key] += 1
                            docs[key].add(instance_no)
                    if not keys:
                        keys[("not_observed", "not_observed", "not_observed", "missing", None, None)] = 0
                    for (clause_status, strength, scope, duration_kind, lower_years, upper_years), evidence_count in sorted(keys.items(), key=lambda x: str(x[0])):
                        dc = len(docs[(clause_status, strength, scope, duration_kind, lower_years, upper_years)])
                        t2.append({"unit": unit, "group": group, "definition": definition, "dimension": dimension,
                                   "clause_status": clause_status, "strength": strength, "scope": scope,
                                   "duration_kind": duration_kind, "lower_years": lower_years, "upper_years": upper_years,
                                   "document_count": dc, "evidence_count": evidence_count, "document_denominator": denom,
                                   "document_fraction": frac(dc, denom), "additivity": "overlapping_nonadditive"})
            issue_docs = sum(bool(f.get("unresolved_or_multi")) for _, f in selected)
            issue_evidence = sum(sum(len(e.get("objects") or []) != 1 for _, e in f.get("experience", [])) for _, f in selected)
            t2.append({"unit": unit, "group": group, "definition": "unresolved_or_multiobject", "dimension": "unresolved_or_multiobject",
                       "clause_status": "needs_review_or_unresolved", "strength": "not_applicable", "scope": "not_applicable",
                       "duration_kind": "not_applicable", "lower_years": "", "upper_years": "",
                       "document_count": issue_docs, "evidence_count": issue_evidence, "document_denominator": denom,
                       "document_fraction": frac(issue_docs, denom), "additivity": "separate_diagnostic_nonadditive"})

    # T3: lexicon mentions, local role cues, explicit-use overlay, cooccurrence and overlap.
    t3 = []
    for unit in UNITS:
        for group in GROUPS:
            denom = denominators[unit][group]
            selected = [(i, features[s]) for i, (s, arm) in enumerate(instances[unit]) if applies(group, arm)]
            for tech_name in TECH:
                docset = set(); evn = 0; roles = collections.Counter(); role_docs = collections.defaultdict(set)
                for i, f in selected:
                    for e in f.get("tech", []):
                        if e.get("technology") == tech_name:
                            evn += 1; docset.add(i); role = e.get("role_cue", "unknown"); roles[role] += 1; role_docs[role].add(i)
                t3.append({"unit": unit, "group": group, "metric": "technology_lexicon_match", "technology": tech_name,
                           "role_or_overlap": "any_nonnegated", "experience_dimension": "not_applicable",
                           "document_count": len(docset), "evidence_count": evn, "document_denominator": denom,
                           "document_fraction": frac(len(docset), denom), "status": "observed_text_candidate"})
                for role in sorted(roles):
                    t3.append({"unit": unit, "group": group, "metric": "neighboring_verb_role_cue", "technology": tech_name,
                               "role_or_overlap": role, "experience_dimension": "not_applicable",
                               "document_count": len(role_docs[role]), "evidence_count": roles[role], "document_denominator": denom,
                               "document_fraction": frac(len(role_docs[role]), denom), "status": "proximity_cue_not_document_role"})
                for obj in OBJECTS:
                    n = sum(any(e.get("technology") == tech_name for e in f.get("tech", [])) and obj in f.get("broad_objects", set()) for _, f in selected)
                    t3.append({"unit": unit, "group": group, "metric": "technology_experience_cooccurrence", "technology": tech_name,
                               "role_or_overlap": "within_document", "experience_dimension": obj,
                               "document_count": n, "evidence_count": "", "document_denominator": denom,
                               "document_fraction": frac(n, denom), "status": "cooccurrence_no_causal_interpretation"})
            explicit_use_docs = sum("explicit_using_named_tool" in f.get("overlay_rules", set()) for _, f in selected)
            t3.append({"unit": unit, "group": group, "metric": "explicit_using_named_tool_overlay", "technology": "named_tool",
                       "role_or_overlap": "use_phrase", "experience_dimension": "not_applicable", "document_count": explicit_use_docs,
                       "evidence_count": "", "document_denominator": denom, "document_fraction": frac(explicit_use_docs, denom),
                       "status": "tool_use_relation_language_not_current_duty_or_adoption"})
            combos = collections.Counter()
            for _, f in selected:
                active = sorted({e.get("technology") for e in f.get("tech", []) if e.get("technology") in TECH})
                combos["+".join(active) if active else "not_observed_by_rules"] += 1
            for combo, n in sorted(combos.items()):
                t3.append({"unit": unit, "group": group, "metric": "mutually_exclusive_technology_overlap", "technology": "all_families",
                           "role_or_overlap": combo, "experience_dimension": "not_applicable", "document_count": n,
                           "evidence_count": "", "document_denominator": denom, "document_fraction": frac(n, denom),
                           "status": "observed_text_candidate" if combo != "not_observed_by_rules" else "unknown_not_absence"})

    # T4: represented posting cohort composition and explicit unavailable fields.
    t4 = []
    for group in GROUPS:
        selected = [r for r in represented if applies(group, r.get("arm"))]
        denom = denominators["represented_posting"][group]
        year_counts = collections.Counter((r.get("cell") or {}).get("created_year") for r in selected)
        for year, n in sorted(year_counts.items(), key=lambda x: str(x[0])):
            missing_year = year is None
            t4.append({"unit": "represented_posting", "group": group, "metric": "created_year_snapshot_cohort",
                       "category": "missing_created_year" if missing_year else year,
                       "numerator": n, "denominator": denom, "fraction": frac(n, denom),
                       "availability": "not_available" if missing_year else "available_snapshot_metadata",
                       "claim_boundary": "missing_not_zero" if missing_year else "composition_not_historical_wording_trend"})
        shared = sum(1 for sha, ys in years_by_sha.items() if applies(group, next(iter(arm_by_sha[sha]))) and len(ys) > 1)
        uden = denominators["unique_exact_text"][group]
        t4.append({"unit": "unique_exact_text", "group": group, "metric": "exact_text_connected_to_multiple_created_year_values",
                   "category": "shared_text_across_metadata_cohorts", "numerator": shared, "denominator": uden,
                   "fraction": frac(shared, uden), "availability": "available_mapping_diagnostic",
                   "claim_boundary": "not_historic_versions_or_updates"})
    unavailable = [
        ("text_version_timestamps", "not_available"), ("listing_start_end", "not_available"),
        ("cross_quarter_year_2022_11_30_risk", "not_computable"),
        ("verified_company_key", "not_verified"), ("verified_occupation_key", "not_verified"),
        ("verified_geography_beyond_frozen_cell", "not_verified"), ("closed_job_text_immutability", "not_verified"),
    ]
    for metric, availability in unavailable:
        t4.append({"unit": "not_available", "group": "ALL", "metric": metric, "category": "not_available",
                   "numerator": "", "denominator": "", "fraction": "", "availability": availability,
                   "claim_boundary": "no_zero_and_no_historical_claim"})

    # T5: independent general/related indicators and entry/experience/responsibility cubes.
    t5 = []
    for unit in UNITS:
        for group in GROUPS:
            denom = denominators[unit][group]
            selected = [features[s] for s, arm in instances[unit] if applies(group, arm)]
            for definition, field in (("broad", "broad_objects"), ("narrow", "narrow_objects")):
                states = collections.Counter()
                for f in selected:
                    objs = f.get(field, set())
                    general = "general_work" in objs
                    related = bool(objs & {"occupation_task", "industry_domain", "tool"})
                    state = "both" if general and related else "general_only" if general else "related_only" if related else "neither_observed"
                    states[state] += 1
                if sum(states.values()) != denom:
                    raise RuntimeError("T5 comparison1 denominator failure")
                for state in ("both", "general_only", "related_only", "neither_observed"):
                    n = states[state]
                    t5.append({"unit": unit, "group": group, "comparison": "general_vs_related", "definition": definition,
                               "state": state, "numerator": n, "denominator": denom, "fraction": frac(n, denom),
                               "status": "unknown_not_absence" if state == "neither_observed" else "observed_text_candidate"})
            for entry_definition, entry_field in (("broad_entry_text", "entry_broad"), ("narrow_explicit_eligibility", "entry_narrow")):
                cube = collections.Counter()
                for f in selected:
                    exp = bool(f.get("broad_objects"))
                    entry = bool(f.get(entry_field))
                    resp = bool(f.get("responsibility"))
                    state = f"entry_{'observed' if entry else 'not_observed'}|experience_{'observed' if exp else 'not_observed'}|responsibility_{'observed' if resp else 'not_observed'}"
                    cube[state] += 1
                if sum(cube.values()) != denom:
                    raise RuntimeError("T5 comparison2 denominator failure")
                for state, n in sorted(cube.items()):
                    t5.append({"unit": unit, "group": group, "comparison": "entry_experience_responsibility_cooccurrence",
                               "definition": entry_definition, "state": state, "numerator": n, "denominator": denom,
                               "fraction": frac(n, denom), "status": "within_document_wording_cooccurrence"})
            mentoring_states = collections.Counter()
            for f in selected:
                duty = bool(f.get("mentoring_duty_candidate"))
                other = bool(f.get("mentoring_referent_or_prior_marker"))
                state = ("both_marker_types" if duty and other else "current_duty_candidate_only" if duty
                         else "referent_or_prior_experience_marker_not_current_duty" if other
                         else "no_mentoring_marker")
                mentoring_states[state] += 1
            if sum(mentoring_states.values()) != denom:
                raise RuntimeError("T5 mentoring classification denominator failure")
            for state in ("both_marker_types", "current_duty_candidate_only",
                          "referent_or_prior_experience_marker_not_current_duty", "no_mentoring_marker"):
                n = mentoring_states[state]
                t5.append({"unit": unit, "group": group, "comparison": "mentoring_marker_scope",
                           "definition": "duties_heading_no_cospan_experience_knowledge_education",
                           "state": state, "numerator": n, "denominator": denom, "fraction": frac(n, denom),
                           "status": "candidate_scope_classification_not_semantic_gold"})

    # T6: broad/narrow and explicit exclusion sensitivities with full denominators.
    t6 = []
    policies = {
        "all_evidence": lambda idx, e, f: True,
        "exclude_needs_review": lambda idx, e, f: e.get("outcome_status") == "explicit_rule_candidate",
        "exclude_conditional": lambda idx, e, f: e.get("scope") == "unconditional_explicit_clause",
        "exclude_background_heading": lambda idx, e, f: idx not in f.get("background_indices", set()),
        "exclude_review_conditional_background": lambda idx, e, f: (e.get("outcome_status") == "explicit_rule_candidate"
            and e.get("scope") == "unconditional_explicit_clause" and idx not in f.get("background_indices", set())),
    }
    for unit in UNITS:
        for group in GROUPS:
            denom = denominators[unit][group]
            selected = [features[s] for s, arm in instances[unit] if applies(group, arm)]
            for target in OBJECTS:
                for policy_name, keep in policies.items():
                    n = 0; retained = 0
                    for f in selected:
                        doc = False
                        for idx, e in f.get("experience", []):
                            if target in (e.get("objects") or []) and keep(idx, e, f):
                                retained += 1; doc = True
                        n += doc
                    t6.append({"unit": unit, "group": group, "target": target, "sensitivity": policy_name,
                               "numerator": n, "denominator": denom, "fraction": frac(n, denom),
                               "retained_evidence_count": retained, "not_observed": denom - n,
                               "claim_status": "allowed_observed_text_candidate",
                               "forbidden_claim": "semantic_accuracy_population_share_or_effect"})
            for target, field in (("entry_broad", "entry_broad"), ("entry_narrow", "entry_narrow")):
                n = sum(bool(f.get(field)) for f in selected)
                t6.append({"unit": unit, "group": group, "target": target, "sensitivity": "frozen_flag_definition",
                           "numerator": n, "denominator": denom, "fraction": frac(n, denom), "retained_evidence_count": "",
                           "not_observed": denom - n, "claim_status": "allowed_wording_cue_only",
                           "forbidden_claim": "validated_entry_job_share"})

    paths = {
        "T1_SAMPLE_COVERAGE_FUNNEL_PUBLIC.csv": (t1, ["unit", "group", "metric", "numerator", "denominator", "fraction", "status", "claim_boundary"]),
        "T2_EXPERIENCE_DIMENSIONS_PUBLIC.csv": (t2, ["unit", "group", "definition", "dimension", "clause_status", "strength", "scope", "duration_kind", "lower_years", "upper_years", "document_count", "evidence_count", "document_denominator", "document_fraction", "additivity"]),
        "T3_TECHNOLOGY_ROLE_OVERLAP_PUBLIC.csv": (t3, ["unit", "group", "metric", "technology", "role_or_overlap", "experience_dimension", "document_count", "evidence_count", "document_denominator", "document_fraction", "status"]),
        "T4_CREATED_YEAR_LIMITATIONS_PUBLIC.csv": (t4, ["unit", "group", "metric", "category", "numerator", "denominator", "fraction", "availability", "claim_boundary"]),
        "T5_CORE_COOCCURRENCES_PUBLIC.csv": (t5, ["unit", "group", "comparison", "definition", "state", "numerator", "denominator", "fraction", "status"]),
        "T6_SENSITIVITY_CLAIM_STATUS_PUBLIC.csv": (t6, ["unit", "group", "target", "sensitivity", "numerator", "denominator", "fraction", "retained_evidence_count", "not_observed", "claim_status", "forbidden_claim"]),
    }
    output_paths = []
    for name, (data, fields) in paths.items():
        path = outdir / name
        write_csv(path, data, fields)
        output_paths.append(path)

    # Compact numerical findings only; substantive conclusions remain root-owned.
    all_repr = [features[r["exact_text_sha256"]] for r in represented]
    summary = {
        "schema_version": "d56_summary_v1",
        "aggregation_release_version": "d56-final-tables-v2",
        "supersedes_job_id": "7977882",
        "supersedes_output_dir": "final_tables_v1",
        "status": "complete_observed_text_statistics",
        "scope": "unweighted frozen fixed sample; not all LinkUp or US postings",
        "denominators": denominators,
        "represented_key_counts": {
            "experience_evidence_observed": sum(bool(f.get("experience")) for f in all_repr),
            "numeric_duration_evidence_observed": sum(bool(f.get("numeric")) for f in all_repr),
            "overlay_relation_candidate_observed": sum(bool(f.get("overlay_rules")) for f in all_repr),
            "experience_not_observed_by_rules_unknown": sum(not f.get("experience") for f in all_repr),
            "entry_broad_text_cue": sum(bool(f.get("entry_broad")) for f in all_repr),
            "entry_narrow_explicit_eligibility_cue": sum(bool(f.get("entry_narrow")) for f in all_repr),
            "responsibility_candidate": sum(bool(f.get("responsibility")) for f in all_repr),
        },
        "T5_represented_general_related": {},
        "limitations": [
            "Observed-text candidates are not semantically validated latent requirements or preferences.",
            "No-match/not-observed is unknown, not confirmed absence.",
            "created_year is snapshot cohort metadata, not historical wording evidence.",
            "Legacy A/B/C arms are sampling groups, not treatments or current technology roles.",
        ],
    }
    for definition in ("broad", "narrow"):
        summary["T5_represented_general_related"][definition] = {
            row["state"]: row["numerator"] for row in t5
            if row["unit"] == "represented_posting" and row["group"] == "ALL"
            and row["comparison"] == "general_vs_related" and row["definition"] == definition
        }
    summary_path = outdir / "SUMMARY_PUBLIC.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_paths.append(summary_path)

    receipt = {
        "schema_version": "d56_final_tables_receipt_v1",
        "aggregation_release_version": "d56-final-tables-v2",
        "supersedes_job_id": "7977882",
        "supersedes_output_dir": "final_tables_v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete_aggregation_only",
        "job_id": os.environ.get("JOB_ID"), "host": socket.gethostname(),
        "elapsed_seconds": round(time.time() - started, 3), "api_calls": 0, "model_calls": 0,
        "input_sha256": {"baseline_full7635": digest(args.baseline), "overlay_full7635": digest(args.overlay),
                          "represented10000": digest(args.represented), "measurement_contract": digest(args.contract)},
        "code_sha256": digest(Path(__file__)), "rows": {"unique": 7635, "represented": 10000},
        "denominators": denominators, "span_checks": span_checks, "span_errors": span_errors,
        "overlay_index_checks": overlay_index_checks, "overlay_index_errors": overlay_index_errors,
        "outputs_sha256": {p.name: digest(p) for p in output_paths},
        "claim_level": contract.get("accepted_claim_level"), "estimator": contract.get("estimator"),
        "whole_corpus_coverage": "not_estimated; no new inventory scan or join",
        "substantive_variable_acceptance": "separate root review; successful aggregation and span checks are not semantic acceptance",
    }
    receipt_path = outdir / "FINAL_TABLES_RUN_RECEIPT_PUBLIC.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path)}, sort_keys=True))


if __name__ == "__main__":
    main()

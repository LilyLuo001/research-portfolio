#!/usr/bin/env python3
"""Summarize direct field changes among the 96 validated Wave02 reviews.

This is a reviewed-record accounting table, not an error-rate estimate and not
a population extrapolation. Unknown review outcomes retain their frozen value.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

from aggregate_wave02_before_after import apply_review

KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
ARMS = ("software_only", "any_ai")
QUESTION = {"experience": "experience_4dims",
            "entry_responsibility": "entry_responsibility_4dims"}
EXP_FIELDS = ("experience.general_work", "experience.occupation_task",
              "experience.industry_domain", "experience.tool_specific")
RESP_FIELDS = ("responsibility.independent_judgment", "responsibility.client_ownership",
               "responsibility.people_supervision", "responsibility.training_mentoring")
ENTRY_FIELDS = ("entry.explicit_target_wording",) + RESP_FIELDS
VERSION = "wave02-reviewed-record-impact-v1"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_jsonl(path):
    with open(path, encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def canonical_from_packet(row):
    value = row["canonical_key"]
    if not isinstance(value, list) or len(value) != 4:
        raise RuntimeError("packet canonical key is not the exact four-key list")
    return tuple(value)


def canonical_from_review(row):
    value = row["canonical_key"]
    if not isinstance(value, dict) or set(value) != set(KEY):
        raise RuntimeError("overlay canonical key is not the exact four-key object")
    return tuple(value[name] for name in KEY)


def baseline_from_packet(row):
    """Return only core fields whose frozen baseline exists in the packet.

    The packet has dimension-specific broad flags but only an across-dimension
    strength summary. Strength/conditionality auxiliary fields are therefore
    deliberately excluded from direct-change counts.
    """
    flags = row["baseline_flags"]
    before = {
        "experience.general_work": flags["current_general_work_broad"] is True,
        "experience.occupation_task": flags["current_occupation_task_broad"] is True,
        "experience.industry_domain": flags["current_industry_domain_broad"] is True,
        "experience.tool_specific": flags["current_tool_broad"] is True,
        "entry.explicit_target_wording": (
            flags["current_explicit_noexperience_candidate"] is True or
            flags["current_graduate_wording_candidate"] is True),
        "responsibility.independent_judgment": flags["current_independent_responsibility_wording"] is True,
        "responsibility.client_ownership": flags["current_client_ownership_wording"] is True,
        "responsibility.people_supervision": flags["current_people_supervision_wording"] is True,
        "responsibility.training_mentoring": flags["current_d57_duty_mentoring_candidate"] is True,
    }
    before["responsibility.any_broad"] = any(before[field] for field in RESP_FIELDS)
    before["responsibility.any_strict_current_duty"] = flags["current_strict_duty_responsibility_candidate"] is True
    return before


def unknown_fields(review):
    decision = review["decision"]
    if review["question"] == "experience_4dims":
        return {"experience." + item["dimension"] for item in decision["dimension_outcomes"]
                if item["ad_level_presence"] == "unknown"}
    result = set()
    if decision["entry"]["ad_level_presence"] == "unknown":
        result.add("entry.explicit_target_wording")
    for item in decision["responsibilities"]:
        if item["ad_level_presence"] == "unknown":
            result.add("responsibility." + item["dimension"])
    return result


def write_csv(path, rows):
    if not rows:
        raise RuntimeError("refusing empty output " + str(path))
    temp = Path(str(path) + ".tmp")
    with open(temp, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    os.replace(str(temp), str(path))


def write_json(path, value):
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(str(temp), str(path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--validated-overlay", required=True)
    parser.add_argument("--selection-counts", required=True,
                        help="Existing KS13_FIELD_SPECIFIC_COUNTS_PUBLIC.csv; supplies stratum population counts only")
    parser.add_argument("--validation-receipt", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    receipt = json.load(open(args.validation_receipt, encoding="utf-8"))
    if receipt.get("status") != "pass" or receipt.get("counts", {}).get("review_records") != 96:
        raise RuntimeError("validated review receipt is not the exact passing 96")
    packet = read_jsonl(args.packet); reviews = read_jsonl(args.validated_overlay)
    if len(packet) != 96 or len(reviews) != 96:
        raise RuntimeError("packet/overlay must each have exactly 96 rows")
    if receipt["inputs"]["packet_sha256"] != sha256(args.packet):
        raise RuntimeError("packet SHA does not match validation receipt")
    if receipt["private_overlay"]["sha256"] != sha256(args.validated_overlay):
        raise RuntimeError("overlay SHA does not match validation receipt")

    packet_by_key = {}
    for row in packet:
        key = canonical_from_packet(row)
        if key in packet_by_key: raise RuntimeError("duplicate packet key")
        packet_by_key[key] = row
    review_by_key = {}
    for row in reviews:
        key = canonical_from_review(row)
        if key in review_by_key: raise RuntimeError("duplicate overlay key")
        review_by_key[key] = row
    if set(packet_by_key) != set(review_by_key):
        raise RuntimeError("packet and validated overlay keys differ")

    eligible = {}
    with open(args.selection_counts, newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = (row["technology_arm"], QUESTION[row["question_group"]], row["stratum"])
            if key in eligible: raise RuntimeError("duplicate selection-count stratum")
            eligible[key] = int(row["numerator_ads"])

    coverage = collections.Counter(); changes = collections.Counter(); cross = collections.Counter()
    any_changed = collections.Counter(); question_totals = collections.Counter()
    for key, source in packet_by_key.items():
        review = review_by_key[key]
        question = QUESTION[source["question_group"]]
        if review["question"] != question:
            raise RuntimeError("question mismatch")
        arm = source["technology_arm"]; stratum = source["selection_stratum"]
        if review.get("technology_arm") != arm or review.get("selection_stratum") != stratum:
            raise RuntimeError("overlay arm/stratum mismatch")
        group = (arm, question, stratum); coverage[group] += 1; question_totals[(arm, question)] += 1
        before = baseline_from_packet(source)
        after, unresolved = apply_review(before, review)
        fields = EXP_FIELDS if question == "experience_4dims" else ENTRY_FIELDS
        unknown = unknown_fields(review)
        changed_fields = []
        for field in fields:
            b, a = before[field], after[field]
            if field in unknown and a != b:
                raise RuntimeError("unknown review outcome did not retain frozen value")
            state = "unchanged"
            if b is False and a is True: state = "false_to_true"
            elif b is True and a is False: state = "true_to_false"
            elif a != b: raise RuntimeError("non-boolean core field")
            if state != "unchanged": changed_fields.append(field)
            changes[group + (field, "reviewed")] += 1
            changes[group + (field, "before_true")] += int(b)
            changes[group + (field, "after_true")] += int(a)
            changes[group + (field, state)] += 1
            changes[group + (field, "unknown_retained")] += int(field in unknown)
        any_changed[group] += int(bool(changed_fields))
        if question == "entry_responsibility_4dims":
            cross[(arm, "before", before["entry.explicit_target_wording"], before["responsibility.any_broad"])] += 1
            cross[(arm, "after", after["entry.explicit_target_wording"], after["responsibility.any_broad"])] += 1

    coverage_rows = []
    for group in sorted(coverage):
        arm, question, stratum = group; selected = coverage[group]
        population = eligible.get(group)
        if population is None or selected > population:
            raise RuntimeError("missing/invalid existing stratum population count")
        coverage_rows.append({"technology_arm": arm, "question": question,
            "original_selection_stratum": stratum, "eligible_rule_stratum_ads": population,
            "selected_packet_ads": selected, "validated_review_ads": selected,
            "reviewed_ads_with_any_direct_core_change": any_changed[group],
            "selected_fraction_of_rule_stratum": selected / population if population else None,
            "design": "purposeful_balanced_review_not_accuracy_sample"})

    change_rows = []
    for group in sorted(coverage):
        arm, question, stratum = group
        fields = EXP_FIELDS if question == "experience_4dims" else ENTRY_FIELDS
        for field in fields:
            change_rows.append({"technology_arm": arm, "question": question,
                "original_selection_stratum": stratum, "field": field,
                "reviewed_ads": changes[group + (field, "reviewed")],
                "before_true": changes[group + (field, "before_true")],
                "after_true": changes[group + (field, "after_true")],
                "false_to_true": changes[group + (field, "false_to_true")],
                "true_to_false": changes[group + (field, "true_to_false")],
                "unchanged": changes[group + (field, "unchanged")],
                "unknown_retained_before": changes[group + (field, "unknown_retained")]})

    cross_rows = []
    reviewed_entry_records = sum(question_totals[(arm, "entry_responsibility_4dims")] for arm in ARMS)
    if reviewed_entry_records != 36:
        raise RuntimeError("entry/responsibility reviewed-record count is not the frozen 36")
    for arm in ARMS:
        for version in ("before", "after"):
            for entry in (False, True):
                for responsibility in (False, True):
                    cross_rows.append({"technology_arm": arm, "version": version,
                        "explicit_entry_target_wording": entry,
                        "any_broad_responsibility": responsibility,
                        "reviewed_ads": cross[(arm, version, entry, responsibility)],
                        "scope": "36_entry_responsibility_question_records_only"})

    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "REVIEW_COVERAGE_BY_STRATUM_PUBLIC.csv", coverage_rows)
    write_csv(output / "DIRECT_CORE_FIELD_CHANGES_PUBLIC.csv", change_rows)
    write_csv(output / "ENTRY_RESPONSIBILITY_REVIEWED36_CROSSTAB_PUBLIC.csv", cross_rows)
    summary = {"version": VERSION, "status": "pass",
        "reviewed_records": len(reviews),
        "reviewed_by_question_and_arm": {"{}|{}".format(k[0], k[1]): v for k, v in sorted(question_totals.items())},
        "reviewed_records_with_any_direct_core_change": sum(any_changed.values()),
        "reviewed_direct_core_field_instances_changed": sum(changes[g + (f, "false_to_true")] + changes[g + (f, "true_to_false")] for g in coverage for f in (EXP_FIELDS if g[1] == "experience_4dims" else ENTRY_FIELDS)),
        "strength_auxiliary_changes_counted": False,
        "unknown_policy": "unknown retains the frozen before value and is counted separately",
        "entry_responsibility_crosstab_scope": "the 36 reviewed entry/responsibility records only",
        "claim_boundary": "direct effects on exact reviewed records; purposeful selection is not a population error rate and no change is propagated",
        "inputs": {"packet_sha256": sha256(args.packet), "validated_overlay_sha256": sha256(args.validated_overlay),
                   "validation_receipt_sha256": sha256(args.validation_receipt), "selection_counts_sha256": sha256(args.selection_counts)}}
    write_json(output / "REVIEW_IMPACT_SUMMARY_PUBLIC.json", summary)
    outputs = {}
    for path in sorted(output.iterdir()):
        if path.name != "RUN_RECEIPT_PUBLIC.json" and path.is_file():
            outputs[path.name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    write_json(output / "RUN_RECEIPT_PUBLIC.json", {"version": VERSION, "status": "pass",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scheduler_job_id": os.environ.get("SLURM_JOB_ID"),
        "checks": {"validated_exact_96": True, "packet_overlay_exact_key_match": True,
                   "unknown_retains_before": True, "core_fields_only": True,
                   "entry_responsibility_reviewed_records_36": True},
        "outputs": outputs, "api_calls": 0, "model_calls": 0})


if __name__ == "__main__":
    main()

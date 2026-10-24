#!/usr/bin/env python3
"""SCNet scheduler-only recovery of accepted original review items; no new labels.

This is a recoverability gate, not a model trainer or an entity pair generator.
Input manifest: {"freeze": {"path":..., "sha256":...},
 "sources": [{"path":..., "sha256":...}],
 "packets": [{"path":..., "sha256":...}]}. Sources must be the exact files
named by ledger provenance (usually combined validated reviews), not substitutes.
Missing source files/packets and absent entity spans are explicitly unsupported.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path

HOLDOUT_SHA = "5d37e0d5840d99f6d9f52d7cc6e2573bd0ca89d7bc948d121a7c9684b36e5de1"
FAMILY_FIELDS = {
    "experience_object": ("experience_clauses", ("object",)),
    "experience_strength": ("experience_clauses", ("object", "strength")),
    "experience_literal_years": ("experience_clauses", ("object", "years_min", "years_max", "years_relation")),
    "qualification_conditions_and_alternatives": ("experience_clauses", ("object", "conditionality", "alternative_group", "alternative_branch")),
    "entry_wording_and_scope": ("entry_items", ("target", "conditionality")),
    "current_responsibility_subject_and_relation": ("responsibility_items", ("dimension", "subject", "relation", "conditionality")),
    "technology_category_and_role": ("technology_items", ("technology", "family", "role")),
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def checked(item):
    if sha(item["path"]) != item["sha256"]:
        raise RuntimeError("input SHA mismatch: " + item["path"])
    return item["path"]


def split(context, final, legacy):
    if context in final:
        return "final_previously_exposed"
    return "previous_holdout_reserved_not_final" if legacy.is_holdout(context) else "train"


def occurrences(text, quote):
    out, start = [], 0
    while quote:
        found = text.find(quote, start)
        if found < 0:
            break
        out.append({"start": found, "end": found + len(quote)})
        start = found + 1
    return out


def write(path, obj, lines=False):
    with open(path, "x", encoding="utf-8") as f:
        os.chmod(path, 0o600)
        if lines:
            for item in obj:
                f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
        else:
            json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("must run as an actual SCNet Slurm job")
    if Path(a.output).exists():
        raise RuntimeError("output must be a new directory")
    manifest = json.loads(Path(a.manifest).read_text())
    freeze = json.loads(Path(checked(manifest["freeze"])).read_text())
    inputs = freeze["inputs"]
    for item in inputs.values():
        checked(item)
    if inputs["holdout"]["sha256"] != HOLDOUT_SHA:
        raise RuntimeError("holdout identity changed")
    final = {r["normalized_context_sha256"] for r in rows(inputs["holdout"]["path"])}
    if len(final) != 1331:
        raise RuntimeError("final holdout cardinality changed")
    isolated = {r["normalized_context_sha256"] for r in rows(inputs["isolation"]["path"])}
    ledger = list(rows(inputs["ledger"]["path"]))
    legacy = module(inputs["legacy"]["path"], "frozen_legacy_adapter")
    source_files, raw = {}, {}
    for item in manifest["sources"]:
        source_files[item["sha256"]] = checked(item)
        for r in rows(item["path"]):
            key = (item["sha256"], str(r.get("record_id")))
            if key in raw:
                raise RuntimeError("duplicate source record binding")
            raw[key] = r
    packets = {}
    for item in manifest.get("packets", []):
        for r in rows(checked(item)):
            c = r.get("context_sha256")
            text = r.get("full_document")
            if c is None or not isinstance(text, str):
                continue
            if hashlib.sha256(text.encode()).hexdigest() != c:
                raise RuntimeError("packet complete input SHA mismatch")
            if c in packets and packets[c] != text:
                raise RuntimeError("packet context conflict")
            packets[c] = text
    if manifest.get("use_frozen_frame_contexts", False):
        import pyarrow.parquet as pq
        normalizer = legacy.load_normalizer(inputs["normalizer"]["path"])
        cached = set()
        for r in pq.read_table(inputs["frame"]["path"], columns=["exact_text_sha256", "original_text", "arm"]).to_pylist():
            raw_sha, original = r["exact_text_sha256"], r["original_text"] or ""
            if raw_sha in cached:
                continue
            cached.add(raw_sha)
            if hashlib.sha256(original.encode()).hexdigest() != raw_sha:
                raise RuntimeError("frozen frame raw SHA mismatch")
            text = legacy.normalize(normalizer, original)
            c = hashlib.sha256(text.encode()).hexdigest()
            if c in packets and packets[c] != text:
                raise RuntimeError("frozen context collision")
            packets[c] = text
    counts, gaps, recovered, seen = collections.Counter(), [], [], {}
    accepted = {}
    for cell in ledger:
        if cell["status"] == "known" and len(cell.get("provenance", [])) == 1:
            v = cell["provenance"][0]
            accepted[(cell["normalized_context_sha256"], cell["field_family"])] = (v.get("source_sha256"), str(v.get("source_record_id")))
    support = collections.defaultdict(set)
    chain_support = collections.defaultdict(set)
    qualification_groups = []
    for cell in ledger:
        c, family = cell["normalized_context_sha256"], cell["field_family"]
        identity = (c, family)
        # Same accepted source can bind directly to one ad and by exact context
        # reuse to another. Only this transport/binding distinction is ignored;
        # all status, semantic values and remaining provenance must still agree.
        signature_value = {k: cell.get(k) for k in ("status", "structured_value", "provenance")}
        signature_value["provenance"] = [{k: value for k, value in v.items() if k != "binding_mode"} for v in cell.get("provenance", [])]
        signature = json.dumps(signature_value, sort_keys=True)
        if identity in seen:
            if seen[identity] != signature:
                raise RuntimeError("inconsistent same-context family acceptance masks")
            continue
        seen[identity] = signature
        state = cell["status"]
        counts["family_state|" + family + "|" + state] += 1
        if c in isolated or state not in ("known", "not_applicable"):
            continue
        provenance = cell.get("provenance", [])
        compatible = [v for v in provenance if v.get("source") == "formal800_final" or re.fullmatch(r"fixed10k_batch(?:00[1-9]|0[1-6][0-9])", v.get("source", ""))]
        # No selecting one among competing provenance entries, even if values agree.
        if len(provenance) != 1 or len(compatible) != 1:
            gaps.append(dict(context=c, family=family, reason="non_single_compatible_original_source")); continue
        v = compatible[0]
        r = raw.get((v.get("source_sha256"), str(v.get("source_record_id"))))
        if r is None:
            gaps.append(dict(context=c, family=family, reason="exact_original_source_unavailable", source_sha256=v.get("source_sha256"))); continue
        if r.get("context_sha256") != c or v.get("source_context_sha256") != c:
            raise RuntimeError("source record/context binding mismatch")
        if r.get("document_status") != "reviewed_full":
            gaps.append(dict(context=c, family=family, reason="original_not_reviewed_full")); continue
        if state == "not_applicable":
            counts["accepted_document_nonmention_not_pair_negative|" + family] += 1
            if family != "qualification_conditions_and_alternatives":
                continue
        if c not in packets:
            gaps.append(dict(context=c, family=family, reason="complete_context_packet_unavailable")); continue
        if family == "qualification_conditions_and_alternatives":
            referenced_groups = {x.get("alternative_group") for x in r["experience_clauses"] if x.get("alternative_group") is not None}
            group_ids = [g["group"] for g in r["qualification_alternatives"]]
            for gi, group_item in enumerate(r["qualification_alternatives"]):
                group_path = "/qualification_alternatives/" + str(gi)
                branches = group_item["branches"]
                branch_ids = [b["branch"] for b in branches]
                group_spans = [{"branch": b["branch"], "quote": q, "occurrences": occurrences(packets[c], q)} for b in branches for q in b.get("quotes", [])]
                if group_ids.count(group_item["group"]) != 1 or len(branch_ids) != len(set(branch_ids)):
                    gaps.append(dict(context=c, family=family, path=group_path, reason="group_branch_keys_not_unique")); continue
                if not branches or not group_spans or any(not b.get("quotes") for b in branches) or any(not s["occurrences"] for s in group_spans):
                    gaps.append(dict(context=c, family=family, path=group_path, reason="group_exact_quote_missing")); continue
                if group_item["relation"] not in ("OR", "AND"):
                    gaps.append(dict(context=c, family=family, path=group_path, reason="unresolved_original_group_relation")); continue
                qualification_groups.append(dict(context_sha256=c, context_ref="CONTEXTS_PRIVATE.jsonl#" + c,
                    split=split(c, final, legacy), source_sha256=v["source_sha256"], source_record_id=v["source_record_id"],
                    original_group_path=group_path, original_group=group_item, evidence=group_spans,
                    accepted_family_status=state, inventory_only=True,
                    referenced_by_experience=group_item["group"] in referenced_groups))
        if state == "not_applicable":
            continue
        field, keys = FAMILY_FIELDS[family]
        for index, item in enumerate(r[field]):
            path = "/" + field + "/" + str(index)
            quotes = item.get("quotes", [])
            spans = [{"quote": q, "occurrences": occurrences(packets[c], q)} for q in quotes]
            if not spans or any(not s["occurrences"] for s in spans):
                gaps.append(dict(context=c, family=family, path=path, reason="exact_quote_missing")); continue
            if any(item.get(k) in ("unresolved", "unknown") for k in keys):
                gaps.append(dict(context=c, family=family, path=path, reason="unresolved_original_item")); continue
            record = dict(context_sha256=c, field_family=family, split=split(c, final, legacy),
                          source_sha256=v["source_sha256"], source_record_id=v["source_record_id"],
                          source=v["source"], original_item_path=path,
                          labels={k: item[k] for k in keys}, original_item_audit_only=item, evidence=spans,
                          context_ref="CONTEXTS_PRIVATE.jsonl#" + c, entity_pair_ready=False,
                          binding_gap="original_schema_has_quote_spans_but_no_separate_entity_argument_spans")
            # Explicit group/branch IDs are the only cross-item relation key.
            if family == "qualification_conditions_and_alternatives":
                group, branch = item.get("alternative_group"), item.get("alternative_branch")
                groups = [g for g in r["qualification_alternatives"] if g["group"] == group] if group else []
                if group and (len(groups) != 1 or (branch and sum(b["branch"] == branch for b in groups[0]["branches"]) != 1)):
                    gaps.append(dict(context=c, family=family, path=path, reason="explicit_group_branch_not_unique")); continue
                record["explicit_qualification_group"] = groups[0] if groups else None
                group_evidence = [{"quote": q, "occurrences": occurrences(packets[c], q)} for g in groups for b in g["branches"] for q in b.get("quotes", [])]
                if any(not s["occurrences"] for s in group_evidence):
                    gaps.append(dict(context=c, family=family, path=path, reason="group_exact_quote_missing")); continue
                record["qualification_group_evidence"] = group_evidence
            recovered.append(record)
            partition = record["split"]
            for k in keys:
                if k in ("technology", "alternative_group", "alternative_branch"):
                    # Free-text names and local relation IDs stay private, not
                    # public class labels or apparent transferable taxonomies.
                    continue
                # Context-level supports avoid inflated sample size from repeated
                # ads, items, or quotes. Null is an original value, not a negative.
                label = json.dumps(item[k], sort_keys=True, ensure_ascii=False)
                support[(family + ":" + k, label, partition)].add(c)
            if field == "experience_clauses":
                needed = ("experience_object", "experience_strength", "experience_literal_years", "qualification_conditions_and_alternatives")
                source_key = (v["source_sha256"], str(v["source_record_id"]))
                if all(accepted.get((c, f)) == source_key for f in needed):
                    record["accepted_same_item_experience_tuple"] = {k: item[k] for k in ("object", "strength", "years_min", "years_max", "years_relation", "conditionality", "alternative_group", "alternative_branch")}
                    chain_support[(partition, item["object"])].add((c, path))
                    counts["complete_experience_chain_unique_context|" + partition] = len({x[0] for (s, _), values in chain_support.items() if s == partition for x in values})
            counts["recovered_original_item|" + family + "|" + record["split"]] += 1
            counts["repeated_quote_items"] += any(len(s["occurrences"]) > 1 for s in spans)
            counts["unique_quote_items"] += all(len(s["occurrences"]) == 1 for s in spans)
    root = Path(a.output); root.mkdir(parents=True, mode=0o700)
    recovered_contexts = sorted({r["context_sha256"] for r in recovered + qualification_groups})
    write(root / "CONTEXTS_PRIVATE.jsonl", ({"context_sha256": c, "complete_context": packets[c]} for c in recovered_contexts), True)
    write(root / "RECOVERED_ORIGINAL_ITEMS_PRIVATE.jsonl", recovered, True)
    write(root / "QUALIFICATION_GROUPS_PRIVATE.jsonl", qualification_groups, True)
    write(root / "BINDING_GAPS_PRIVATE.jsonl", gaps, True)
    support_rows = [{"task": task, "class": label, "split": partition, "unique_contexts": len(values)} for (task, label, partition), values in sorted(support.items())]
    gates = []
    for task, label in sorted({(t, l) for t, l, _ in support}):
        train = len(support.get((task, label, "train"), set()))
        final_n = len(support.get((task, label, "final_previously_exposed"), set()))
        gates.append(dict(task=task, **{"class": label}, train_unique_contexts=train, final_unique_contexts=final_n,
                          train50_final50_pass=train >= 50 and final_n >= 50))
    group_support = []
    for partition, relation in sorted({(g["split"], g["original_group"]["relation"]) for g in qualification_groups}):
        selected = [g for g in qualification_groups if g["split"] == partition and g["original_group"]["relation"] == relation]
        group_support.append(dict(split=partition, relation=relation, unique_contexts=len({g["context_sha256"] for g in selected}),
                                  groups=len(selected), branches=sum(len(g["original_group"]["branches"]) for g in selected),
                                  groups_not_referenced_by_experience=sum(not g["referenced_by_experience"] for g in selected)))
    report = dict(version="relation-supervision-recoverability-v1", scheduler_job_id=os.environ["SLURM_JOB_ID"],
                  code_sha256=sha(__file__), manifest_sha256=sha(a.manifest), counts=dict(sorted(counts.items())),
                  unique_materialized_contexts=len(recovered_contexts),
                  gap_counts=dict(collections.Counter(g["reason"] for g in gaps)),
                  entity_pair_ready_rows=0, generated_no_relation_rows=0,
                  support_by_task_class_split=support_rows, frozen_support_gate=gates,
                  qualification_group_support_by_split_relation=group_support,
                  complete_experience_chain_item_support=[dict(split=s, object=o, original_items=len(values), unique_contexts=len({x[0] for x in values})) for (s, o), values in sorted(chain_support.items())],
                  explicit_branch_items=sum(bool(r["labels"].get("alternative_branch")) for r in recovered),
                  shared_condition_group_items=sum(bool(r["labels"].get("alternative_group")) and r["labels"].get("alternative_branch") is None for r in recovered),
                  decision="inventory_only_no_model_authorized_by_this_script",
                  limitations=["Original clause-level labels are preserved, not entity spans or new annotations.",
                               "Within-item field bindings are real; explicit entity endpoint span supervision is absent from this original schema.",
                               "Entity-pair route remains unsupported; no_relation pair supervision is absent.",
                               "No cross-family positional joins; no unknown or document nonmention pair negatives.",
                               "Final 1331 and all old hash holdout members remain excluded from training."])
    write(root / "RECOVERABILITY_PUBLIC.json", report)


if __name__ == "__main__":
    main()

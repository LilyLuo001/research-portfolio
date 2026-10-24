#!/usr/bin/env python3
"""One fixed, scheduler-only frozen-candidate technology attribute preparation.

No training, resampling, new labels, parser edits, reference-selected windows, or
corpus traversal. Run only on the already recovered bounded context inventory.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

ROLES = ("background_mention", "develop_technology", "implement_deploy_technology", "use_tool_for_work")
SPLITS = ("train", "final_previously_exposed", "previous_holdout_reserved_not_final")
HOLDOUT_SHA = "5d37e0d5840d99f6d9f52d7cc6e2573bd0ca89d7bc948d121a7c9684b36e5de1"
RADIUS = 192


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


def write(path, obj, lines=False):
    with open(path, "x", encoding="utf-8") as f:
        os.chmod(path, 0o600)
        if lines:
            for r in obj:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        else:
            json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def checked(item):
    if sha(item["path"]) != item["sha256"]:
        raise RuntimeError("frozen input digest mismatch")
    return item["path"]


def candidates(rule, context, text, partition):
    """This function has no reference-item/label/quote argument or dependency."""
    result = rule.extract(text)
    if result.get("status") != "processed":
        return [], "frozen_engine_invalid_context"
    if result.get("normalized_text") != text:
        return [], "frozen_normalization_not_idempotent"
    out = {}
    # The old engine records clause offsets and term text but omits term offsets.
    # Reapply its EXACT compiled regex in its EXACT evidence clause, without a
    # changed parser or additional vocabulary; enforce emitted-term conservation.
    groups = collections.defaultdict(list)
    for ev in result["evidence"]:
        if ev.get("kind") == "technology":
            groups[(ev["start"], ev["end"], ev["technology"])].append(ev)
    for (start, end, family), emitted in groups.items():
        quote = text[start:end]
        if any(ev["quote"] != quote for ev in emitted):
            raise RuntimeError("frozen evidence coordinate mismatch")
        matches = list(rule.TECH[family].finditer(quote))
        if [m.group(0) for m in matches] != [e["term"] for e in emitted]:
            raise RuntimeError("frozen entity offset reconstruction mismatch")
        for m, ev in zip(matches, emitted):
            left, right = start + m.start(), start + m.end()
            key = (left, right, family)
            if key in out:
                raise RuntimeError("duplicate frozen candidate")
            lo, hi = max(0, left - RADIUS), min(len(text), right + RADIUS)
            model_input = text[lo:left] + "[TECH]" + text[left:right] + "[/TECH]" + text[right:hi]
            cid = hashlib.sha256((context + "|%d|%d|%s" % key).encode()).hexdigest()
            out[key] = dict(candidate_id=cid, context_sha256=context, split=partition,
                            term=text[left:right], frozen_family=family,
                            entity_start=left, entity_end=right, clause_start=start, clause_end=end,
                            window_start=lo, window_end=hi, model_input=model_input,
                            frozen_negated=ev.get("negated"),
                            candidate_source="frozen_rulefirst_v1_2_technology_evidence")
    return sorted(out.values(), key=lambda x: (x["entity_start"], x["entity_end"], x["frozen_family"])), "processed"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--recovered", required=True)
    p.add_argument("--input-manifest", required=True, help="Original checked recovery manifest")
    p.add_argument("--frozen-rule-dir", required=True)
    p.add_argument("--expected-rule-sha256", required=True)
    p.add_argument("--expected-legacy-sha256", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    if not os.getenv("SLURM_JOB_ID"):
        raise RuntimeError("actual scheduled SCNet job required")
    root = Path(a.output)
    if root.exists():
        raise RuntimeError("create-only output directory already exists")
    frozen = Path(a.frozen_rule_dir)
    if sha(frozen / "rule_engine.py") != a.expected_rule_sha256 or sha(frozen / "legacy_v5_frozen.py") != a.expected_legacy_sha256:
        raise RuntimeError("approved frozen engine identity mismatch")
    sys.path.insert(0, str(frozen))
    import rule_engine as rule
    if rule.VERSION != "rulefirst-20261008-v1.2":
        raise RuntimeError("wrong frozen engine version")
    manifest = json.loads(Path(a.input_manifest).read_text())
    freeze = json.loads(Path(checked(manifest["freeze"])).read_text())
    inputs = freeze["inputs"]
    if inputs["holdout"]["sha256"] != HOLDOUT_SHA:
        raise RuntimeError("original final holdout identity changed")
    final = {r["normalized_context_sha256"] for r in rows(checked(inputs["holdout"]))}
    if len(final) != 1331:
        raise RuntimeError("original final holdout size changed")
    legacy = load(checked(inputs["legacy"]), "original_holdout_adapter")
    recovered = Path(a.recovered)
    context_path = recovered / "CONTEXTS_PRIVATE.jsonl"
    item_path = recovered / "RECOVERED_ORIGINAL_ITEMS_PRIVATE.jsonl"
    # Context split is determined independently from original frozen exclusions.
    def partition(c):
        if c in final:
            return SPLITS[1]
        return SPLITS[2] if legacy.is_holdout(c) else SPLITS[0]
    context_states, by_context, seen = [], {}, set()
    for row in rows(context_path):
        c, text = row["context_sha256"], row["complete_context"]
        if c in seen or hashlib.sha256(text.encode()).hexdigest() != c:
            raise RuntimeError("recovered complete context identity mismatch")
        seen.add(c)
        cand, state = candidates(rule, c, text, partition(c))
        by_context[c] = cand
        context_states.append(dict(context_sha256=c, split=partition(c), state=state, candidates=len(cand)))
    root.mkdir(parents=True, mode=0o700)
    flat = [x for c in sorted(by_context) for x in by_context[c]]
    # Persist production inputs before opening any teacher artifact.
    write(root / "CANDIDATES_PRIVATE.jsonl", flat, True)
    write(root / "CONTEXT_STATES_PRIVATE.jsonl", context_states, True)
    write(root / "LABEL_DICTIONARY.json", dict(label_to_id={r: i for i, r in enumerate(ROLES)}, target="technology_role_attribute_only"))
    refs, links = [], collections.defaultdict(list)
    support = collections.defaultdict(set)
    for index, row in enumerate(rows(item_path)):
        if row["field_family"] != "technology_category_and_role":
            continue
        c, labels = row["context_sha256"], row["labels"]
        if c not in seen or row["split"] != partition(c):
            raise RuntimeError("reference split/context mismatch")
        role, term = labels.get("role"), labels.get("technology")
        if role not in ROLES or not isinstance(term, str) or not term:
            raise RuntimeError("reference original role/name incompatible; no taxonomy conversion allowed")
        evidence = row.get("evidence", [])
        spans = [s for e in evidence for s in e.get("occurrences", [])]
        # References may only assess coverage/associate supervision; they never
        # add candidates or choose/modify the model input window.
        matched = [x for x in by_context[c] if x["term"].casefold() == term.casefold()
                   and any(s["start"] <= x["entity_start"] and x["entity_end"] <= s["end"] for s in spans)]
        rid = hashlib.sha256((c + "|" + str(index) + "|" + row["original_item_path"]).encode()).hexdigest()
        repeated_evidence = any(len(e.get("occurrences", [])) > 1 for e in evidence)
        state = ("ambiguous_reference_evidence_occurrences" if repeated_evidence
                 else "matched_unique" if len(matched) == 1
                 else "matched_multiple_occurrences" if matched
                 else "unmatched_frozen_candidate")
        ref = dict(reference_id=rid, context_sha256=c, split=row["split"], labels=labels,
                   source_sha256=row["source_sha256"], source_record_id=row["source_record_id"],
                   original_item_path=row["original_item_path"], candidate_ids=[x["candidate_id"] for x in matched],
                   localization_state=state, evidence=evidence)
        refs.append(ref)
        support[(row["split"], role, "reference")].add(c)
        if matched:
            support[(row["split"], role, "candidate_covered")].add(c)
        for candidate in matched:
            links[candidate["candidate_id"]].append(ref)
    associated, fit_rows = [], []
    for x in flat:
        linked = links[x["candidate_id"]]
        roles = {r["labels"]["role"] for r in linked}
        if not linked:
            state = "unlabeled_candidate_no_negative"
        elif len(roles) > 1:
            state = "conflicting_reference_roles"
        elif any(r["localization_state"] != "matched_unique" for r in linked):
            state = "ambiguous_reference_occurrences"
        elif len(linked) > 1:
            state = "duplicate_or_multiple_reference_items"
        else:
            state = "compatible_unique_reference"
        record = dict(candidate_id=x["candidate_id"], context_sha256=x["context_sha256"], split=x["split"],
                      supervision_state=state, reference_ids=[r["reference_id"] for r in linked])
        if state == "compatible_unique_reference":
            role = next(iter(roles))
            record.update(label=role, label_id=ROLES.index(role))
            support[(x["split"], role, "compatible")].add(x["context_sha256"])
            # Holdouts may be evaluated but are never in the training file.
            if x["split"] == "train":
                fit_rows.append(dict(x, label=role, label_id=ROLES.index(role)))
        associated.append(record)
    write(root / "REFERENCE_COVERAGE_PRIVATE.jsonl", refs, True)
    write(root / "CANDIDATE_SUPERVISION_PRIVATE.jsonl", associated, True)
    write(root / "TRAIN_COMPATIBLE_PRIVATE.jsonl", fit_rows, True)
    counts = []
    for s in SPLITS:
        for role in ROLES:
            selected = [r for r in refs if r["split"] == s and r["labels"]["role"] == role]
            counts.append(dict(split=s, role=role, reference_items=len(selected),
                               candidate_covered_items=sum(bool(r["candidate_ids"]) for r in selected),
                               reference_unique_contexts=len(support[(s, role, "reference")]),
                               candidate_covered_unique_contexts=len(support[(s, role, "candidate_covered")]),
                               compatible_unique_contexts=len(support[(s, role, "compatible")]),
                               reference_localization_states=dict(collections.Counter(r["localization_state"] for r in selected))))
    report = dict(version="fixed-nonoracle-technology-attribute-input-v1", scheduler_job_id=os.environ["SLURM_JOB_ID"],
                  code_sha256=sha(__file__), input_manifest_sha256=sha(a.input_manifest),
                  inputs={"contexts_sha256": sha(context_path), "items_sha256": sha(item_path),
                          "rule_engine_sha256": a.expected_rule_sha256, "legacy_sha256": a.expected_legacy_sha256},
                  input_scheme=dict(frozen_version=rule.VERSION, radius_unicode_codepoints=RADIUS,
                                    entity_markers=["[TECH]", "[/TECH]"], supervised_name_match="casefold_exact_literal",
                                    scope="recovered_contexts_only_attribute_classification"),
                  total_contexts=len(seen), production_candidates=len(flat), original_technology_reference_items=len(refs),
                  train_compatible_candidates=len(fit_rows), support_by_split_role=counts,
                  context_states=dict(collections.Counter(r["state"] for r in context_states)),
                  candidate_supervision_states_by_split={s: dict(collections.Counter(r["supervision_state"] for r in associated if r["split"] == s)) for s in SPLITS},
                  reference_localization_states=dict(collections.Counter(r["localization_state"] for r in refs)),
                  original_final_holdout_contexts=len(final), generated_negative_examples=0,
                  limitations=["Every original technology reference, including unmatched items, remains in candidate-recall denominator.",
                               "Coverage is reported on recovered bounded contexts only, not corpus/frame accuracy.",
                               "Reference names/evidence associate supervision only; production candidate inputs precede teacher reads.",
                               "Exact literal matching is conservative: no alias inference, label repairs, or dictionary additions.",
                               "Repeated, duplicate, conflicting and unlabeled candidates retain explicit states and are excluded from fit.",
                               "This is technology role attribute classification, not entity-pair or end-to-end relation extraction.",
                               "Final was previously exposed. Original 1331 final and all legacy holdouts remain excluded from training."])
    report["outputs"] = {p.name: sha(p) for p in sorted(root.iterdir()) if p.is_file()}
    write(root / "PREPARATION_PUBLIC.json", report)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""One fixed scheduled year-mention to original experience-object contextual fit.

Derived from the retained unexecuted technology-role draft; no model search,
new labels, inferred negatives, downloads, changed splits, or automatic reruns.
Public files contain aggregate metrics/digests; all row sidecars stay private.
"""
import argparse
import collections
import hashlib
import json
import os
import random
import re
import signal
import sys
import time
import traceback
from pathlib import Path

CLASSES = ()  # Loaded intact from the checked original-label dictionary.
SPLITS = ("train", "final_previously_exposed", "previous_holdout_reserved_not_final")
MARKERS = ("[YEAR]", "[/YEAR]")
FIXED = dict(seed=1729, epochs=3, learning_rate=2e-5, optimizer="AdamW",
             weight_decay=0.01, max_length=256, batch_size=4,
             gradient_accumulation_steps=8, precision="fp32", class_weights=None,
             model_selection="final_epoch_only", scheduler=None, warmup_steps=0)
DATA_FILES = ("CANDIDATES_PRIVATE.jsonl", "CONTEXT_STATES_PRIVATE.jsonl",
              "LABEL_DICTIONARY.json", "CANDIDATE_SUPERVISION_PRIVATE.jsonl",
              "TRAIN_COMPATIBLE_PRIVATE.jsonl", "EVAL_COMPATIBLE_PRIVATE.jsonl", "REFERENCE_COVERAGE_PRIVATE.jsonl",
              "PREPARATION_PUBLIC.json")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def rows(path):
    with open(path, encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write(path, obj):
    with open(path, "x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(obj, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")


def counts(records, label_field=None):
    out = {}
    for split in SPLITS:
        group = [r for r in records if r["split"] == split]
        result = dict(items=len(group), unique_contexts=len({r["context_sha256"] for r in group}))
        if label_field:
            result["by_class"] = {role: dict(
                items=sum(r[label_field] == role for r in group),
                unique_contexts=len({r["context_sha256"] for r in group if r[label_field] == role}))
                for role in CLASSES}
        out[split] = result
    return out


def model_identity(model_dir, manifest_path):
    manifest = read_json(manifest_path)
    if manifest.get("repo_id") != "FacebookAI/xlm-roberta-base" or not re.fullmatch(r"[0-9a-f]{40}", manifest.get("revision", "")):
        raise RuntimeError("one pinned FacebookAI/xlm-roberta-base commit required")
    declared = manifest.get("files", {})
    if not isinstance(declared, dict) or not declared:
        raise RuntimeError("checkpoint manifest files are required")
    for name in declared:
        p = Path(name)
        if p.is_absolute() or ".." in p.parts or not re.fullmatch(r"[0-9a-f]{64}", declared[name]):
            raise RuntimeError("invalid checkpoint manifest entry")
    actual = {str(p.relative_to(model_dir)) for p in model_dir.rglob("*") if p.is_file()}
    if actual != set(declared):
        raise RuntimeError("checkpoint file inventory differs from pin manifest")
    for name, digest in declared.items():
        if sha(model_dir / name) != digest:
            raise RuntimeError("checkpoint digest mismatch")
    if not {"config.json", "sentencepiece.bpe.model"}.issubset(actual):
        raise RuntimeError("fixed XLM-R config/tokenizer files missing")
    if not ({"pytorch_model.bin", "pytorch_model.bin.index.json"} & actual):
        raise RuntimeError("existing torch-compatible checkpoint weights missing")
    return dict(repo_id=manifest["repo_id"], revision=manifest["revision"], files=declared,
                manifest_sha256=sha(manifest_path))


def load_inputs(data_dir):
    digests = {name: sha(data_dir / name) for name in DATA_FILES}
    preparation = read_json(data_dir / "PREPARATION_PUBLIC.json")
    if preparation.get("version") != "year-object-original-same-item-binding-v1":
        raise RuntimeError("wrong frozen production input schema")
    for name in DATA_FILES[:-1]:
        if preparation.get("outputs", {}).get(name) != digests[name]:
            raise RuntimeError("preparation output digest mismatch")
    global CLASSES
    label_map = read_json(data_dir / "LABEL_DICTIONARY.json")["label_to_id"]
    if (not isinstance(label_map, dict) or not label_map or
            any(not isinstance(k, str) or not k or type(v) is not int for k, v in label_map.items()) or
            sorted(label_map.values()) != list(range(len(label_map)))):
        raise RuntimeError("original class dictionary must contain contiguous unique IDs")
    CLASSES = tuple(sorted(label_map, key=label_map.get))
    if list(CLASSES) != preparation.get("label_classes"):
        raise RuntimeError("original class dictionary/preparation mismatch")
    if preparation.get("original_final_holdout_contexts") != 1331 or preparation.get("generated_negative_examples") != 0:
        raise RuntimeError("original final exclusion/no-generated-negative contract changed")
    candidates = rows(data_dir / "CANDIDATES_PRIVATE.jsonl")
    supervision = rows(data_dir / "CANDIDATE_SUPERVISION_PRIVATE.jsonl")
    train = rows(data_dir / "TRAIN_COMPATIBLE_PRIVATE.jsonl")
    refs = rows(data_dir / "REFERENCE_COVERAGE_PRIVATE.jsonl")
    contexts = rows(data_dir / "CONTEXT_STATES_PRIVATE.jsonl")
    by_id, sup_by_id, context_split = {}, {}, {}
    for r in contexts:
        c, s = r["context_sha256"], r["split"]
        if c in context_split or s not in SPLITS:
            raise RuntimeError("duplicate context or invalid original split")
        if (r.get("reference_group") not in ("GA", "GB", "other", "unknown")
                or type(r.get("inventory_eligible")) is not bool
                or r["inventory_eligible"] != (r.get("year_family_status") in ("known", "not_applicable")
                    and r.get("object_family_status") in ("known", "not_applicable"))
                or (r.get("reference_group_conflict") and r["reference_group"] != "unknown")
                or r.get("metadata_granularity") != "one_normalized_complete_context_unweighted"):
            raise RuntimeError("accepted reference-group/context-mask metadata inconsistent")
        context_split[c] = s
    for r in candidates:
        cid = r["candidate_id"]
        if cid in by_id or context_split.get(r["context_sha256"]) != r["split"]:
            raise RuntimeError("candidate uniqueness/context split violation")
        if r.get("candidate_source") != "unchanged_frozen_year_regex_global_with_frozen_clause_evidence":
            raise RuntimeError("unexpected candidate source")
        if (type(r.get("primary_old_experience_candidate")) is not bool
                or r["primary_old_experience_candidate"] != bool(r.get("frozen_experience_evidence"))):
            raise RuntimeError("primary frozen experience-evidence membership changed")
        by_id[cid] = r
    for r in supervision:
        cid = r["candidate_id"]
        if cid in sup_by_id or cid not in by_id:
            raise RuntimeError("supervision candidate coverage violation")
        c = by_id[cid]
        if (r["context_sha256"], r["split"]) != (c["context_sha256"], c["split"]):
            raise RuntimeError("supervision split/context mismatch")
        if r["supervision_state"] == "compatible_unique_reference":
            if r.get("label") not in CLASSES or r.get("label_id") != CLASSES.index(r["label"]) or len(r["reference_ids"]) != 1:
                raise RuntimeError("compatible original label mismatch")
        elif "label" in r or "label_id" in r:
            raise RuntimeError("non-compatible candidates must remain unlabeled")
        sup_by_id[cid] = r
    if set(by_id) != set(sup_by_id):
        raise RuntimeError("every frozen candidate needs an explicit supervision state")
    seen_train = set()
    for r in train:
        cid = r["candidate_id"]
        if cid in seen_train or cid not in by_id:
            raise RuntimeError("duplicate/unknown fit candidate")
        c, s = by_id[cid], sup_by_id[cid]
        if r["split"] != "train" or s["supervision_state"] != "compatible_unique_reference":
            raise RuntimeError("fit must contain compatible train only")
        if any(r.get(k) != v for k, v in c.items()) or any(r.get(k) != v for k, v in s.items()):
            raise RuntimeError("fit candidate/label is not exact frozen input")
        seen_train.add(cid)
    expected = {cid for cid, s in sup_by_id.items() if s["split"] == "train" and s["supervision_state"] == "compatible_unique_reference"}
    if seen_train != expected or not train:
        raise RuntimeError("fit file must contain every compatible train item exactly once")
    evaluation_rows = rows(data_dir / "EVAL_COMPATIBLE_PRIVATE.jsonl")
    seen_eval = set()
    for r in evaluation_rows:
        cid = r["candidate_id"]
        if cid in seen_eval or cid not in by_id:
            raise RuntimeError("duplicate/unknown held-out candidate")
        c, sup = by_id[cid], sup_by_id[cid]
        if r["split"] not in SPLITS[1:] or sup["supervision_state"] != "compatible_unique_reference":
            raise RuntimeError("held-out file must contain compatible final/reserved only")
        if any(r.get(k) != v for k, v in c.items()) or any(r.get(k) != v for k, v in sup.items()):
            raise RuntimeError("held-out candidate/label is not exact frozen input")
        seen_eval.add(cid)
    expected_eval = {cid for cid, sup in sup_by_id.items() if sup["split"] in SPLITS[1:] and sup["supervision_state"] == "compatible_unique_reference"}
    if seen_eval != expected_eval or len(evaluation_rows) != preparation["eval_compatible_candidates"]:
        raise RuntimeError("held-out input conservation failed")
    ref_by_id = {}
    for r in refs:
        rid = r["reference_id"]
        if rid in ref_by_id or context_split.get(r["context_sha256"]) != r["split"] or r["labels"]["object"] not in CLASSES:
            raise RuntimeError("reference uniqueness/split/label violation")
        if any(cid not in by_id or by_id[cid]["context_sha256"] != r["context_sha256"] for cid in r["candidate_ids"]):
            raise RuntimeError("reference candidate association violation")
        ref_by_id[rid] = r
    for s in supervision:
        if any(rid not in ref_by_id for rid in s["reference_ids"]):
            raise RuntimeError("unknown original reference association")
        if s["supervision_state"] == "compatible_unique_reference":
            r = ref_by_id[s["reference_ids"][0]]
            masks = r.get("accepted_family_masks", {})
            if (r["localization_state"] != "matched_unique" or r["candidate_ids"] != [s["candidate_id"]]
                    or r["labels"]["object"] != s["label"] or s.get("bound_original_item") != r
                    or masks.get("experience_literal_years") is not True
                    or masks.get("experience_object_same_original_item") is not True):
                raise RuntimeError("compatible reference is not unique/exact")
    if len(candidates) != preparation["production_candidates"] or len(train) != preparation["train_compatible_candidates"]:
        raise RuntimeError("preparation inventory counts changed")
    membership = membership_manifest(candidates, supervision, refs, contexts)
    if membership["contexts_by_split"] != preparation.get("context_membership_by_split"):
        raise RuntimeError("frozen complete-context membership digest changed")
    if membership["compatible_contexts_by_split"] != preparation.get("compatible_context_membership_by_split"):
        raise RuntimeError("frozen compatible context membership digest changed")
    return candidates, supervision, train, refs, contexts, digests, preparation


def encode_candidate(tokenizer, row, marker_ids):
    text = row["model_input"]
    if any(text.count(marker) != 1 for marker in MARKERS):
        raise RuntimeError("candidate marker strings must occur exactly once")
    left_text, remainder = text.split(MARKERS[0])
    term, right_text = remainder.split(MARKERS[1])
    if term != row["term"]:
        raise RuntimeError("marker span differs from frozen literal year")
    ids = tokenizer.encode(text, add_special_tokens=False, truncation=False)
    if any(ids.count(i) != 1 for i in marker_ids):
        raise RuntimeError("tokenizer did not preserve unique year markers")
    start, end = ids.index(marker_ids[0]), ids.index(marker_ids[1])
    if end <= start + 1:
        raise RuntimeError("empty/reversed tokenized year span")
    budget = FIXED["max_length"] - tokenizer.num_special_tokens_to_add(pair=False)
    span = end - start + 1
    complete_year_span = ids[start:end+1]
    if span > budget:
        raise RuntimeError("complete year exceeds fixed token budget; no silent truncation")
    cropped = len(ids) > budget
    if cropped:
        spare = budget - span
        left = min(start, spare // 2)
        right = min(len(ids) - end - 1, spare - left)
        left = min(start, spare - right)
        ids = ids[start-left:end+1+right]
    encoded = tokenizer.prepare_for_model(ids, add_special_tokens=True, truncation=False,
                                          return_attention_mask=True, return_token_type_ids=False)
    if len(encoded["input_ids"]) > FIXED["max_length"] or any(encoded["input_ids"].count(i) != 1 for i in marker_ids):
        raise RuntimeError("final fixed input lost marker or exceeded token budget")
    final_ids = encoded["input_ids"]
    if final_ids[final_ids.index(marker_ids[0]):final_ids.index(marker_ids[1])+1] != complete_year_span:
        raise RuntimeError("final input changed/truncated marked year token span")
    # The complete contiguous marked entity token span is retained verbatim.
    return encoded, cropped


def membership_sha(values):
    return hashlib.sha256(("\n".join(sorted(set(values))) + "\n").encode()).hexdigest()


def membership_manifest(candidates, supervision, refs, contexts):
    compatible = [r for r in supervision if r["supervision_state"] == "compatible_unique_reference"]
    return dict(contexts_by_split={s: dict(count=sum(r["split"] == s for r in contexts),
        sorted_context_membership_sha256=membership_sha(r["context_sha256"] for r in contexts if r["split"] == s))
        for s in SPLITS}, compatible_contexts_by_split={s: dict(
        count=len({r["context_sha256"] for r in compatible if r["split"] == s}),
        sorted_context_membership_sha256=membership_sha(r["context_sha256"] for r in compatible if r["split"] == s))
        for s in SPLITS}, all_candidate_ids_sha256=membership_sha(r["candidate_id"] for r in candidates),
        all_reference_ids_sha256=membership_sha(r["reference_id"] for r in refs),
        reference_quote_membership_sha256=membership_sha(json.dumps(dict(reference_id=r["reference_id"],
            context_sha256=r["context_sha256"], evidence=r["evidence"]), sort_keys=True, ensure_ascii=False) for r in refs))


def metrics(gold, pred):
    if len(gold) != len(pred):
        raise RuntimeError("metric inventory conservation failed")
    n = len(CLASSES)
    confusion = [[0] * n for _ in CLASSES]
    for y, p in zip(gold, pred):
        confusion[y][p] += 1
    per_class = {}
    for i, label in enumerate(CLASSES):
        support, predicted = sum(confusion[i]), sum(row[i] for row in confusion)
        tp = confusion[i][i]
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = dict(support=support, reference_items=support, predicted_items=predicted,
            precision=precision, recall=recall, f1=f1,
            reference_share=support / len(gold) if gold else None,
            predicted_share=predicted / len(pred) if pred else None,
            precision_denominator_zero=(predicted == 0), recall_denominator_zero=(support == 0))
    correct = sum(confusion[i][i] for i in range(n))
    accuracy = correct / len(gold) if gold else None
    return dict(items=len(gold), support=len(gold), confusion_matrix_rows_true_columns_predicted=confusion,
        class_order=list(CLASSES), per_class=per_class, accuracy=accuracy,
        macro_precision_fixed_all_classes=sum(x["precision"] for x in per_class.values()) / n if gold else None,
        macro_recall_fixed_all_classes=sum(x["recall"] for x in per_class.values()) / n if gold else None,
        macro_f1_fixed_all_classes=sum(x["f1"] for x in per_class.values()) / n if gold else None,
        micro_precision=accuracy, micro_recall=accuracy, micro_f1=accuracy,
        undefined_ratio_policy="zero with explicit per-class zero-denominator flags; empty inventory aggregates null")


def group_metrics(compatible, candidate_by_id, predictions):
    result = {}
    for flag in ("tech_genai", "tech_software"):
        result[flag] = {}
        for value, name in ((True, "rule_observed"), (False, "not_rule_observed_not_verified_absent")):
            selected = [r for r in compatible if bool(candidate_by_id[r["candidate_id"]].get(
                "frozen_technology_flags", {}).get(flag)) == value]
            result[flag][name] = metrics([r["label_id"] for r in selected],
                [predictions[r["candidate_id"]]["predicted_label_id"] for r in selected])
            result[flag][name]["unique_contexts"] = len({r["context_sha256"] for r in selected})
    return dict(group_definition="unchanged frozen rule-observed context mention flags; not adoption or causal exposure",
        groups=result, adoption_or_other_exposure_metadata="unavailable in recovered source; no inferred exposure")


def conservative_inventory(candidates, supervision, refs, contexts, predictions, inventory):
    """Verified-link bounds; unconfirmed predictions are not labeled false."""
    if inventory not in ("primary_old_experience_candidate", "global_all_numeric_candidates"):
        raise RuntimeError("unapproved inventory diagnostic scope")
    sup_by_id = {r["candidate_id"]: r for r in supervision}
    missing = sum("inventory_eligible" not in r or "reference_group" not in r for r in contexts)
    if missing:
        return dict(status="unavailable_missing_accepted_context_metadata", contexts_missing_metadata=missing)

    def summarize(selected):
        context_ids = {r["context_sha256"] for r in selected}
        cs = [r for r in candidates if r["context_sha256"] in context_ids and
            (inventory == "global_all_numeric_candidates" or r["primary_old_experience_candidate"])]
        rs = [r for r in refs if r["context_sha256"] in context_ids and r["labels"].get("years_relation") != "not_stated"]
        rid_set = {r["reference_id"] for r in rs}
        confirmed, confirmed_refs = [], set()
        for c in cs:
            sup = sup_by_id[c["candidate_id"]]
            if (sup["supervision_state"] == "compatible_unique_reference"
                    and len(sup["reference_ids"]) == 1 and sup["reference_ids"][0] in rid_set
                    and predictions[c["candidate_id"]]["predicted_label"] == sup["label"]):
                confirmed.append(c)
                confirmed_refs.add(sup["reference_ids"][0])
        if len(confirmed) != len(confirmed_refs):
            raise RuntimeError("conservative confirmed links must be one-to-one")
        def score(tp, predicted, reference):
            precision = tp / predicted if predicted else None
            recall = tp / reference if reference else None
            return dict(confirmed_true_positive_links=tp, all_frozen_predictions=predicted,
                all_original_explicit_numeric_references=reference,
                unconfirmed_predictions=predicted-tp, unconfirmed_numeric_references=reference-tp,
                precision_denominator_zero=(predicted == 0), recall_denominator_zero=(reference == 0),
                pessimistic_verified_link_precision_bound=precision, verified_reference_recall_bound=recall,
                verified_link_f1_bound=(2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else 0.0)
                    if predicted or reference else None)
        report = score(len(confirmed), len(cs), len(rs))
        report["per_class"] = {label: score(
            sum(predictions[c["candidate_id"]]["predicted_label"] == label for c in confirmed),
            sum(predictions[c["candidate_id"]]["predicted_label"] == label for c in cs),
            sum(r["labels"]["object"] == label for r in rs)) for label in CLASSES}
        counts = collections.defaultdict(lambda: [0, 0, 0])
        for c in cs:
            counts[c["context_sha256"]][0] += 1
        for r in rs:
            counts[r["context_sha256"]][1] += 1
        for c in confirmed:
            counts[c["context_sha256"]][2] += 1
        nonempty = [counts[c] for c in context_ids if counts[c][0] or counts[c][1]]
        report["context_joint_inventory_match"] = dict(eligible_contexts=len(context_ids),
            contexts_with_prediction_or_numeric_reference=len(nonempty),
            strict_all_predictions_and_numeric_references_confirmed_contexts=sum(a == b == t and a > 0 for a, b, t in nonempty),
            both_inventories_empty_contexts=len(context_ids)-len(nonempty),
            description="literal-year/object joint inventory equality relative to retained original numeric references and verified one-to-one links; not complete-chain or end-to-end accuracy")
        report["eligible_context_membership_sha256"] = membership_sha(context_ids)
        report["reference_group_conflict_contexts"] = sum(bool(r.get("reference_group_conflict")) for r in selected)
        return report

    output = {}
    for split in SPLITS:
        selected = [r for r in contexts if r["split"] == split and r["inventory_eligible"] is True]
        output[split] = dict(overall=summarize(selected), by_pro_reference_technology_group={
            group: summarize([r for r in selected if r["reference_group"] == group])
            for group in ("GA", "GB", "other", "unknown")},
            excluded_contexts_without_accepted_year_and_object_masks=sum(r["split"] == split and r["inventory_eligible"] is not True for r in contexts))
    return dict(status="verified_link_conservative_inventory_diagnostic", inventory=inventory, by_split=output,
        recall_denominator="all original explicit numeric references in accepted contexts for BOTH inventories; old candidate misses remain penalized",
        class_order=list(CLASSES), gold_no_relation_available=False,
        interpretation="Unconfirmed predictions may include correct but unverifiable relations; they are not labeled false positives. Bounds refer to retained Pro references plus verified links and do not identify corpus error rates.",
        group_policy="one complete context, one Pro-reference group; conflicting ad-level groups preserved as unknown, without ad weighting",
        training_scope="training split is a resubstitution diagnostic; final and legacy reserved splits remain separate")


def run(a, root, progress):
    import numpy as np
    import torch
    import transformers
    from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or not torch.version.hip:
        raise RuntimeError("one allocated working DCU required")
    torch.set_num_threads(8)
    timings = {}
    begin = time.perf_counter()
    progress["stage"] = "read_and_verify"
    candidates, supervision, train, refs, contexts, data_digests, prep = load_inputs(Path(a.inputs))
    model_pin = model_identity(Path(a.model_dir), Path(a.model_manifest))
    code_digests = {p.name: sha(p) for p in Path(__file__).parent.iterdir() if p.is_file() and p.suffix in (".py", ".sbatch")}
    timings["read_and_verify_seconds"] = time.perf_counter() - begin
    write(root / "INPUT_MANIFEST_PUBLIC.json", dict(code_sha256=code_digests, data_sha256=data_digests,
          checkpoint=model_pin, original_preparation_inputs=prep["inputs"], fixed_config=FIXED,
          membership=membership_manifest(candidates, supervision, refs, contexts), label_classes=list(CLASSES)))
    write(root / "INPUT_MANIFEST_PRIVATE.json", dict(input_directory=str(Path(a.inputs).resolve()),
          input_files=data_digests, model_directory=str(Path(a.model_dir).resolve()),
          model_manifest=str(Path(a.model_manifest).resolve()), code_files=code_digests))
    random.seed(FIXED["seed"])
    np.random.seed(FIXED["seed"])
    torch.manual_seed(FIXED["seed"])
    torch.cuda.manual_seed_all(FIXED["seed"])
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    progress["stage"] = "load_local_checkpoint_and_tokenize"
    begin = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(a.model_dir, local_files_only=True, trust_remote_code=False, use_fast=True)
    tokenizer.add_special_tokens({"additional_special_tokens": list(MARKERS)})
    marker_ids = [tokenizer.convert_tokens_to_ids(m) for m in MARKERS]
    if len(set(marker_ids)) != 2 or tokenizer.unk_token_id in marker_ids:
        raise RuntimeError("special year markers must have distinct token IDs")
    timings["tokenizer_load_seconds"] = time.perf_counter() - begin
    begin = time.perf_counter()
    encoded, crop_counts = {}, collections.Counter()
    for row in candidates:
        value, cropped = encode_candidate(tokenizer, row, marker_ids)
        encoded[row["candidate_id"]] = value
        crop_counts[row["split"]] += int(cropped)
    timings["tokenize_seconds"] = time.perf_counter() - begin
    begin = time.perf_counter()
    config = AutoConfig.from_pretrained(a.model_dir, local_files_only=True, trust_remote_code=False)
    if config.model_type != "xlm-roberta" or config.hidden_size != 768 or config.num_hidden_layers != 12:
        raise RuntimeError("pinned checkpoint must be XLM-RoBERTa-base")
    config.num_labels = len(CLASSES)
    config.label2id = {role: i for i, role in enumerate(CLASSES)}
    config.id2label = {i: role for i, role in enumerate(CLASSES)}
    model = AutoModelForSequenceClassification.from_pretrained(a.model_dir, config=config,
                local_files_only=True, trust_remote_code=False)
    model.resize_token_embeddings(len(tokenizer))
    model = model.float().to("cuda:0")
    if any(p.dtype != torch.float32 for p in model.parameters()):
        raise RuntimeError("fixed fp32 model required")
    timings["model_load_seconds"] = time.perf_counter() - begin
    progress["_model"], progress["_tokenizer"] = model, tokenizer

    def batch_input(group):
        return {k: v.to("cuda:0") for k, v in tokenizer.pad(
            [encoded[r["candidate_id"]] for r in group], padding=True, return_tensors="pt").items()}

    progress["stage"] = "train_fixed_three_epochs"
    begin = time.perf_counter()
    optimizer = torch.optim.AdamW(model.parameters(), lr=FIXED["learning_rate"], weight_decay=FIXED["weight_decay"])
    epoch_logs, optimizer_steps = [], 0
    progress["optimizer_steps"], progress["completed_epochs"] = 0, 0
    for epoch in range(FIXED["epochs"]):
        model.train()
        order = list(range(len(train)))
        random.Random(FIXED["seed"] + epoch).shuffle(order)
        epoch_loss_sum, epoch_items = 0.0, 0
        # Accumulate exactly the mean over each effective 32-item group. The
        # final short group is normalized by its actual size, not by eight.
        for offset in range(0, len(order), FIXED["batch_size"] * FIXED["gradient_accumulation_steps"]):
            group_ids = order[offset:offset + FIXED["batch_size"] * FIXED["gradient_accumulation_steps"]]
            optimizer.zero_grad(set_to_none=True)
            for micro in range(0, len(group_ids), FIXED["batch_size"]):
                group = [train[i] for i in group_ids[micro:micro + FIXED["batch_size"]]]
                batch = batch_input(group)
                labels = torch.tensor([r["label_id"] for r in group], dtype=torch.long, device="cuda:0")
                result = model(**batch, labels=labels)
                if not torch.isfinite(result.loss):
                    raise RuntimeError("nonfinite training loss")
                (result.loss * (len(group) / len(group_ids))).backward()
                epoch_loss_sum += result.loss.detach().item() * len(group)
                epoch_items += len(group)
            optimizer.step()
            optimizer_steps += 1
            progress["optimizer_steps"] = optimizer_steps
        if epoch_items != len(train):
            raise RuntimeError("epoch did not consume every compatible train item")
        torch.cuda.synchronize()
        log = dict(epoch=epoch + 1, train_items=epoch_items,
                   mean_train_loss=epoch_loss_sum / epoch_items, cumulative_optimizer_steps=optimizer_steps)
        epoch_logs.append(log)
        progress["completed_epochs"] = epoch + 1
        write(root / ("EPOCH_%d_TRAIN_ONLY_PUBLIC.json" % (epoch + 1)), log)
    timings["train_seconds"] = time.perf_counter() - begin

    progress["stage"] = "save_only_final_epoch_checkpoint"
    begin = time.perf_counter()
    final_model = root / "FINAL_MODEL_PRIVATE"
    model.save_pretrained(final_model, safe_serialization=False)
    tokenizer.save_pretrained(final_model)
    timings["save_final_checkpoint_seconds"] = time.perf_counter() - begin

    progress["stage"] = "predict_every_frozen_candidate"
    begin = time.perf_counter()
    model.eval()
    predictions = {}
    with torch.no_grad():
        for offset in range(0, len(candidates), FIXED["batch_size"]):
            group = candidates[offset:offset + FIXED["batch_size"]]
            logits = model(**batch_input(group)).logits
            if not torch.isfinite(logits).all():
                raise RuntimeError("nonfinite candidate logits")
            probabilities = torch.softmax(logits, dim=-1).cpu().tolist()
            for row, probability in zip(group, probabilities):
                p = max(range(len(CLASSES)), key=lambda i: probability[i])
                predictions[row["candidate_id"]] = dict(predicted_label_id=p, predicted_label=CLASSES[p], probabilities=probability)
    torch.cuda.synchronize()
    timings["predict_seconds"] = time.perf_counter() - begin
    if len(predictions) != len(candidates):
        raise RuntimeError("frozen candidate prediction conservation failed")

    progress["stage"] = "write_private_predictions_and_public_conditional_metrics"
    begin = time.perf_counter()
    sup_by_id = {r["candidate_id"]: r for r in supervision}
    prediction_path = root / "PREDICTIONS_PRIVATE.jsonl"
    with open(prediction_path, "x", encoding="utf-8") as stream:
        os.chmod(prediction_path, 0o600)
        for row in candidates:
            cid = row["candidate_id"]
            result = dict(candidate_id=cid, context_sha256=row["context_sha256"], split=row["split"],
                          supervision_state=sup_by_id[cid]["supervision_state"], **predictions[cid])
            stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    evaluation, prediction_shares, evaluation_by_existing_group, evaluation_by_pro_group = {}, {}, {}, {}
    context_by_id = {r["context_sha256"]: r for r in contexts}
    candidate_by_id = {r["candidate_id"]: r for r in candidates}
    for split in SPLITS:
        compatible = [r for r in supervision if r["split"] == split and r["supervision_state"] == "compatible_unique_reference"]
        gold = [r["label_id"] for r in compatible]
        pred = [predictions[r["candidate_id"]]["predicted_label_id"] for r in compatible]
        evaluation[split] = metrics(gold, pred)
        evaluation_by_existing_group[split] = group_metrics(compatible, candidate_by_id, predictions)
        evaluation_by_pro_group[split] = {}
        for reference_group in ("GA", "GB", "other", "unknown"):
            members = [r for r in compatible if context_by_id[r["context_sha256"]]["reference_group"] == reference_group]
            result = metrics([r["label_id"] for r in members],
                [predictions[r["candidate_id"]]["predicted_label_id"] for r in members])
            result["unique_contexts"] = len({r["context_sha256"] for r in members})
            evaluation_by_pro_group[split][reference_group] = result
        evaluation[split]["unique_contexts"] = len({r["context_sha256"] for r in compatible})
        evaluation[split]["scope"] = ("training resubstitution diagnostic only" if split == "train" else
            "conditional on frozen candidate and compatible unique original reference; previously exposed final" if split == SPLITS[1] else
            "separate reserved original holdout; excluded from training and all selection")
        split_candidates = [r for r in candidates if r["split"] == split]
        shares = collections.Counter(predictions[r["candidate_id"]]["predicted_label"] for r in split_candidates)
        prediction_shares[split] = dict(items=len(split_candidates), by_class={role: dict(
            items=shares[role], share=shares[role]/len(split_candidates) if split_candidates else None) for role in CLASSES})
    reference_scope = {}
    for split in SPLITS:
        group = [r for r in refs if r["split"] == split]
        numeric = [r for r in group if r["labels"].get("years_relation") != "not_stated"]
        reference_scope[split] = dict(items=len(group), unique_contexts=len({r["context_sha256"] for r in group}),
            localization_states=dict(collections.Counter(r["localization_state"] for r in group)),
            by_class={label: sum(r["labels"]["object"] == label for r in group) for label in CLASSES},
            not_stated_original_items=len(group) - len(numeric), numeric_reference_items=len(numeric),
            numeric_candidate_covered_items=sum(bool(r["candidate_ids"]) for r in numeric),
            numeric_candidate_coverage=sum(bool(r["candidate_ids"]) for r in numeric)/len(numeric) if numeric else None,
            numeric_localization_states=dict(collections.Counter(r["localization_state"] for r in numeric)),
            scope="all original accepted year-family references retained; numeric coverage is frozen-candidate binding coverage, not end-to-end accuracy")
    output_hashes = {str(p.relative_to(root)): sha(p) for p in root.rglob("*") if p.is_file()}
    timings["write_seconds"] = time.perf_counter() - begin
    return dict(status="completed_fixed_fit_and_all_candidate_prediction", scheduler_job_id=os.environ["SLURM_JOB_ID"],
        finished_unix=time.time(),
        requested_resources=dict(partition="wzhdtest", cpus=8, memory="16G", dcu=1, time_limit="02:00:00"),
        actual_scheduler_environment={k: os.environ.get(k) for k in (
            "SLURM_JOB_PARTITION", "SLURM_CPUS_PER_TASK", "SLURM_MEM_PER_NODE", "SLURM_JOB_GPUS", "SLURM_JOB_NODELIST")},
        runtime=dict(python=sys.version.split()[0], interpreter=sys.executable, torch=torch.__version__,
                     transformers=transformers.__version__, numpy=np.__version__, hip=torch.version.hip,
                     device=torch.cuda.get_device_name(0)),
        fixed_config=FIXED, code_sha256=code_digests, data_sha256=data_digests, checkpoint=model_pin,
        marker_policy=dict(markers=list(MARKERS), ids=marker_ids, max_length=256,
            policy="deterministic centered token crop within frozen 192-character context window; full marked year retained",
            cropped_candidates_by_split=dict(crop_counts)),
        train_support=counts(train, "label"), compatible_support=counts(
            [r for r in supervision if r["supervision_state"] == "compatible_unique_reference"], "label"),
        candidate_support=counts(candidates), context_inventory=counts(contexts),
        candidate_supervision_states_by_split={s: dict(collections.Counter(r["supervision_state"] for r in supervision if r["split"] == s)) for s in SPLITS},
        reference_scope=reference_scope, evaluation=evaluation,
        evaluation_by_frozen_rule_mention_group=evaluation_by_existing_group,
        evaluation_by_pro_reference_technology_group=evaluation_by_pro_group,
        pro_group_metadata=prep["group_metadata"],
        all_candidate_prediction_shares=prediction_shares, membership=membership_manifest(candidates, supervision, refs, contexts),
        original_final_holdout_membership_sha256=prep["original_final_holdout_membership_sha256"],
        end_to_end_relation_qualification=False, gold_no_relation_available=False,
        primary_quality_diagnostic_inventory="primary_old_experience_candidate",
        fit_training_inventory="all compatible candidates, unchanged by diagnostic inventory",
        conservative_inventory_diagnostic={inventory: conservative_inventory(candidates, supervision, refs, contexts, predictions, inventory)
            for inventory in ("primary_old_experience_candidate", "global_all_numeric_candidates")},
        epoch_train_logs=epoch_logs, optimizer_steps=optimizer_steps, timings=timings,
        output_sha256=output_hashes, new_labels=0, generated_negatives=0, new_software_installed=0,
        downloaded_weights_during_fit=0, independent_private_prediction_sidecar=prediction_path.name,
        complete_same_item_chain_accuracy="not evaluated: only year-mention object prediction is modeled",
        final_based_model_selection=False, automatic_reruns=False,
        limitations=["This is contextual literal-year-mention to accepted experience-object classification; it is not qualified end-to-end relation extraction.",
            "Evaluation is conditional on frozen candidates with compatible unique references; unmatched/ambiguous references stay in scope inventories.",
            "Frozen duration and old rule object evidence are audit/group metadata only; the model consumes only marked model_input text.",
            "All frozen candidates are predicted, including unlabeled/conflicting/ambiguous candidates; these are not negatives and have no accuracy labels.",
            "Previously exposed final and reserved original holdout are reported separately; neither enters fit/model selection.",
            "No whole-corpus quality claim or acceptance threshold is established by this receipt.",
            "No gold no_relation exists; spurious relation precision and end-to-end relation quality are unidentifiable from these labels.",
            "Seed and deterministic cuDNN settings are fixed; exact cross-hardware bitwise reproducibility is not asserted."])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", required=True)
    p.add_argument("--model-dir", required=True)
    p.add_argument("--model-manifest", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("scheduled SCNet execution required")
    os.umask(0o077)
    # Atomic create-only output guard also preserves partially started/failed fits.
    root = Path(a.output)
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    progress = {"stage": "startup"}
    write(root / "STARTED_PUBLIC.json", dict(scheduler_job_id=os.environ["SLURM_JOB_ID"],
        started_unix=time.time(), fixed_config=FIXED, code_sha256=sha(__file__), automatic_reruns=False))
    def interrupted(signum, frame):
        raise InterruptedError("scheduler termination signal")
    signal.signal(signal.SIGTERM, interrupted)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    try:
        report = run(a, root, progress)
        write(root / "FIT_EVALUATION_PUBLIC.json", report)
    except BaseException as exc:
        # A failure never authorizes restart or another fit. If training itself
        # failed, preserve current weights best effort as an explicitly failed
        # private artifact, never a selected/evaluated final checkpoint.
        original_trace = traceback.format_exc()
        partial_checkpoint = "not_applicable"
        if progress["stage"] == "train_fixed_three_epochs" and "_model" in progress:
            try:
                progress["_model"].save_pretrained(root / "FAILED_PARTIAL_MODEL_PRIVATE", safe_serialization=False)
                progress["_tokenizer"].save_pretrained(root / "FAILED_PARTIAL_MODEL_PRIVATE")
                partial_checkpoint = "preserved_failed_state_not_for_selection_or_resume"
            except BaseException:
                partial_checkpoint = "preservation_failed_original_failure_retained"
                with open(root / "CHECKPOINT_FAILURE_TRACE_PRIVATE.txt", "x", encoding="utf-8") as stream:
                    stream.write(traceback.format_exc())
        # No exception messages/tracebacks enter public receipts: runtime errors
        # can contain private text. Original details are retained privately.
        write(root / "FAILED_PUBLIC.json", dict(status="failed_no_automatic_rerun",
            scheduler_job_id=os.environ["SLURM_JOB_ID"], stage=progress["stage"], error_type=type(exc).__name__,
            completed_epochs=progress.get("completed_epochs", 0), optimizer_steps=progress.get("optimizer_steps", 0),
            failed_checkpoint=partial_checkpoint, final_checkpoint_present=(root / "FINAL_MODEL_PRIVATE").exists()))
        with open(root / "FAILURE_TRACE_PRIVATE.txt", "x", encoding="utf-8") as stream:
            stream.write(original_trace)
        raise


if __name__ == "__main__":
    main()

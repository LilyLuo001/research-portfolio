"""Controller-neutral bounded physical-row preparation. Importing performs no I/O."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import signal
import time


LIMIT = 10_000
NORMALIZER_SHA256 = "336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd"
PROTOCOL_VERSION = "economic-pilot-20261119-v1"
KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
DENY_STATES = {"quarantined", "protected", "not_reconciled", "reviewed_unknown", "saved_unverified"}


class PreparationError(ValueError):
    pass


def need(test, reason):
    if not test:
        raise PreparationError(reason)


def stable(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def sha(value):
    need(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), "invalid_sha256")
    return value


def canonical(row):
    values = tuple(row[k] for k in KEY)
    need(all(v is not None for v in values), "missing_canonical_key")
    need(all(type(v) is int and v >= 0 for v in values[2:]), "invalid_source_row")
    return (str(values[0]), str(values[1]), values[2], values[3])


def cache_key(context, versions):
    sha(context)
    need(versions.get("protocol_version") == PROTOCOL_VERSION, "wrong_protocol_version")
    for key in ("schema_sha256", "extractor_sha256", "normalizer_sha256"):
        sha(versions.get(key))
    need(versions["normalizer_sha256"] == NORMALIZER_SHA256, "normalizer_changed")
    return digest(stable(["normalized-context-cache-v1", context, versions]).encode())


@dataclass(frozen=True)
class Origin:
    """Metadata-only, SHA-bound original window and immutable confirmation successor."""
    window_sha256: str
    confirmation_frame_sha256: str
    confirmation_preparation_sha256: str
    base_artifact_sha256: str
    description_artifact_sha256: str
    shard_ordinal: int
    next_row_offset: int
    shard_rows: int

    def identity(self):
        return digest(stable(self.__dict__).encode())


def origin_from_metadata(window, preparation, *, window_sha256, frame_sha256, preparation_sha256):
    """Caller verifies actual bytes before supplying these metadata objects/pins."""
    for h in (window_sha256, frame_sha256, preparation_sha256):
        sha(h)
    begin, end = window["start_cursor"], window["end_cursor_exclusive"]
    need(not window["cursor_gate_blockers"], "original_window_blocked")
    need(begin["shard_ordinal"] == end["shard_ordinal"]
         and end["row_offset"] - begin["row_offset"] == 150, "original_window_shape_changed")
    need(preparation["start_cursor"] == begin and preparation["end_cursor_exclusive"] == end
         and preparation["canonical_window_rows"] == 150
         and preparation["fresh_complete_unique_contexts"] == 135
         and preparation["normalizer_sha256"] == NORMALIZER_SHA256
         and preparation["no_rejected_row_replacement"] is True, "confirmation_receipt_disagrees")
    base, binding = window["base_register_entry"], window["description_source_binding"]
    need(base["ad_rows"] == window["catalog_entry"]["ad_rows"], "catalog_count_disagrees")
    return Origin(window_sha256, frame_sha256, preparation_sha256, sha(base["ad_sha256"]),
                  sha(binding["source_sha256_from_cached_receipts"]), end["shard_ordinal"],
                  end["row_offset"], base["ad_rows"])


@dataclass
class GuardSnapshot:
    """All members are metadata, never saved judgments or raw source strings.

    key_states maps four-key tuples to {state, context_sha256(optional)}.
    context_states preserves original ledger states. Canonical-only exclusions
    may lack a context link; their physical row is still retained as unresolved.
    """
    excluded_contexts: set
    context_states: dict
    key_states: dict
    protected_keys: set
    protected_contexts: set
    forbidden_source_fragments: tuple
    source_pins: dict
    coverage: dict

    def validate(self):
        required = ("all_prior_statuses", "all_prior_source_manifests", "original_10000_reference",
                    "stage5_135_frame", "stage5_all_final_exclusions", "current_runtime_guards")
        need(all(self.coverage.get(k) is True for k in required), "incomplete_exclusion_coverage")
        need(self.coverage.get("original_status_context_count", 0) >= 55882,
             "original_status_union_incomplete")
        need(len(self.context_states) >= 55882 and set(self.context_states) <= self.excluded_contexts,
             "context_state_union_incomplete")
        need(self.protected_contexts <= self.excluded_contexts, "protected_union_incomplete")
        for h in self.excluded_contexts:
            sha(h)
        need(bool(self.source_pins), "exclusion_source_pins_missing")
        for value in self.source_pins.values():
            sha(value)

    def fingerprint(self):
        return digest(stable({
            "excluded_contexts": sorted(self.excluded_contexts),
            "context_states": self.context_states,
            "key_states": sorted((list(k), v) for k, v in self.key_states.items()),
            "protected_keys": sorted(map(list, self.protected_keys)),
            "protected_contexts": sorted(self.protected_contexts),
            "forbidden_source_fragments": list(self.forbidden_source_fragments),
            "source_pins": self.source_pins, "coverage": self.coverage,
        }).encode())


def compatible_cache(context, versions, cache):
    entry = cache.get(cache_key(context, versions))
    if entry is None:
        return None
    need(entry.get("cache_key") == cache_key(context, versions)
         and entry.get("context_sha256") == context and entry.get("versions") == versions,
         "cache_identity_mismatch")
    if entry.get("status") != "complete_known_compatible" or not entry.get("measure_ids"):
        return None
    sha(entry.get("output_sha256"))
    return {k: entry[k] for k in ("cache_key", "context_sha256", "output_sha256", "measure_ids")}


def prepare_batch(*, source, origin, snapshot, refresh_snapshot, normalize, versions,
                  batch_id, row_limit=100, previous=None, prior_context_links=None, cache=None):
    """Read only the exact selected shard range; preserve one mapping per physical row.

    ``source.metadata_rows(start,count)`` returns exact four keys + catalog offset.
    ``source.descriptions(allowed_rows)`` is called only after identity protection;
    it returns SOURCE_ROW -> {JOB_HASH, DESCRIPTION} for those selected rows only.
    Source implementation must verify ledger SHA/size, ETag and projected ranges.
    """
    need(type(row_limit) is int and 1 <= row_limit <= LIMIT, "row_limit_out_of_bounds")
    need(re.fullmatch(r"batch[0-9]{4,}", batch_id), "invalid_batch_id")
    cache_key("0" * 64, versions)
    snapshot.validate()
    before = snapshot.fingerprint()
    prior_context_links, cache = prior_context_links or {}, cache or {}
    physical_used = unique_used = 0
    start = origin.next_row_offset
    previous_sha = None
    if previous:
        need(previous["origin_sha256"] == origin.identity() and previous["versions"] == versions,
             "continuation_origin_or_versions_changed")
        need(previous["end_cursor_exclusive"]["shard_ordinal"] == origin.shard_ordinal,
             "continuation_shard_changed_without_binding")
        previous_sha = sha(previous["manifest_sha256"])
        start = previous["end_cursor_exclusive"]["row_offset"]
        physical_used = previous["cumulative_physical_rows"]
        unique_used = previous["cumulative_new_unique_contexts"]
        need(len(prior_context_links) == unique_used, "prior_input_context_links_incomplete")
    else:
        need(not prior_context_links, "prior_contexts_without_manifest")
    need(type(start) is int and origin.next_row_offset <= start < origin.shard_rows,
         "selected_shard_exhausted_or_cursor_regressed")
    need(type(physical_used) is int and type(unique_used) is int
         and 0 <= unique_used <= physical_used < LIMIT, "cumulative_limit_or_counter_invalid")
    count = min(row_limit, LIMIT - physical_used, origin.shard_rows - start)
    selected = source.metadata_rows(start, count)
    need(len(selected) == count and [x["catalog_row_offset"] for x in selected] == list(range(start, start + count)),
         "physical_window_not_exactly_conserved")
    mappings, ready, inputs, current = [], [], [], {}

    def old_disposition(mapping, state, context=None):
        mapping["prior_state"] = state
        mapping["state"] = state if state in DENY_STATES else "old_context_unresolved"
        mapping["context_sha256"] = context
        if context:
            mapping["cache_key"] = cache_key(context, versions)
            if state not in DENY_STATES:
                hit = compatible_cache(context, versions, cache)
                if hit:
                    mapping.update(state="compatible_cache_reference", cache_reference=hit)

    for item in selected:
        k = canonical(item)
        mapping = {"physical_row_id": digest(stable(["base-physical-row-v1", origin.base_artifact_sha256,
                                                     item["catalog_row_offset"]]).encode()),
                   "physical_identity_kind": "immutable_base_artifact_sha256_and_actual_row_ordinal",
                   "canonical_key": list(k), "catalog_row_offset": item["catalog_row_offset"],
                   "shard_ordinal": origin.shard_ordinal, "base_artifact_sha256": origin.base_artifact_sha256,
                   "description_artifact_sha256": origin.description_artifact_sha256,
                   "context_sha256": None, "cache_key": None, "input_case": None,
                   "state": "unresolved", "prior_state": None}
        mappings.append(mapping)
        forbidden = any(x.lower() in k[1].lower() for x in snapshot.forbidden_source_fragments)
        if k in snapshot.protected_keys or forbidden:
            old_disposition(mapping, "protected")
        elif k in snapshot.key_states:
            saved = snapshot.key_states[k]
            old_disposition(mapping, saved["state"], saved.get("context_sha256"))
        else:
            ready.append((item, mapping))
    bodies = source.descriptions([item for item, _ in ready]) if ready else {}
    need(set(bodies) <= {canonical(item)[2] for item, _ in ready}, "unrequested_source_value_returned")
    for item, mapping in ready:
        k = canonical(item)
        value = bodies.get(k[2])
        if value is None:
            mapping.update(state="source_unavailable", reason="selected_description_missing")
            continue
        need(str(value["JOB_HASH"]) == k[0], "source_JOB_HASH_binding_mismatch")
        body = value.get("DESCRIPTION")
        if not isinstance(body, str) or len(body.encode("utf-8")) > 128 * 1024:
            mapping.update(state="source_unavailable", reason="invalid_or_oversize_complete_description")
            continue
        normalized, flags = normalize(body)
        if not isinstance(normalized, str) or not normalized:
            mapping.update(state="source_unavailable", reason="empty_normalized_description")
            continue
        h = digest(normalized.encode("utf-8"))
        mapping.update(context_sha256=h, cache_key=cache_key(h, versions))
        if h in snapshot.protected_contexts:
            old_disposition(mapping, "protected", h)
        elif h in prior_context_links or h in current:
            link = prior_context_links[h] if h in prior_context_links else current[h]
            mapping.update(state="duplicate_context", input_case=link["input_case"],
                           primary_batch_id=link["batch_id"], duplicate_result_state="pending_or_existing_not_inferred_negative")
        elif h in snapshot.excluded_contexts:
            old_disposition(mapping, snapshot.context_states.get(h, "prepared_or_exposed"), h)
        else:
            hit = compatible_cache(h, versions, cache)
            if hit:
                mapping.update(state="compatible_cache_reference", cache_reference=hit)
            else:
                need(unique_used + len(inputs) < LIMIT, "new_unique_context_limit")
                case = batch_id + "-" + h
                inputs.append({"case": case, "row": {"record_id": "economic-pilot-" + h,
                    "context_sha256": h, "full_document": normalized}, "protected": False,
                    "fresh_never_exposed": True, "partition": "pilot",
                    "source_task": "economic-pilot-20261119", "cache_key": mapping["cache_key"]})
                current[h] = {"input_case": case, "batch_id": batch_id}
                mapping.update(state="new_context_prepared", input_case=case, primary_batch_id=batch_id,
                               normalization_flags=flags)
    after = refresh_snapshot()
    after.validate()
    need(after.fingerprint() == before, "exposure_or_protection_snapshot_changed")
    need(len(mappings) == count and len({x["physical_row_id"] for x in mappings}) == count,
         "physical_row_mapping_not_100_percent")
    need(len(inputs) == len(current) and not set(current) & snapshot.excluded_contexts,
         "new_input_dedup_or_exclusion_error")
    excluded = snapshot.excluded_contexts | set(prior_context_links)
    ranges = source.range_receipts() if hasattr(source, "range_receipts") else []
    source_stats = source.statistics() if hasattr(source, "statistics") else {"synthetic_source": True}
    return {"inputs": inputs, "physical_rows": mappings, "source_ranges": ranges,
            "exclusions": {"context_sha256": sorted(excluded), "tasks": list(snapshot.forbidden_source_fragments)},
            "manifest": {"batch_id": batch_id, "protocol_version": PROTOCOL_VERSION, "versions": versions,
                "origin_sha256": origin.identity(), "origin": origin.__dict__,
                "previous_batch_manifest_sha256": previous_sha, "snapshot_sha256": before,
                "snapshot_source_pins": snapshot.source_pins,
                "start_cursor": {"shard_ordinal": origin.shard_ordinal, "row_offset": start},
                "end_cursor_exclusive": {"shard_ordinal": origin.shard_ordinal, "row_offset": start + count},
                "physical_rows": count, "new_unique_contexts": len(inputs),
                "cumulative_physical_rows": physical_used + count,
                "cumulative_new_unique_contexts": unique_used + len(inputs),
                "physical_row_mapping_coverage": 1.0, "state_counts": dict(Counter(x["state"] for x in mappings)),
                "global_authoritative_physical_total": None, "requested_full_target_approximate": 500_000_000,
                "global_unique_context_total": None, "full_target_dedup_ratio": None,
                "source_read_statistics": source_stats,
                "model_calls": 0, "new_semantic_acceptances": 0, "production_admission": False}}


def commit_batch(result, output):
    """Append-only local files; manifest is written last as the commit marker."""
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    files = {"inputs": "INPUTS_PRIVATE.jsonl", "physical_rows": "PHYSICAL_ROWS_PRIVATE.jsonl",
             "exclusions": "EXCLUSIONS_PRIVATE.json", "source_ranges": "SOURCE_RANGE_READS_PRIVATE.json"}
    pins = {}
    for key, name in files.items():
        value = result[key]
        data = (("".join(stable(x) + "\n" for x in value)) if key in ("inputs", "physical_rows")
                else stable(value) + "\n").encode()
        with (out / name).open("xb") as stream:
            stream.write(data)
        (out / name).chmod(0o600)
        pins[key + "_sha256"] = digest(data)
    manifest = {**result["manifest"], "filenames": files, **pins}
    data = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    with (out / "BATCH_MANIFEST_PUBLIC.json").open("xb") as stream:
        stream.write(data)
    return {"manifest_path": str(out / "BATCH_MANIFEST_PUBLIC.json"), "manifest_sha256": digest(data),
            "physical_rows": manifest["physical_rows"], "new_unique_contexts": manifest["new_unique_contexts"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller", type=Path, required=True)
    parser.add_argument("--controller-sha256", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--batch-id", default="batch0001")
    parser.add_argument("--row-limit", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    signal.alarm(240)
    try:
        code, data = args.controller.read_bytes(), args.config.read_bytes()
        need(digest(code) == sha(args.controller_sha256), "controller_sha_mismatch")
        need(digest(data) == sha(args.config_sha256), "controller_config_sha_mismatch")
        module = importlib.util.module_from_spec(importlib.util.spec_from_loader("pinned_preparation_controller", loader=None))
        module.__file__ = str(args.controller)
        exec(compile(code, str(args.controller), "exec"), module.__dict__)
        kwargs = module.build_preparation_inputs(json.loads(data))
        result = prepare_batch(**kwargs, batch_id=args.batch_id, row_limit=args.row_limit)
        result["manifest"]["preparation_elapsed_before_commit_seconds"] = time.monotonic() - started
        print(json.dumps(commit_batch(result, args.output), sort_keys=True))
    except Exception as exc:
        print(json.dumps({"status": "preparation_stopped_no_cursor_advance",
                          "error_type": type(exc).__name__,
                          "reason": str(exc) if isinstance(exc, PreparationError) or type(exc).__name__ == "GateError"
                          else "unexpected_error_details_not_exported", "model_calls": 0}))
        raise SystemExit(2) from None
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()

"""Explicit existing-VM configuration adapter. No execution or network on import."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

from prepare_physical import GuardSnapshot, NORMALIZER_SHA256, canonical, digest, need, origin_from_metadata
from legacy_projected_source import LegacyProjectedSource


def load_code(path, expected, name):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "pinned_code_path_invalid")
    data = path.read_bytes()
    need(digest(data) == expected, "pinned_code_changed")
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader=None))
    mod.__file__ = str(path)
    exec(compile(data, str(path), "exec"), mod.__dict__)
    return mod


def build_preparation_inputs(config):
    sys.dont_write_bytecode = True
    root = Path(config["migration_root"]).resolve()
    legacy = load_code(config["legacy_code"]["path"], config["legacy_code"]["sha256"], "pinned_legacy_preparation")
    normalizer = load_code(config["normalizer"]["path"], NORMALIZER_SHA256, "pinned_legacy_normalizer")
    sys.path.insert(0, config["parquet_libraries"])
    import pyarrow as pa
    import pyarrow.parquet as pq
    sys.path.insert(0, str(root / "code"))
    from workflow import call
    state = legacy.State(root, Path(config["run_root"]))
    state.pa, state.pq, state.call = pa, pq, call

    def metadata(entry, lines=False):
        return state.read(Path(entry["path"]), entry["sha256"], lines)

    window = metadata(config["original_window"])
    preparation = metadata(config["confirmation_preparation"])
    frame = metadata(config["stage5_frame"], True)
    need(len(frame) == 135 and len({r["context_sha256"] for r in frame}) == 135
         and all("full_document" not in r for r in frame), "stage5_frame_shape_changed")
    origin = origin_from_metadata(window, preparation,
        window_sha256=config["original_window"]["sha256"],
        frame_sha256=config["stage5_frame"]["sha256"],
        preparation_sha256=config["confirmation_preparation"]["sha256"])
    initial = metadata(config["original_exclusions"])
    need(len(config["stage5_final_exclusions"]) == 3, "all_three_stage5_exclusions_required")
    finals = [metadata(entry) for entry in config["stage5_final_exclusions"]]
    # Original 10k reference: only its four canonical keys and normalized hash.
    # Reuse the existing bounded transport/schema, never decode its text column.
    loc = legacy.ledger_locations(root, legacy.REFERENCE_SHA)[0]
    need(loc["size"] <= legacy.MAX_REFERENCE, "reference_metadata_artifact_cap")
    blob = legacy.Blob(state, loc, "prior_10000_reference_metadata")
    reference_bytes = blob.read(0, blob.size)
    need(digest(reference_bytes) == legacy.REFERENCE_SHA, "original_reference_sha_changed")
    table = pq.ParquetFile(pa.BufferReader(reference_bytes))
    need(table.metadata.num_rows == 10000, "original_reference_count_changed")
    reference_rows = table.read(columns=legacy.KEY + ["normalized_context_sha256"], use_threads=False).to_pylist()
    reference = {canonical(r): r["normalized_context_sha256"] for r in reference_rows}
    need(len(reference) == 10000, "reference_keys_not_unique")
    del table, reference_rows, reference_bytes

    def collect():
        # live_union checks the bounded source-manifest inventory and all known
        # runtime guards; it does not reopen saved semantic result payloads.
        excluded, prior_keys, _ = legacy.live_union(state, initial["context_sha256"], True)
        excluded.update(reference.values())
        excluded.update(r["context_sha256"] for r in frame)
        for entry in config["stage5_final_exclusions"]:
            excluded.update(legacy.metadata_contexts(metadata(entry)))
        if config.get("pilot_runtime_exclusions"):
            excluded.update(legacy.metadata_contexts(metadata(config["pilot_runtime_exclusions"])))
        path = root / "integration_20261116/run001/revision003/STATUS_INDEX_PRIVATE.sqlite"
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        try:
            db.execute("PRAGMA query_only=ON")
            context_states = dict(db.execute("select h,state from final_status"))
            blocked = {row[0] for row in db.execute("select h from blocked")}
        finally:
            db.close()
        excluded.update(context_states)
        excluded.update(blocked)
        protected = blocked | {h for h, value in context_states.items() if value == "quarantined"}
        key_states = {tuple(k): {"state": "prepared_or_exposed", "context_sha256": None} for k in prior_keys}
        for key, h in reference.items():
            key_states[key] = {"state": context_states.get(h, "prepared_or_exposed"), "context_sha256": h}
        # Additional exact source-key/index metadata may carry saved/unknown/
        # protection statuses not represented by an old packet manifest.
        protected_keys = {k for k, v in key_states.items() if v.get("context_sha256") in protected}
        if config.get("additional_key_states"):
            for row in metadata(config["additional_key_states"], True):
                key = tuple(row["canonical_key"])
                prior = key_states.get(key)
                if prior and prior.get("context_sha256") and row.get("context_sha256") not in (None, prior["context_sha256"]):
                    key_states[key] = {"state": "not_reconciled", "context_sha256": None}
                else:
                    key_states[key] = {"state": row["state"], "context_sha256": row.get("context_sha256")}
                if row.get("protected") is True:
                    protected_keys.add(key)
        pins = dict(state.pins)
        pins["original_reference_metadata_artifact"] = legacy.REFERENCE_SHA
        pins["current_status_and_blocked_metadata_rows"] = digest(json.dumps(
            [sorted(context_states.items()), sorted(blocked)], separators=(",", ":")).encode())
        return GuardSnapshot(excluded, context_states, key_states, protected_keys, protected,
            tuple(legacy.FORBIDDEN), pins, {
                "all_prior_statuses": True, "all_prior_source_manifests": True,
                "original_10000_reference": True, "stage5_135_frame": True,
                "stage5_all_final_exclusions": True, "current_runtime_guards": True,
                "original_status_context_count": len(context_states)})

    previous, prior_context_links = None, {}
    if config.get("previous_manifest"):
        need(config.get("pilot_runtime_exclusions"), "continuation_runtime_exclusions_required")
        entry = config["previous_manifest"]
        previous = metadata(entry)
        previous["manifest_sha256"] = entry["sha256"]
        # Root's immutable registration must provide the accumulated prepared
        # context links from SHA-pinned preceding batch INPUT metadata, not bodies.
        for row in metadata(config["prior_context_links"], True):
            h = row["context_sha256"]
            need(h not in prior_context_links, "duplicate_prior_context_link")
            prior_context_links[h] = {"input_case": row["input_case"], "batch_id": row["batch_id"]}
    cache = metadata(config["cache_metadata"]) if config.get("cache_metadata") else {}
    snapshot = collect()
    return dict(source=LegacyProjectedSource(legacy, state, window, origin), origin=origin,
                snapshot=snapshot, refresh_snapshot=collect,
                normalize=normalizer._normalize_with_flags, versions=config["versions"],
                previous=previous, prior_context_links=prior_context_links, cache=cache)

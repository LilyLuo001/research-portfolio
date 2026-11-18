"""Synthetic-only physical conservation, cache, guard and continuation checks."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import prepare_physical as p


def h(value):
    return p.digest(str(value).encode())


VERSIONS = {"protocol_version": p.PROTOCOL_VERSION, "schema_sha256": h("schema"),
            "extractor_sha256": h("extractor"), "normalizer_sha256": p.NORMALIZER_SHA256}
ORIGIN = p.Origin(h("window"), h("frame"), h("prep"), h("base"), h("description"), 0, 150, 20000)


class Source:
    def __init__(self, mutations=None):
        self.mutations = mutations or {}
        self.body_reads = []

    def metadata_rows(self, start, count):
        return [{"JOB_HASH": "job" + str(i), "SOURCE_FILE": "source.parquet", "SOURCE_ROW": i,
                 "RECORD_SOURCE_ROW": i, "catalog_row_offset": i} for i in range(start, start + count)]

    def descriptions(self, rows):
        result = {}
        for row in rows:
            i = row["SOURCE_ROW"]
            self.body_reads.append(i)
            result[i] = {"JOB_HASH": row["JOB_HASH"], "DESCRIPTION": self.mutations.get(i, "body " + str(i))}
        return result


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_states = {h("prior" + str(i)): "accepted_original_scope" for i in range(55882)}

    def snapshot(self):
        return p.GuardSnapshot(set(self.old_states), dict(self.old_states), {}, set(), set(),
            ("protected-source",), {"synthetic_metadata": h("metadata")},
            {**{k: True for k in ("all_prior_statuses", "all_prior_source_manifests", "original_10000_reference",
                 "stage5_135_frame", "stage5_all_final_exclusions", "current_runtime_guards")},
             "original_status_context_count": 55882})

    def prepare(self, source=None, snapshot=None, **kwargs):
        source, snapshot = source or Source(), snapshot or self.snapshot()
        return p.prepare_batch(source=source, origin=ORIGIN, snapshot=snapshot,
            refresh_snapshot=kwargs.pop("refresh_snapshot", lambda: snapshot),
            normalize=lambda text: (text.strip(), []), versions=kwargs.pop("versions", VERSIONS),
            batch_id=kwargs.pop("batch_id", "batch0001"), **kwargs)

    def test_first_100_true_physical_rows_and_original_item_shape(self):
        result = self.prepare()
        self.assertEqual(result["manifest"]["start_cursor"]["row_offset"], ORIGIN.next_row_offset)
        self.assertEqual(len(result["physical_rows"]), 100)
        self.assertEqual(len(result["inputs"]), 100)
        self.assertEqual(set(result["inputs"][0]["row"]), {"record_id", "context_sha256", "full_document"})
        self.assertEqual(result["manifest"]["global_authoritative_physical_total"], None)
        self.assertIsNone(result["manifest"]["full_target_dedup_ratio"])

    def test_protected_old_unknown_unreconciled_and_duplicates_preserve_every_row(self):
        snapshot = self.snapshot()
        source = Source({154: "shared body", 155: "shared body", 156: "", 157: None})
        metadata = source.metadata_rows(150, 4)
        snapshot.protected_keys.add(p.canonical(metadata[0]))
        for item, state in zip(metadata[1:], ("accepted_original_scope", "reviewed_unknown", "not_reconciled")):
            snapshot.key_states[p.canonical(item)] = {"state": state, "context_sha256": h("prior0")}
        result = self.prepare(source=source, snapshot=snapshot)
        self.assertEqual(len(result["physical_rows"]), 100)
        self.assertFalse(set(range(150, 154)) & set(source.body_reads))
        self.assertEqual([r["state"] for r in result["physical_rows"][:8]], ["protected", "old_context_unresolved",
            "reviewed_unknown", "not_reconciled", "new_context_prepared", "duplicate_context",
            "source_unavailable", "source_unavailable"])
        self.assertEqual(result["physical_rows"][4]["input_case"], result["physical_rows"][5]["input_case"])
        self.assertEqual(len(result["inputs"]), 93)

    def test_old_context_hash_not_called_or_inferred_negative(self):
        snapshot = self.snapshot()
        body = "previously exposed normalized body"
        snapshot.excluded_contexts.add(h(body))
        snapshot.context_states[h(body)] = "saved_unverified"
        result = self.prepare(source=Source({150: body}), snapshot=snapshot)
        self.assertEqual(result["physical_rows"][0]["state"], "saved_unverified")
        self.assertIsNone(result["physical_rows"][0]["input_case"])
        self.assertEqual(len(result["inputs"]), 99)

    def test_compatible_cache_uses_versions_and_never_promotes_old_unknown(self):
        snapshot = self.snapshot()
        body, context = "cached body", h("cached body")
        key = p.cache_key(context, VERSIONS)
        cache = {key: {"cache_key": key, "context_sha256": context, "versions": VERSIONS,
                      "status": "complete_known_compatible", "measure_ids": ["existing.frozen.measure"],
                      "output_sha256": h("saved output")}}
        result = self.prepare(source=Source({150: body}), cache=cache)
        self.assertEqual(result["physical_rows"][0]["state"], "compatible_cache_reference")
        self.assertEqual(len(result["inputs"]), 99)
        snapshot.excluded_contexts.add(context)
        snapshot.context_states[context] = "reviewed_unknown"
        result = self.prepare(source=Source({150: body}), snapshot=snapshot, cache=cache)
        self.assertEqual(result["physical_rows"][0]["state"], "reviewed_unknown")

    def test_different_extractor_cannot_hit_old_cache(self):
        other = dict(VERSIONS, extractor_sha256=h("new extractor"))
        self.assertNotEqual(p.cache_key(h("body"), VERSIONS), p.cache_key(h("body"), other))

    def test_changed_guard_aborts_without_committed_inputs(self):
        before = self.snapshot()
        after = deepcopy(before)
        after.excluded_contexts.add(h("new external exposure"))
        with self.assertRaisesRegex(p.PreparationError, "snapshot_changed"):
            self.prepare(snapshot=before, refresh_snapshot=lambda: after)

    def test_incomplete_exclusion_metadata_refused_before_source_reads(self):
        snapshot, source = self.snapshot(), Source()
        snapshot.coverage["stage5_all_final_exclusions"] = False
        with self.assertRaisesRegex(p.PreparationError, "incomplete_exclusion"):
            self.prepare(snapshot=snapshot, source=source)
        self.assertEqual(source.body_reads, [])

    def test_next_batch_exact_cursor_chain_and_prior_duplicate(self):
        first = self.prepare()
        previous = {**first["manifest"], "manifest_sha256": h("actual prior manifest bytes")}
        links = {item["row"]["context_sha256"]: {"input_case": item["case"], "batch_id": "batch0001"}
                 for item in first["inputs"]}
        result = self.prepare(source=Source({250: "body 150"}), batch_id="batch0002", previous=previous,
                              prior_context_links=links)
        self.assertEqual(result["manifest"]["start_cursor"]["row_offset"], 250)
        self.assertEqual(result["manifest"]["cumulative_physical_rows"], 200)
        self.assertEqual(result["manifest"]["cumulative_new_unique_contexts"], 199)
        self.assertEqual(result["physical_rows"][0]["state"], "duplicate_context")

    def test_total_physical_cap_includes_reused_rows(self):
        previous = {"origin_sha256": ORIGIN.identity(), "versions": VERSIONS,
            "end_cursor_exclusive": {"shard_ordinal": 0, "row_offset": 10140},
            "cumulative_physical_rows": 9990, "cumulative_new_unique_contexts": 0,
            "manifest_sha256": h("prior")}
        result = self.prepare(previous=previous, batch_id="batch0100")
        self.assertEqual(result["manifest"]["physical_rows"], 10)
        self.assertEqual(result["manifest"]["cumulative_physical_rows"], 10000)

    def test_changed_origin_or_versions_and_missing_prior_links_refused(self):
        first = self.prepare()
        previous = {**first["manifest"], "manifest_sha256": h("prior")}
        with self.assertRaisesRegex(p.PreparationError, "prior_input_context_links_incomplete"):
            self.prepare(previous=previous)
        previous["origin_sha256"] = h("wrong")
        with self.assertRaisesRegex(p.PreparationError, "origin_or_versions_changed"):
            self.prepare(previous=previous)

    def test_source_window_gap_and_source_identity_mismatch_refused(self):
        class Gap(Source):
            def metadata_rows(self, start, count):
                return super().metadata_rows(start + 1, count)
        with self.assertRaisesRegex(p.PreparationError, "not_exactly_conserved"):
            self.prepare(source=Gap())
        class Wrong(Source):
            def descriptions(self, rows):
                result = super().descriptions(rows)
                result[150]["JOB_HASH"] = "wrong"
                return result
        with self.assertRaisesRegex(p.PreparationError, "JOB_HASH"):
            self.prepare(source=Wrong())

    def test_row_limit_bounds_and_shard_boundary_no_guessed_successor(self):
        for limit in (0, 10001, True):
            with self.subTest(limit=limit), self.assertRaises(p.PreparationError):
                self.prepare(row_limit=limit)
        end_origin = p.Origin(**{**ORIGIN.__dict__, "shard_rows": 155})
        snapshot = self.snapshot()
        result = p.prepare_batch(source=Source(), origin=end_origin, snapshot=snapshot,
            refresh_snapshot=lambda: snapshot, normalize=lambda x: (x, []), versions=VERSIONS, batch_id="batch0001")
        self.assertEqual(result["manifest"]["physical_rows"], 5)
        self.assertEqual(result["manifest"]["end_cursor_exclusive"], {"shard_ordinal": 0, "row_offset": 155})

    def test_append_only_output_manifest_hashes_and_every_row_roundtrip(self):
        result = self.prepare()
        with tempfile.TemporaryDirectory(prefix="economic-physical-synthetic-") as temp:
            out = Path(temp) / "batch0001"
            receipt = p.commit_batch(result, out)
            raw = (out / "BATCH_MANIFEST_PUBLIC.json").read_bytes()
            manifest = json.loads(raw)
            self.assertEqual(p.digest(raw), receipt["manifest_sha256"])
            for key, name in manifest["filenames"].items():
                self.assertEqual(p.digest((out / name).read_bytes()), manifest[key + "_sha256"])
            self.assertEqual(len((out / "PHYSICAL_ROWS_PRIVATE.jsonl").read_text().splitlines()), 100)
            with self.assertRaises(FileExistsError):
                p.commit_batch(result, out)


if __name__ == "__main__":
    unittest.main()

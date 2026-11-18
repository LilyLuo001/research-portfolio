"""Reuse original Stage 5 Blob/RangeIO projection; no network on import."""
from pathlib import Path

from prepare_physical import canonical, need


class LegacyProjectedSource:
    def __init__(self, legacy, state, window, origin):
        self.legacy, self.state, self.window, self.origin = legacy, state, window, origin
        self.groups = {"base": 0, "description": 0}

    def range_receipts(self):
        return list(self.state.ranges)

    def statistics(self):
        return {"network_bytes_read": self.state.net, "metadata_bytes_read": self.state.meta,
                "row_groups_selected": dict(self.groups), "range_events": len(self.state.ranges),
                "source_whole_content_sha_recomputed": False,
                "original_reference_metadata_artifact_whole_sha_recomputed": True,
                "provenance": "verified_ledger_sha_size_stable_ETag_projected_ranges_and_actual_source_keys",
                "storage_row_groups_decode_extra_rows_but_only_allowed_source_values_selected": True}

    def metadata_rows(self, start, count):
        legacy, state, window = self.legacy, self.state, self.window
        base = window["base_register_entry"]
        loc = legacy.ledger_locations(state.root, self.origin.base_artifact_sha256)[0]
        need(loc["size"] == base["ad_bytes"], "base_size_changed")
        blob = legacy.Blob(state, loc, "pilot_canonical_base")
        md = blob.metadata()
        need(md.num_rows == self.origin.shard_rows, "base_row_count_changed")
        spans = legacy.group_ranges(md)
        groups = [g for a, b, g in spans if a < start + count and b > start]
        need(len(groups) <= 2, "bounded_base_row_group_cap")
        self.groups["base"] = len(groups)
        result = []
        binding = window["description_source_binding"]
        for group, table in blob.projected_groups(md, groups, legacy.KEY):
            offset = spans[group][0]
            low, high = max(start - offset, 0), min(start + count - offset, table.num_rows)
            for ordinal, row in enumerate(table.slice(low, high - low).to_pylist(), offset + low):
                key = canonical(row)
                need(key[1] == binding["accounting_source_path"]
                     or (not Path(key[1]).is_absolute() and Path(key[1]).name == binding["source_basename"]),
                     "source_file_binding_disagrees")
                result.append({**row, "catalog_row_offset": ordinal})
        return result

    def descriptions(self, selected):
        legacy, state = self.legacy, self.state
        loc = legacy.ledger_locations(state.root, self.origin.description_artifact_sha256)[0]
        need(loc["size"] == self.window["description_source_binding"]["source_bytes"], "description_size_changed")
        blob = legacy.Blob(state, loc, "pilot_selected_Description")
        md = blob.metadata()
        spans = legacy.group_ranges(md)
        requested = {canonical(row)[2] for row in selected}
        need(all(0 <= n < md.num_rows for n in requested), "source_row_outside_footer")
        jobs = {g: sorted(n for n in requested if a <= n < b) for a, b, g in spans}
        jobs = {g: rows for g, rows in jobs.items() if rows}
        need(len(jobs) <= 4, "bounded_description_row_group_cap")
        self.groups["description"] = len(jobs)
        result = {}
        for group, table in blob.projected_groups(md, sorted(jobs), ["JOB_HASH", "DESCRIPTION"]):
            begin = spans[group][0]
            for ordinal in jobs[group]:
                result[ordinal] = {"JOB_HASH": table.column("JOB_HASH")[ordinal - begin].as_py(),
                                   "DESCRIPTION": table.column("DESCRIPTION")[ordinal - begin].as_py()}
        return result

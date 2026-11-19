"""Create new code versions only. Never edit frozen source or research artifacts."""
from pathlib import Path
P=Path(__file__).resolve().parent;B=P.parent
s=(B/'control/finite_pipeline.py').read_text()
s=s.replace('economic-finite-pipeline-20261119-v1','economic-finite-pipeline-20261119-v2-jsonl')
s=s.replace('FINITE_PIPELINE_CODE_PINS_PUBLIC.json','FINITE_PIPELINE_CODE_PINS_V2_PUBLIC.json')
s=s.replace('measurement/publish_physical_v2.py','measurement/publish_physical_v3.py')
s=s.replace('path.read_text().splitlines()', 'jsonl_lines(path)')
s=s.replace('output.read_text().splitlines()', 'jsonl_lines(output)')
s=s.replace('input_path.read_text().splitlines()', 'jsonl_lines(input_path)')
# Replacement order must not accidentally transform input_path into input_jsonl_lines.
s=s.replace('input_jsonl_lines(path)', 'jsonl_lines(input_path)')
s=s.replace('def encoded(value):', '''def jsonl_lines(path):
    """Only physical LF delimits JSONL; Unicode separators inside strings are data."""
    with Path(path).open("rb") as stream:
        yield from stream


def encoded(value):''')
s=s.replace('        self.deadline = self.state["started_epoch"] + min(args.max_wall_seconds, MAX_WALL)', '        self.state["version"] = VERSION\n        self.deadline = self.state["started_epoch"] + min(args.max_wall_seconds, MAX_WALL)')
s=s.replace('        self.state.update(status=status,', '        if status != \"finite_pipeline_stopped\":\n            self.state.pop(\"stop_reason\", None)\n        self.state.update(status=status,')
s=s.replace('    def luna_finished(self, manifest):', '''    def verified_size_no_call(self, manifest, row):
        # This is an unprocessed, deliberately unbilled input, NOT a successful label.
        # Reconstruct the unchanged original payload locally to verify the bound.
        sys.path.insert(0, str(self.root / "runtime"))
        import pilot_common as common
        policy, items, exclusions, batch = common.load_bundle(
            self.root, self.root / "policy.json", Path(manifest["manifest_path"]), manifest["manifest_sha256"])
        item = next((x for x in items if x["row"]["context_sha256"] == row["context_sha256"]), None)
        if item is None or row.get("leg") != "Luna" or row.get("case") != str(item["case"]) or row.get("record_id") != item["row"]["record_id"]:
            raise StopPipeline("no_call_input_identity_mismatch")
        if row.get("payload") is not None or row.get("field_validation") is not None:
            raise StopPipeline("no_call_must_not_contain_semantic_result")
        conn = sqlite3.connect((self.root / "ADMISSION_PRIVATE.sqlite3").as_uri() + "?mode=ro", uri=True)
        try:
            if conn.execute("SELECT COUNT(*) FROM claims WHERE leg='Luna' AND context=?", (row["context_sha256"],)).fetchone()[0]:
                raise StopPipeline("no_call_has_existing_claim")
        finally:
            conn.close()
        body = common.encoded(common.model_payload(self.root, "Luna", item, exclusions))
        if len(body) <= common.MAX_REQUEST_BYTES:
            raise StopPipeline("no_call_size_bound_not_reproduced")
        # Retain the original request_bound_exceeded_no_call row and every byte.
        # The projection has no ledger result and correctly retains unknowns.
        return True

    def luna_finished(self, manifest):''')
s=s.replace('            elif row.get("status") == "unprocessed_bounded_stop":\n                pending = True\n            else:', '            elif row.get("status") == "unprocessed_bounded_stop":\n                pending = True\n            elif previous is None and row.get("status") == "request_bound_exceeded_no_call":\n                self.verified_size_no_call(manifest, row)\n            else:')
assert 'input_jsonl' not in s and '.read_text().splitlines()' not in s
(P/'finite_pipeline_v2.py').write_text(s)
p=(B/'measurement/publish_physical.py').read_text()
p=p.replace('    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]', '    with Path(path).open("rb") as stream:\n        return [json.loads(x) for x in stream if x.strip()]')
(P/'publish_physical_v3.py').write_text(p)

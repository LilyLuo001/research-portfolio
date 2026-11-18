"""Real frozen scorer/validator API, but synthetic text and a temporary ledger only."""
import argparse
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
import pilot_common as c

BASE = Path(__file__).resolve().parents[2]
PROTOCOL_DIR = BASE / "confirmation_stage5_20261118/protocol"
REPOSITORY = BASE.parents[0] / "LinkUp_Research_20260924/reproducibility_git"


class ProjectionIntegrationTests(unittest.TestCase):
    def test_actual_frozen_api_projects_exact15_and_preserves_local_unknown(self):
        publisher = c.import_path("projection_under_review", BASE / "pilot_economic_20261119/measurement/publish_physical.py")
        scorer = c.import_path("real_frozen_scorer", PROTOCOL_DIR / "field_score.py")
        with patch.dict(sys.modules, {"field_score": scorer}):
            fixtures = c.import_path("original_synthetic_score_fixtures", PROTOCOL_DIR / "test_field_score.py")
        validator = scorer.load_validator(repo=REPOSITORY, protocol=fixtures.PROTOCOL)
        source = fixtures.packet("Three years accounting experience required.")
        review = fixtures.blank(source)
        review["experience_outcomes"]["occupation_task"] = "present"
        review["experience_clauses"] = [fixtures.clause(source["full_document"], object="occupation_task")]
        review["responsibility_outcomes"]["training_mentoring"] = "present"
        review["responsibility_items"] = [{"dimension": "training_mentoring", "subject": "advertised_worker",
            "relation": "current_duty", "conditionality": "unconditional", "quotes": ["MISSING SYNTHETIC QUOTE"]}]
        validation = validator.validate(source, review, protected=False)
        release_file = BASE / "pilot_economic_20261119/measurement/ECONOMIC_RELEASE_PUBLIC.json"
        release = c.read(release_file)
        self.assertEqual(len(release["released_measure_ids"]), 15)
        with tempfile.TemporaryDirectory() as folder, \
             patch("socket.socket.connect", side_effect=AssertionError("network forbidden")), \
             patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            root = Path(folder).resolve()
            batch = root / "preparation/batch0001"
            batch.mkdir(parents=True)
            (root / "measurement").mkdir()
            (root / "measurement/ECONOMIC_RELEASE_PUBLIC.json").write_bytes(release_file.read_bytes())
            item = {"case": "synthetic", "row": source, "fresh_never_exposed": True}
            inputs = [item]
            physical = [{"physical_row_id": "synthetic_%s" % i, "context_sha256": source["context_sha256"], "state": state}
                for i, state in enumerate(("new_context_prepared", "duplicate_context", "protected"))]
            manifest = {"batch_id": "batch0001", "cumulative_physical_rows": 3,
                "previous_batch_manifest_sha256": None, "filenames": {}}
            for key, value in (("inputs", inputs), ("physical_rows", physical), ("exclusions", {})):
                name = key + ".json"
                manifest["filenames"][key] = name
                if key == "exclusions":
                    c.save(batch / name, value)
                else:
                    (batch / name).write_bytes(b"".join(c.encoded(row) + b"\n" for row in value))
                manifest[key + "_sha256"] = c.sha(batch / name)
            c.save(batch / "BATCH_MANIFEST_PUBLIC.json", manifest)
            manifest_sha = c.sha(batch / "BATCH_MANIFEST_PUBLIC.json")
            cpu_path = batch / "CPU_RULE_RESULTS_PRIVATE.jsonl"
            cpu_path.write_bytes(c.encoded({'context_sha256': source['context_sha256'], 'result': {'candidate_only': True}}) + b'\n')
            c.save(batch / 'CPU_RULE_RECEIPT_PUBLIC.json', {'input_sha256': manifest['inputs_sha256'], 'output_sha256': c.sha(cpu_path)})
            policy = dict(protocol_version=c.VERSION, released_measure_ids=release["released_measure_ids"],
                phase_prior_reserved_nano=c.MIN_PRIOR_RESERVED_NANO,
                prior_confirmation_reserved_nano=c.CONFIRMATION_RESERVED_NANO,
                phase_infrastructure_reserved_nano=c.INFRASTRUCTURE_CAP_NANO, phase_cap_nano=c.PHASE_CAP_NANO,
                initial_batch_manifest_sha256=manifest_sha,
                pins={"measurement/ECONOMIC_RELEASE_PUBLIC.json": c.sha(release_file)})
            c.save(root / "policy.json", policy)
            ledger = c.Ledger(root, policy, c.sha(root / "policy.json"))
            ledger.register_batch(dict(manifest, manifest_sha256=manifest_sha))
            result = dict(case="synthetic", record_id=source["record_id"], context_sha256=source["context_sha256"],
                leg="Luna", payload=review, field_validation=validation, status="field_local_validation_complete",
                policy_sha256=c.sha(root / "policy.json"))
            c.save(root / "RESULT_PRIVATE.json", result)
            attempt = ledger.reserve("Luna", item, b"{}", c.time.time() + 100, 100)
            ledger.finish(attempt, "field_local_validation_complete", {}, root / "RESULT_PRIVATE.json")
            args = argparse.Namespace(directory=root, through_batch="batch0001", output=root / "output",
                scorer=PROTOCOL_DIR / "field_score.py", scorer_sha256=c.sha(PROTOCOL_DIR / "field_score.py"),
                frozen_validator=REPOSITORY / fixtures.PROTOCOL["frozen_validator"],
                frozen_validator_sha256=c.sha(REPOSITORY / fixtures.PROTOCOL["frozen_validator"]))
            with contextlib.redirect_stdout(io.StringIO()):
                publisher.project(args)
            rows = publisher.lines(args.output / "PHYSICAL_INCREMENT_PRIVATE.jsonl")
            self.assertEqual(len(rows), 3)
            for row in rows[:2]:
                fields = row["semantic_context_result"]["measurements"]
                self.assertEqual(set(fields), set(release["released_measure_ids"]))
                self.assertEqual(fields["experience.occupation_task.mention"]["value"], 1)
                self.assertEqual(fields["responsibility.people_supervision.mention"]["value"], 0)
                self.assertIsNone(fields["responsibility.training_mentoring.mention"]["value"])
                self.assertEqual(fields["responsibility.training_mentoring.mention"]["source_observation_status"], "invalid_local")
            self.assertIsNone(rows[2]["semantic_context_result"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Generated metadata only; never load a real score, row, output, or body."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest

import release_mask as m


PROTOCOL_DIR = Path(__file__).resolve().parents[1] / "protocol"
MENTION = "experience.general_work.mention"
YEARS = "experience.general_work.years"
OTHER = "experience.general_work.strength"
FRAME_SHA = hashlib.sha256(b"synthetic-frame-only").hexdigest()


def original_scorer():
    path = PROTOCOL_DIR / "field_score.py"
    source = path.read_bytes()
    assert hashlib.sha256(source).hexdigest() == m.SCORER_SHA256
    module = types.ModuleType("synthetic_frozen_scorer")
    module.__file__ = str(path)
    # Hash-verified source, no import cache writes and no main() execution.
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def aggregate():
    scorer = original_scorer()
    protocol = json.loads((PROTOCOL_DIR / "CONFIRMATION_PROTOCOL.json").read_bytes())
    claim = {"values": {"object": "general_work", "years_min": 3},
             "evidence": {"units": [0], "spans": [[0, 10]]}, "scope": None}
    positive = {"status": "known", "outcome": "present", "atoms": [claim]}
    negative = {"status": "known", "outcome": "not_mentioned", "atoms": []}
    unknown = {"status": "reviewed_unknown", "outcome": "unknown", "atoms": []}
    pairs = [(positive, positive)] * 25 + [(negative, negative)] * 25
    results = {"confirmation": {}, "challenge": {}}
    for spec in protocol["measures"]:
        sample = pairs if spec["id"] in {MENTION, YEARS} else [(unknown, unknown)] * 50
        results["confirmation"][spec["id"]] = scorer.summarize(sample, spec, protocol["gate"], qualify=True)
        results["challenge"][spec["id"]] = scorer.summarize([], spec, protocol["gate"], qualify=False)
    return {
        "protocol_version": protocol["version"], "accounting": {"frame_cases": 50},
        "measure_results": results, "eligible_measure_dependencies": [MENTION, YEARS],
        "freeze_binding": {"frame_sha256": FRAME_SHA,
                           "protocol_bundle_sha256": m.BUNDLE_SHA256,
                           "frozen_before_first_request": True},
        "production_admission": False,
        "production_requires_qualified_dependency_subset_and_external_runtime_controls": True,
        "machine_reference_agreement_is_not_gold_accuracy": True,
        "population_generalization_certified": False,
    }


def row():
    validation = {
        "status": "field_checks_completed", "production_admission": False,
        "original_review_modified": False,
        "fields": {"experience.general_work": {
            "status": "engineering_valid", "errors": [],
            "inventory_scope": "full", "field_review_complete": True,
            "semantic_accuracy_certified": False,
        }},
    }
    observations = {name: {"status": "known", "outcome": "not_mentioned", "atoms": []}
                    for name in (MENTION, YEARS, OTHER)}
    return {"declared_missing_measures": [MENTION, YEARS, OTHER],
            "validation": validation, "observations": observations}


class ReleaseMaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = aggregate()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pilot-mask-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.score_path = Path(self.temp.name) / "SYNTHETIC_SCORES.json"

    def load(self, score=None, expected_score=None, frame=FRAME_SHA, protocol=PROTOCOL_DIR):
        data = json.dumps(self.template if score is None else score, allow_nan=False).encode()
        self.score_path.write_bytes(data)
        return m.load_gate(protocol, self.score_path,
                           expected_score_sha256=expected_score or m.digest(data),
                           expected_frame_sha256=frame)

    def test_exact_measure_intersection_no_whole_family_promotion(self):
        gate = self.load()
        result = m.row_mask(gate, **row())
        self.assertEqual(result["release_measure_dependencies"], [MENTION, YEARS])
        self.assertEqual(result["denied_missing_measures"], {OTHER: "not_independently_eligible"})
        self.assertFalse(result["production_admission"])
        self.assertFalse(result["derived_qualification_granted"])

    def test_existing_or_undeclared_measure_not_released(self):
        args = row()
        args["declared_missing_measures"] = [YEARS]
        self.assertEqual(m.row_mask(self.load(), **args)["release_measure_dependencies"], [YEARS])

    def test_invalid_unknown_partial_or_incomplete_field_denied(self):
        changes = [{"status": value} for value in ("reviewed_unknown", "invalid_local", "blocked_shared_input")]
        changes += [{"inventory_scope": "partial"}, {"field_review_complete": False}, {"errors": ["invalid"]}]
        gate = self.load()
        for patch in changes:
            with self.subTest(patch=patch):
                args = row()
                args["validation"]["fields"]["experience.general_work"].update(patch)
                self.assertEqual(m.row_mask(gate, **args)["release_measure_dependencies"], [])

    def test_known_family_does_not_promote_unknown_measure(self):
        gate = self.load()
        for state in ("reviewed_unknown", "unresolved_measure_component", "invalid_local", "unprocessed"):
            with self.subTest(state=state):
                args = row()
                args["observations"][YEARS] = {"status": state, "outcome": "unknown", "atoms": []}
                self.assertEqual(m.row_mask(gate, **args)["release_measure_dependencies"], [MENTION])

    def test_missing_observation_and_unknown_outcome_deny(self):
        args = row()
        del args["observations"][YEARS]
        args["observations"][MENTION]["outcome"] = "unknown"
        self.assertEqual(m.row_mask(self.load(), **args)["release_measure_dependencies"], [])

    def test_shared_invalid_or_protected_validation_deny(self):
        gate = self.load()
        for state in ("shared_input_invalid", "quarantined"):
            with self.subTest(state=state):
                args = row()
                args["validation"] = {"status": state, "fields": {}, "production_admission": False}
                self.assertEqual(m.row_mask(gate, **args)["release_measure_dependencies"], [])

    def test_all_declared_derived_dependencies_required_without_qualification(self):
        args = row()
        args["derived_dependencies"] = {"synthetic.complete": [MENTION, YEARS],
                                        "synthetic.incomplete": [MENTION, YEARS, OTHER]}
        result = m.row_mask(self.load(), **args)
        self.assertEqual(result["derived_all_declared_dependencies_released"],
                         {"synthetic.complete": True, "synthetic.incomplete": False})
        self.assertNotIn("synthetic.complete", result["eligible_measure_dependencies"])
        self.assertFalse(result["derived_qualification_granted"])
        args["declared_missing_measures"] = [MENTION]
        self.assertFalse(m.row_mask(self.load(), **args)["derived_all_declared_dependencies_released"]["synthetic.complete"])

    def test_family_wildcard_unknown_or_duplicate_measure_ids_rejected(self):
        gate = self.load()
        for ids in (["experience.general_work"], ["experience.*"], ["missing"], [MENTION, MENTION], MENTION):
            with self.subTest(ids=ids), self.assertRaises(m.MaskError):
                m.row_mask(gate, **dict(row(), declared_missing_measures=ids))

    def test_empty_unknown_or_family_derived_dependency_rejected(self):
        gate = self.load()
        for ids in ([], ["experience.general_work"], ["missing"], [MENTION, MENTION]):
            with self.subTest(ids=ids), self.assertRaises(m.MaskError):
                m.row_mask(gate, **dict(row(), derived_dependencies={"synthetic": ids}))

    def test_no_eligible_measure_refused(self):
        score = deepcopy(self.template)
        for measure in (MENTION, YEARS):
            score["measure_results"]["confirmation"][measure]["machine_reference_measure_gate_pass"] = False
            score["measure_results"]["confirmation"][measure]["blocking_reasons"] = ["synthetic_failure"]
        score["eligible_measure_dependencies"] = []
        with self.assertRaisesRegex(m.MaskError, "no_independently_eligible_measure"):
            self.load(score)

    def test_score_bytes_or_frame_pin_change_refused(self):
        with self.assertRaisesRegex(m.MaskError, "artifact_sha_mismatch"):
            self.load(expected_score="0" * 64)
        with self.assertRaisesRegex(m.MaskError, "score_freeze_binding_mismatch"):
            self.load(frame="0" * 64)

    def test_boolean_freeze_and_bundle_binding_required(self):
        for key, value in (("frozen_before_first_request", 1), ("frozen_before_first_request", False),
                           ("protocol_bundle_sha256", "0" * 64)):
            score = deepcopy(self.template)
            score["freeze_binding"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(m.MaskError):
                self.load(score)

    def test_protocol_member_modified_refused(self):
        folder = Path(self.temp.name) / "synthetic-bundle-copy"
        folder.mkdir()
        bundle = json.loads((PROTOCOL_DIR / "PROTOCOL_FREEZE.json").read_bytes())
        for name in ["PROTOCOL_FREEZE.json", *bundle["files"]]:
            (folder / name).write_bytes((PROTOCOL_DIR / name).read_bytes())
        with (folder / "CONFIRMATION_PROTOCOL.json").open("ab") as output:
            output.write(b" ")
        with self.assertRaisesRegex(m.MaskError, "frozen_member_sha_mismatch"):
            self.load(protocol=folder)

    def test_list_gate_and_challenge_consistency_required(self):
        for kind in ("list", "gate", "challenge", "count", "version", "admission"):
            score = deepcopy(self.template)
            if kind == "list":
                score["eligible_measure_dependencies"].append(OTHER)
            elif kind == "gate":
                score["measure_results"]["confirmation"][MENTION]["blocking_reasons"] = ["failure"]
            elif kind == "challenge":
                score["measure_results"]["challenge"][OTHER].update(
                    machine_reference_measure_gate_pass=True, blocking_reasons=[])
            elif kind == "count":
                score["accounting"]["frame_cases"] = 49
            elif kind == "version":
                score["protocol_version"] = "other"
            else:
                score["production_admission"] = True
            with self.subTest(kind=kind), self.assertRaises(m.MaskError):
                self.load(score)

    def test_sanitized_report_without_freeze_binding_not_accepted(self):
        score = deepcopy(self.template)
        del score["freeze_binding"]
        with self.assertRaises(m.MaskError):
            self.load(score)

    def test_duplicate_keys_nonfinite_and_overflow_refused(self):
        for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}'):
            with self.subTest(data=data), self.assertRaises(m.MaskError):
                m.parse(data)

    def test_inputs_not_mutated_and_gate_mapping_immutable(self):
        gate = self.load()
        args = row()
        before = deepcopy(args)
        m.row_mask(gate, **args)
        self.assertEqual(args, before)
        with self.assertRaises(TypeError):
            gate.measure_fields[MENTION] = "other"


if __name__ == "__main__":
    unittest.main()
